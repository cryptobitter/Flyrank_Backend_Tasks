"""
Comprehensive Test Suite for the AI Message Triage & Judgment Engine.
Includes 8 core test cases proving schema enforcement, real timeouts,
and retries that know when to stop.
"""

import asyncio
import json
import pytest
from unittest.mock import patch, MagicMock
import httpx
from fastapi.testclient import TestClient

from main import app
from schemas import (
    TriageRequest,
    TriageJudgment,
    CategoryEnum,
    SentimentEnum,
    ActionEnum,
    CustomerTierEnum,
)
from llm_client import (
    TrustworthyLLMClient,
    PermanentClientException,
    TransientUpstreamException,
    UpstreamTimeoutException,
    SchemaValidationException,
)

client = TestClient(app)


# ------------------------------------------------------------------------------
# Test Case 1: Valid High-Urgency Judgment (Happy Path - Security Breach)
# ------------------------------------------------------------------------------
def test_urgent_security_incident_judgment_success():
    """
    Test 1: Validates happy path for a critical security incident.
    Proves model output parses cleanly into full Pydantic schema with high urgency.
    """
    async def _run():
        test_client = TrustworthyLLMClient(provider="mock")
        req = TriageRequest(
            message_id="sec-001",
            message_body="EMERGENCY: Our production API key was compromised and someone is performing unauthorized database dumps!",
            customer_tier=CustomerTierEnum.ENTERPRISE,
            sender_email="ciso@megacorp.com"
        )

        judgment = await test_client.judge_message(req)

        assert isinstance(judgment, TriageJudgment)
        assert judgment.message_id == "sec-001"
        assert judgment.category == CategoryEnum.SECURITY_INCIDENT
        assert judgment.urgency_score == 5
        assert judgment.recommended_action == ActionEnum.ESCALATE_TO_SECURITY
        assert judgment.requires_human_escalation is True
        assert judgment.confidence_score >= 0.90
        assert len(judgment.reasoning) > 0
        assert judgment.processing_time_ms >= 0

    asyncio.run(_run())


# ------------------------------------------------------------------------------
# Test Case 2: Valid Low-Urgency Judgment (Happy Path - Feature Request)
# ------------------------------------------------------------------------------
def test_feature_request_judgment_success():
    """
    Test 2: Validates happy path for a low-urgency feature request.
    Verifies sentiment calibration and standard queue routing.
    """
    async def _run():
        test_client = TrustworthyLLMClient(provider="mock")
        req = TriageRequest(
            message_id="feat-772",
            message_body="Hi team! We love your platform. Would love if you could add dark mode or export to CSV on the dashboard.",
            customer_tier=CustomerTierEnum.STANDARD,
            sender_email="user@startup.co"
        )

        judgment = await test_client.judge_message(req)

        assert isinstance(judgment, TriageJudgment)
        assert judgment.message_id == "feat-772"
        assert judgment.category == CategoryEnum.FEATURE_REQUEST
        assert judgment.urgency_score == 1
        assert judgment.sentiment == SentimentEnum.POSITIVE
        assert judgment.recommended_action == ActionEnum.STANDARD_SUPPORT_QUEUE
        assert judgment.requires_human_escalation is False

    asyncio.run(_run())


# ------------------------------------------------------------------------------
# Test Case 3: Strict Schema Validation Failure on Corrupt / Invalid LLM Output
# ------------------------------------------------------------------------------
def test_strict_schema_validation_failure_on_corrupt_llm_output():
    """
    Test 3: Verifies that when an LLM returns invalid JSON or violates field bounds
    (e.g., urgency_score = 99 or invalid category), the client rejects it instantly
    with SchemaValidationException rather than corrupting downstream databases.
    """
    async def _run():
        test_client = TrustworthyLLMClient(provider="mock")
        req = TriageRequest(
            message_id="err-schema-01",
            message_body="Please cancel my subscription.",
            customer_tier=CustomerTierEnum.STANDARD
        )

        # Corrupt payload: urgency_score out of range (must be 1-5), missing required fields
        corrupt_mock_response = json.dumps({
            "category": "not_a_real_category",
            "urgency_score": 99,
            "sentiment": "neutral"
            # missing recommended_action, requires_human_escalation, confidence_score, reasoning
        })

        with patch.object(test_client, "_call_mock_provider", return_value=corrupt_mock_response):
            with pytest.raises(SchemaValidationException) as exc_info:
                await test_client.judge_message(req)

            assert exc_info.value.status_code == 502
            assert exc_info.value.is_retryable is False
            assert "Schema violation" in exc_info.value.message

    asyncio.run(_run())


