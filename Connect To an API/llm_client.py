"""
Trustworthy LLM Client with Strict Schema Enforcement, Real Timeouts,
and Intelligent Retries that Know When to Stop.

Supports two free model providers (Groq Console and Google Gemini API)
plus a built-in Mock provider for offline deterministic verification.
"""

import json
import logging
import os
import random
import time
from typing import Dict, Any, Optional

import httpx
from pydantic import ValidationError

from schemas import (
    TriageRequest,
    TriageJudgment,
    CategoryEnum,
    SentimentEnum,
    ActionEnum,
)

logger = logging.getLogger("triage_llm_client")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


# ------------------------------------------------------------------------------
# Custom Exceptions for Granular Downstream Handling
# ------------------------------------------------------------------------------

class LLMClientException(Exception):
    """Base exception for LLM Client failures."""
    def __init__(self, message: str, status_code: int = 502, is_retryable: bool = False, attempts: int = 1):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.is_retryable = is_retryable
        self.attempts = attempts


class PermanentClientException(LLMClientException):
    """Errors where retrying would be futile (400 Bad Request, 401 Unauthorized, 403 Forbidden)."""
    def __init__(self, message: str, status_code: int = 400, attempts: int = 1):
        super().__init__(message, status_code=status_code, is_retryable=False, attempts=attempts)


class TransientUpstreamException(LLMClientException):
    """Errors that are temporary and safe to retry (429 Rate Limit, 503 Outage, Network drops)."""
    def __init__(self, message: str, status_code: int = 503, attempts: int = 1):
        super().__init__(message, status_code=status_code, is_retryable=True, attempts=attempts)


class UpstreamTimeoutException(LLMClientException):
    """Raised when the upstream LLM exceeds configured real timeout."""
    def __init__(self, message: str, attempts: int = 1):
        super().__init__(message, status_code=504, is_retryable=True, attempts=attempts)


class SchemaValidationException(LLMClientException):
    """Raised when the model output fails strict Pydantic contract validation."""
    def __init__(self, message: str, raw_output: str, attempts: int = 1):
        super().__init__(f"Schema violation: {message}. Raw output: {raw_output}", status_code=502, is_retryable=False, attempts=attempts)
        self.raw_output = raw_output


# ------------------------------------------------------------------------------
# System Prompt & Structured Schema Contract
# ------------------------------------------------------------------------------

SYSTEM_PROMPT = """You are an automated, high-precision customer support triage engine.
Your single job is to analyze incoming raw customer messages and make an objective operational judgment.

You MUST respond ONLY with a valid JSON object matching the exact schema below. Do NOT output markdown, backticks, or preamble:
{
  "category": "billing" | "technical_issue" | "security_incident" | "feature_request" | "churn_risk" | "general_inquiry",
  "urgency_score": <integer from 1 to 5, where 1 is cosmetic/informational and 5 is critical security breach or total system outage>,
  "sentiment": "positive" | "neutral" | "frustrated" | "hostile",
  "recommended_action": "auto_refund_review" | "escalate_to_security" | "route_to_tier3_eng" | "standard_support_queue" | "churn_retention_contact" | "send_knowledge_base",
  "requires_human_escalation": <true if urgency_score >= 4 or security_incident or hostile sentiment, else false>,
  "confidence_score": <float between 0.0 and 1.0 calibrated to certainty>,
  "reasoning": "<concise explanation under 300 characters>",
  "extracted_entities": ["<order-id>", "<error-code>", "<monetary-amount>"]
}
"""


# ------------------------------------------------------------------------------
# Trustworthy LLM Client Implementation
# ------------------------------------------------------------------------------

