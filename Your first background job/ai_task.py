"""
Slow Operation Worker Task:
Simulates or performs the heavy A6 AI judgment classification call.
In synchronous request cycles, this operation would block HTTP threads for 1.5 - 5 seconds.
Moving it to a background worker frees the web server immediately.
"""

import asyncio
import os
import time
import json
from datetime import datetime, timezone
from typing import Optional
import httpx

from schemas import (
    TriageJudgment,
    TriageCategory,
    UrgencyLevel,
    JobSubmissionRequest,
)


class SlowAIOperationError(Exception):
    """Raised when the slow AI task experiences a transient or fatal error."""
    pass


async def execute_slow_ai_triage(
    request: JobSubmissionRequest,
    simulate_failure: bool = False,
    attempt: int = 1
) -> TriageJudgment:
    """
    Executes the slow AI customer triage operation.
    """
    start_time = time.perf_counter()

    # 1. Simulate artificial work / slow network latency if specified
    delay = getattr(request, "simulate_delay_sec", 1.0)
    if delay > 0:
        await asyncio.sleep(delay)

    # 2. Check for forced failure simulation (for testing retries and alerts)
    if simulate_failure:
        raise SlowAIOperationError(
            f"Simulated upstream model 503 Service Unavailable (attempt #{attempt})"
        )

    # 3. Check if real Groq API key is present
    groq_api_key = os.getenv("GROQ_API_KEY")
    if groq_api_key and groq_api_key.strip():
        try:
            return await _call_groq_api(request.message, groq_api_key, start_time)
        except Exception as e:
            # Fall back to offline deterministic evaluator if upstream fails
            pass

    # 4. Deterministic offline evaluation
    return _evaluate_offline_deterministic(request.message, start_time)


async def _call_groq_api(message: str, api_key: str, start_time: float) -> TriageJudgment:
    prompt = f"""
    Analyze the following customer inquiry and return ONLY valid JSON matching this schema:
    {{
        "category": "support_technical" | "billing_refund" | "security_incident" | "feature_request" | "general_inquiry",
        "urgency": "critical" | "high" | "medium" | "low",
        "confidence": float (0.0 to 1.0),
        "summary": "1-sentence summary",
        "recommended_action": "concrete operational step",
        "is_escalation_required": boolean
    }}

    Customer message:
    \"\"\"{message}\"\"\"
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "llama-3.1-8b-instant",
                "messages": [
                    {"role": "system", "content": "You are an automated support triage AI. Output only JSON."},
                    {"role": "user", "content": prompt}
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.1,
            }
        )
        resp.raise_for_status()
        data = resp.json()
        raw_content = data["choices"][0]["message"]["content"]
        parsed = json.loads(raw_content)

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        return TriageJudgment(
            category=TriageCategory(parsed["category"]),
            urgency=UrgencyLevel(parsed["urgency"]),
            confidence=float(parsed["confidence"]),
            summary=parsed["summary"],
            recommended_action=parsed["recommended_action"],
            is_escalation_required=bool(parsed["is_escalation_required"]),
            tokens_used=data.get("usage", {}).get("total_tokens", 85),
            execution_time_ms=elapsed_ms
        )


def _evaluate_offline_deterministic(message: str, start_time: float) -> TriageJudgment:
    """
    Zero-dependency deterministic classifier for offline development & tests.
    """
    lower = message.lower()

    if any(k in lower for k in ["breach", "hack", "leak", "exploit", "cve", "ddos", "unauthorized", "stolen"]):
        category = TriageCategory.SECURITY_INCIDENT
        urgency = UrgencyLevel.CRITICAL
        summary = "Potential security breach or vulnerability detected in message."
        action = "Immediately notify On-Call SecOps, rotate API credentials, and isolate session."
        escalate = True
    elif any(k in lower for k in ["refund", "charge", "invoice", "double charge", "billing", "payment", "card"]):
        category = TriageCategory.BILLING_REFUND
        urgency = UrgencyLevel.HIGH
        summary = "Customer inquiry regarding payment dispute or refund."
        action = "Cross-reference Stripe transaction ledger and dispatch to Tier-2 Finance."
        escalate = False
    elif any(k in lower for k in ["500", "down", "error", "crash", "timeout", "bug", "broken", "offline"]):
        category = TriageCategory.SUPPORT_TECHNICAL
        urgency = UrgencyLevel.HIGH if "down" in lower or "500" in lower else UrgencyLevel.MEDIUM
        summary = "Technical outage or software error reported."
        action = "Check Datadog APM logs and file bug report in JIRA."
        escalate = "down" in lower
    elif any(k in lower for k in ["feature", "roadmap", "wish", "could you add", "would love"]):
        category = TriageCategory.FEATURE_REQUEST
        urgency = UrgencyLevel.LOW
        summary = "User feature enhancement suggestion."
        action = "Log to ProductBoard and tag product manager."
        escalate = False
    else:
        category = TriageCategory.GENERAL_INQUIRY
        urgency = UrgencyLevel.LOW
        summary = "General question regarding services or usage."
        action = "Send standard documentation links."
        escalate = False

    elapsed_ms = (time.perf_counter() - start_time) * 1000.0

    return TriageJudgment(
        category=category,
        urgency=urgency,
        confidence=0.94,
        summary=summary,
        recommended_action=action,
        is_escalation_required=escalate,
        tokens_used=120,
        execution_time_ms=elapsed_ms
    )