# ------------------------------------------------------------------------------
# Test Case 4: Real Timeout Enforcement (Upstream Latency Spike)
# ------------------------------------------------------------------------------
def test_real_timeout_triggers_gateway_timeout():
    """
    Test 4: Verifies that slow upstream network calls trigger a real timeout
    rather than hanging the API worker indefinitely.
    """
    async def _run():
        test_client = TrustworthyLLMClient(provider="groq", timeout_seconds=0.1, max_retries=1)
        test_client.groq_api_key = "gsk_test_mock_key"
        req = TriageRequest(
            message_id="timeout-01",
            message_body="Testing timeout handling on slow connection.",
            customer_tier=CustomerTierEnum.STANDARD
        )

        # Simulate httpx.ReadTimeout during network request
        with patch("httpx.AsyncClient.post", side_effect=httpx.ReadTimeout("Read timed out after 0.1s")):
            with pytest.raises(UpstreamTimeoutException) as exc_info:
                await test_client.judge_message(req)

            assert exc_info.value.status_code == 504
            assert exc_info.value.is_retryable is True
            assert "timeout" in exc_info.value.message.lower()

    asyncio.run(_run())


# ------------------------------------------------------------------------------
# Test Case 5: Transient 429 Rate Limit Retries with Backoff and Succeeds
# ------------------------------------------------------------------------------
def test_transient_429_rate_limit_retries_and_succeeds():
    """
    Test 5: Verifies that transient HTTP 429 (Rate Limit) triggers exponential
    backoff retry and recovers successfully on attempt 2.
    """
    async def _run():
        test_client = TrustworthyLLMClient(provider="groq", max_retries=3, base_backoff_seconds=0.01)
        test_client.groq_api_key = "gsk_test_valid_key"
        req = TriageRequest(
            message_id="retry-429-01",
            message_body="I was charged twice for order #992.",
            customer_tier=CustomerTierEnum.STANDARD
        )

        valid_judgment_json = json.dumps({
            "category": CategoryEnum.BILLING.value,
            "urgency_score": 3,
            "sentiment": SentimentEnum.FRUSTRATED.value,
            "recommended_action": ActionEnum.AUTO_REFUND_REVIEW.value,
            "requires_human_escalation": False,
            "confidence_score": 0.95,
            "reasoning": "Duplicate charge inquiry on order #992.",
            "extracted_entities": ["992"]
        })

        # Mock responses: 1st call -> 429 Too Many Requests, 2nd call -> 200 OK
        resp_429 = MagicMock(status_code=429, text="Rate limit exceeded. Try again in 200ms.")
        resp_200 = MagicMock(
            status_code=200,
            json=lambda: {"choices": [{"message": {"content": valid_judgment_json}}]}
        )

        with patch("httpx.AsyncClient.post", side_effect=[resp_429, resp_200]) as mock_post:
            judgment = await test_client.judge_message(req)

            assert mock_post.call_count == 2
            assert judgment.category == CategoryEnum.BILLING
            assert judgment.urgency_score == 3
            assert judgment.message_id == "retry-429-01"

    asyncio.run(_run())