class TrustworthyLLMClient:
    """
    Production-ready LLM Client incorporating:
    - Real, enforced timeouts (connect=3.0s, read=8.0s)
    - Jittered exponential backoff retries that KNOW when to stop
    - Strict Pydantic schema validation on all model responses
    - Multi-provider support (Groq Console, Google Gemini, and Mock)
    """

    def __init__(
        self,
        provider: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        max_retries: Optional[int] = None,
        base_backoff_seconds: Optional[float] = None,
    ):
        self.provider = (provider or os.getenv("LLM_PROVIDER", "mock")).lower()
        self.timeout_seconds = float(timeout_seconds or os.getenv("LLM_TIMEOUT_SECONDS", "8.0"))
        self.connect_timeout = float(os.getenv("LLM_CONNECT_TIMEOUT_SECONDS", "3.0"))
        self.max_retries = int(max_retries or os.getenv("LLM_MAX_RETRIES", "3"))
        self.base_backoff = float(base_backoff_seconds or os.getenv("LLM_BASE_BACKOFF_SECONDS", "0.5"))

        # Provider-specific configurations
        self.groq_api_key = os.getenv("GROQ_API_KEY", "")
        self.groq_model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", "")
        self.gemini_model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

        # Configure real timeouts using httpx.Timeout
        self.http_timeout = httpx.Timeout(
            connect=self.connect_timeout,
            read=self.timeout_seconds,
            write=5.0,
            pool=5.0
        )

    def is_retryable_status(self, status_code: int) -> bool:
        """Determines if an HTTP status code is safe and logical to retry."""
        # 429: Rate limit (retry with backoff)
        # 500, 502, 503, 504: Upstream server/gateway hiccups
        return status_code in (429, 500, 502, 503, 504)

    def is_permanent_client_error(self, status_code: int) -> bool:
        """Recognizes permanent failure states where retries must STOP immediately."""
        # 400: Bad request / prompt policy violation
        # 401: Unauthorized (bad or missing API key)
        # 403: Forbidden (insufficient permission)
        # 404: Not found (invalid endpoint/model URI)
        return status_code in (400, 401, 403, 404)

    async def judge_message(self, request: TriageRequest) -> TriageJudgment:
        """
        Executes the judgment workflow with retries, real timeouts, and schema enforcement.
        """
        start_time = time.time()
        last_exception = None
        attempts = 0

        user_content = (
            f"Customer Tier: {request.customer_tier.value.upper()}\n"
            f"Sender Email: {request.sender_email or 'N/A'}\n"
            f"Message Body:\n\"\"\"{request.message_body}\"\"\""
        )

        for attempt in range(1, self.max_retries + 1):
            attempts = attempt
            try:
                logger.info(
                    "Executing judgment call (Attempt %d/%d) via provider=%s for message_id=%s",
                    attempt,
                    self.max_retries,
                    self.provider,
                    request.message_id
                )

                if self.provider == "mock":
                    raw_json_str = await self._call_mock_provider(request.message_body, request.customer_tier.value)
                    model_identifier = "mock-triage-v1"
                elif self.provider == "groq":
                    raw_json_str = await self._call_groq_api(user_content)
                    model_identifier = f"groq:{self.groq_model}"
                elif self.provider == "gemini":
                    raw_json_str = await self._call_gemini_api(user_content)
                    model_identifier = f"gemini:{self.gemini_model}"
                else:
                    raise PermanentClientException(f"Unsupported LLM provider: {self.provider}", status_code=400, attempts=attempts)

                # Step 1: Parse JSON text
                try:
                    parsed_dict = json.loads(raw_json_str)
                except Exception as json_err:
                    logger.error("Model returned non-JSON text: %s", raw_json_str)
                    raise SchemaValidationException(f"Malformed JSON: {str(json_err)}", raw_output=raw_json_str, attempts=attempts)

                # Step 2: Enforce strict Pydantic schema validation
                processing_time_ms = int((time.time() - start_time) * 1000)
                judgment = self._validate_and_build_judgment(
                    parsed_dict=parsed_dict,
                    message_id=request.message_id,
                    model_used=model_identifier,
                    processing_time_ms=processing_time_ms,
                    attempts=attempts
                )

                logger.info(
                    "Successful judgment for message_id=%s: category=%s, urgency=%d, action=%s (took %dms)",
                    request.message_id,
                    judgment.category.value,
                    judgment.urgency_score,
                    judgment.recommended_action.value,
                    processing_time_ms
                )
                return judgment

            except PermanentClientException as pce:
                # CRITICAL: Stop immediately. Do not burn retries on 401/400/403 errors.
                logger.warning("Permanent failure encountered. Stopping retries immediately: %s", pce.message)
                raise pce

            except SchemaValidationException as sve:
                # Schema errors from deterministic model completions should not be retried blindly
                logger.error("Strict schema validation failed: %s", sve.message)
                raise sve

            except UpstreamTimeoutException as ute:
                last_exception = ute
                logger.warning("Upstream timeout on attempt %d: %s", attempt, ute.message)
                if attempt == self.max_retries:
                    break
                await self._sleep_backoff(attempt)

            except TransientUpstreamException as tue:
                last_exception = tue
                logger.warning("Transient upstream error on attempt %d: %s", attempt, tue.message)
                if attempt == self.max_retries:
                    break
                await self._sleep_backoff(attempt)

            except httpx.TimeoutException as te:
                last_exception = UpstreamTimeoutException(f"Read/Connect timeout of {self.timeout_seconds}s exceeded", attempts=attempts)
                logger.warning("Network timeout on attempt %d: %s", attempt, str(te))
                if attempt == self.max_retries:
                    break
                await self._sleep_backoff(attempt)

            except httpx.NetworkError as ne:
                last_exception = TransientUpstreamException(f"Network error: {str(ne)}", status_code=503, attempts=attempts)
                logger.warning("Network connection error on attempt %d: %s", attempt, str(ne))
                if attempt == self.max_retries:
                    break
                await self._sleep_backoff(attempt)

            except Exception as e:
                logger.error("Unexpected error during triage call: %s", str(e), exc_info=True)
                raise LLMClientException(f"Internal processing failure: {str(e)}", status_code=500, attempts=attempts)

        # If loop finishes without returning, retries are exhausted
        logger.error("Retry limit reached (%d attempts). Upstream service remains unavailable.", self.max_retries)
        if isinstance(last_exception, LLMClientException):
            raise last_exception
        raise TransientUpstreamException(
            f"Failed after {self.max_retries} attempts: Upstream service unavailable",
            status_code=503,
            attempts=self.max_retries
        )

    async def _sleep_backoff(self, attempt: int) -> None:
        """Exponential backoff with randomized full jitter."""
        multiplier = 2 ** (attempt - 1)
        jitter = random.uniform(0.05, 0.25)
        delay = (self.base_backoff * multiplier) + jitter
        logger.info("Sleeping %.2f seconds before retry attempt %d...", delay, attempt + 1)
        time.sleep(delay)

    def _validate_and_build_judgment(
        self,
        parsed_dict: Dict[str, Any],
        message_id: str,
        model_used: str,
        processing_time_ms: int,
        attempts: int
    ) -> TriageJudgment:
        """Injects contextual metadata and validates every field against TriageJudgment."""
        try:
            # Map into full payload
            payload = {
                **parsed_dict,
                "message_id": message_id,
                "model_used": model_used,
                "processing_time_ms": processing_time_ms,
            }
            return TriageJudgment.model_validate(payload)
        except ValidationError as ve:
            raise SchemaValidationException(
                f"Pydantic validation failed: {ve.errors()}",
                raw_output=json.dumps(parsed_dict),
                attempts=attempts
            )

    # --------------------------------------------------------------------------
    # Provider 1: Groq Console (Llama 3.3 / Llama 3.1)
    # --------------------------------------------------------------------------
    async def _call_groq_api(self, user_content: str) -> str:
        """Calls Groq's high-speed inference API with forced JSON response format."""
        if not self.groq_api_key or self.groq_api_key.startswith("gsk_your_free"):
            raise PermanentClientException("GROQ_API_KEY is not configured or invalid.", status_code=401)

        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.groq_api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": self.groq_model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content}
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"}
        }

        async with httpx.AsyncClient(timeout=self.http_timeout) as client:
            response = await client.post(url, headers=headers, json=data)

        if response.status_code == 200:
            resp_json = response.json()
            return resp_json["choices"][0]["message"]["content"]

        # Handle specific error status codes
        if self.is_permanent_client_error(response.status_code):
            raise PermanentClientException(
                f"Groq API client error: HTTP {response.status_code} - {response.text}",
                status_code=response.status_code
            )
        if self.is_retryable_status(response.status_code):
            raise TransientUpstreamException(
                f"Groq API transient error: HTTP {response.status_code} - {response.text}",
                status_code=response.status_code
            )
        raise LLMClientException(f"Groq unexpected status: {response.status_code}", status_code=502)

    # --------------------------------------------------------------------------
    # Provider 2: Google Gemini API (Google AI Studio)
    # --------------------------------------------------------------------------
    async def _call_gemini_api(self, user_content: str) -> str:
        """Calls Google AI Studio Gemini API with response_mime_type=application/json."""
        if not self.gemini_api_key or self.gemini_api_key.startswith("AIzaSy_your_free"):
            raise PermanentClientException("GEMINI_API_KEY is not configured or invalid.", status_code=401)

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.gemini_model}:generateContent?key={self.gemini_api_key}"
        headers = {"Content-Type": "application/json"}
        data = {
            "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": [{"parts": [{"text": user_content}]}],
            "generationConfig": {
                "temperature": 0.1,
                "response_mime_type": "application/json"
            }
        }

        async with httpx.AsyncClient(timeout=self.http_timeout) as client:
            response = await client.post(url, headers=headers, json=data)

        if response.status_code == 200:
            resp_json = response.json()
            return resp_json["candidates"][0]["content"]["parts"][0]["text"]

        if self.is_permanent_client_error(response.status_code):
            raise PermanentClientException(
                f"Gemini API client error: HTTP {response.status_code} - {response.text}",
                status_code=response.status_code
            )
        if self.is_retryable_status(response.status_code):
            raise TransientUpstreamException(
                f"Gemini API transient error: HTTP {response.status_code} - {response.text}",
                status_code=response.status_code
            )
        raise LLMClientException(f"Gemini unexpected status: {response.status_code}", status_code=502)

    # --------------------------------------------------------------------------
    # Deterministic Mock Provider (Zero Key Required, Fast Local Testing)
    # --------------------------------------------------------------------------
    async def _call_mock_provider(self, text: str, tier: str) -> str:
        """
        Synthesizes a realistic, deterministic judgment for unit and integration testing.
        Analyzes keywords to return accurate schema-compliant responses.
        """
        text_lower = text.lower()

        # 1. Security Incident
        if any(w in text_lower for w in ["hack", "breach", "security", "unauthorized", "stolen", "compromised"]):
            return json.dumps({
                "category": CategoryEnum.SECURITY_INCIDENT.value,
                "urgency_score": 5,
                "sentiment": SentimentEnum.HOSTILE.value if "now" in text_lower else SentimentEnum.FRUSTRATED.value,
                "recommended_action": ActionEnum.ESCALATE_TO_SECURITY.value,
                "requires_human_escalation": True,
                "confidence_score": 0.99,
                "reasoning": "Detected security breach or unauthorized access indicators. Requires immediate supervisor intervention.",
                "extracted_entities": [w for w in ["unauthorized", "compromised", "account"] if w in text_lower]
            })

        # 2. Billing / Refund
        if any(w in text_lower for w in ["charge", "refund", "invoice", "billing", "$", "double", "paid"]):
            return json.dumps({
                "category": CategoryEnum.BILLING.value,
                "urgency_score": 4 if tier == "enterprise" else 3,
                "sentiment": SentimentEnum.FRUSTRATED.value,
                "recommended_action": ActionEnum.AUTO_REFUND_REVIEW.value,
                "requires_human_escalation": tier == "enterprise",
                "confidence_score": 0.96,
                "reasoning": "Financial/billing transaction inquiry with duplicate or unexpected charge claims.",
                "extracted_entities": ["billing-inquiry"]
            })

        # 3. Technical Outage
        if any(w in text_lower for w in ["error", "500", "broken", "down", "crash", "cluster", "api"]):
            return json.dumps({
                "category": CategoryEnum.TECHNICAL_ISSUE.value,
                "urgency_score": 4 if "cluster" in text_lower or "production" in text_lower else 3,
                "sentiment": SentimentEnum.FRUSTRATED.value,
                "recommended_action": ActionEnum.ROUTE_TO_TIER3_ENG.value,
                "requires_human_escalation": True if "production" in text_lower else False,
                "confidence_score": 0.94,
                "reasoning": "System error or infrastructure degradation reported.",
                "extracted_entities": ["error-code-500"] if "500" in text_lower else ["tech-incident"]
            })

        # 4. Feature Request
        if any(w in text_lower for w in ["feature", "suggest", "would love", "add support", "roadmap"]):
            return json.dumps({
                "category": CategoryEnum.FEATURE_REQUEST.value,
                "urgency_score": 1,
                "sentiment": SentimentEnum.POSITIVE.value,
                "recommended_action": ActionEnum.STANDARD_SUPPORT_QUEUE.value,
                "requires_human_escalation": False,
                "confidence_score": 0.92,
                "reasoning": "Constructive product improvement proposal or enhancement suggestion.",
                "extracted_entities": []
            })

        # 5. Churn Risk / Cancellation Warning
        if any(w in text_lower for w in ["churn", "cancel", "terminat", "leaving", "competitor", "switch to"]):
            return json.dumps({
                "category": CategoryEnum.CHURN_RISK.value,
                "urgency_score": 4 if tier == "enterprise" else 3,
                "sentiment": SentimentEnum.HOSTILE.value if "competitor" in text_lower else SentimentEnum.FRUSTRATED.value,
                "recommended_action": ActionEnum.CHURN_RETENTION_CONTACT.value,
                "requires_human_escalation": True if tier in ("enterprise", "pro") else False,
                "confidence_score": 0.95,
                "reasoning": "High-risk customer cancellation or competitor defection warning identified.",
                "extracted_entities": ["retention-alert"]
            })

        # 6. Default General Inquiry
        return json.dumps({
            "category": CategoryEnum.GENERAL_INQUIRY.value,
            "urgency_score": 2,
            "sentiment": SentimentEnum.NEUTRAL.value,
            "recommended_action": ActionEnum.SEND_KNOWLEDGE_BASE.value,
            "requires_human_escalation": False,
            "confidence_score": 0.88,
            "reasoning": "General customer inquiry addressed by documentation.",
            "extracted_entities": []
        })