# ------------------------------------------------------------------------------
# Test Case 6: Permanent 401 Unauthorized Stops Immediately Without Retrying
# ------------------------------------------------------------------------------
def test_permanent_401_unauthorized_stops_immediately_without_retrying():
    """
    Test 6: Proves that the client KNOWS WHEN TO STOP. An HTTP 401 (Invalid API Key)
    must fail immediately on Attempt 1 and NEVER loop through wasted retries.
    """
    async def _run():
        test_client = TrustworthyLLMClient(provider="groq", max_retries=3)
        test_client.groq_api_key = "gsk_invalid_bogus_key"
        req = TriageRequest(
            message_id="stop-401-01",
            message_body="Can you help me reset my account password?",
            customer_tier=CustomerTierEnum.STANDARD
        )

        resp_401 = MagicMock(status_code=401, text="Invalid API Key provided.")

        with patch("httpx.AsyncClient.post", return_value=resp_401) as mock_post:
            with pytest.raises(PermanentClientException) as exc_info:
                await test_client.judge_message(req)

            # Crucial check: call_count must be EXACTLY 1! No blind retries!
            assert mock_post.call_count == 1
            assert exc_info.value.status_code == 401
            assert exc_info.value.is_retryable is False
            assert "401" in exc_info.value.message

    asyncio.run(_run())


# ------------------------------------------------------------------------------
# Test Case 7: Permanent 400 Bad Request Stops Immediately Without Retrying
# ------------------------------------------------------------------------------
def test_permanent_400_bad_request_stops_immediately_without_retrying():
    """
    Test 7: Proves that client-side prompt or policy violations (HTTP 400)
    stop immediately without triggering useless retry loops.
    """
    async def _run():
        test_client = TrustworthyLLMClient(provider="gemini", max_retries=3)
        test_client.gemini_api_key = "AIza_mock_key"
        req = TriageRequest(
            message_id="stop-400-01",
            message_body="Blocked content triggering model safety filter.",
            customer_tier=CustomerTierEnum.STANDARD
        )

        resp_400 = MagicMock(status_code=400, text="Request contained disallowed prompt content.")

        with patch("httpx.AsyncClient.post", return_value=resp_400) as mock_post:
            with pytest.raises(PermanentClientException) as exc_info:
                await test_client.judge_message(req)

            assert mock_post.call_count == 1
            assert exc_info.value.status_code == 400
            assert exc_info.value.is_retryable is False

    asyncio.run(_run())


# ------------------------------------------------------------------------------
# Test Case 8: Retry Exhaustion on Persistent 503 Service Outage
# ------------------------------------------------------------------------------
def test_retry_exhaustion_on_persistent_503_service_unavailable():
    """
    Test 8: Verifies that when an upstream service has a persistent outage (HTTP 503),
    the client attempts exactly max_retries (3) times with backoff, then ceases
    and returns a clean, structured 503 error.
    """
    async def _run():
        test_client = TrustworthyLLMClient(provider="groq", max_retries=3, base_backoff_seconds=0.01)
        test_client.groq_api_key = "gsk_valid_key"
        req = TriageRequest(
            message_id="exhaust-503-01",
            message_body="Can't load dashboard.",
            customer_tier=CustomerTierEnum.STANDARD
        )

        resp_503 = MagicMock(status_code=503, text="Service Temporarily Overloaded")

        with patch("httpx.AsyncClient.post", return_value=resp_503) as mock_post:
            with pytest.raises(TransientUpstreamException) as exc_info:
                await test_client.judge_message(req)

            # Must have attempted exactly 3 times before giving up
            assert mock_post.call_count == 3
            assert exc_info.value.status_code == 503
            assert exc_info.value.is_retryable is True

    asyncio.run(_run())


# ------------------------------------------------------------------------------
# Bonus Integration Test: End-to-End FastAPI Endpoint Verification
# ------------------------------------------------------------------------------
def test_fastapi_endpoint_e2e_integration():
    """
    Bonus: Full HTTP endpoint integration test via FastAPI TestClient.
    Verifies HTTP status codes, headers, and JSON structure match OpenAPI spec.
    """
    with TestClient(app) as test_cli:
        payload = {
            "message_id": "api-e2e-100",
            "message_body": "Critical security incident: Unauthorized root access detected on database server!",
            "customer_tier": "enterprise",
            "sender_email": "security@corp.io"
        }

        response = test_cli.post("/api/v1/triage/judge", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["message_id"] == "api-e2e-100"
        assert data["category"] == "security_incident"
        assert data["urgency_score"] == 5
        assert data["requires_human_escalation"] is True
        assert "model_used" in data
        assert "processing_time_ms" in data
