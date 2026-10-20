"""
AI Incident Commander:
LLM integration providing automated root-cause analysis, severity classification,
tactical mitigation steps, and executive incident summaries.
"""

import json
import logging
import os
import re
from typing import Optional
import httpx

from schemas import IncidentSeverity, IncidentTriageResult

logger = logging.getLogger("ai_commander")


class AICommander:
    def __init__(self):
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")

    async def analyze_incident(
        self,
        title: str,
        service_name: str,
        raw_logs: str,
        error_count: int = 1,
    ) -> IncidentTriageResult:
        """
        Analyzes incident telemetry with LLM, falling back to deterministic heuristic if API key is unset.
        """
        # 1. Try Groq Cloud if configured
        if self.groq_api_key and self.groq_api_key.strip():
            try:
                return await self._call_groq(title, service_name, raw_logs, error_count)
            except Exception as e:
                logger.warning(f"Groq LLM call failed, falling back to deterministic analyzer: {e}")

        # 2. Deterministic SRE Heuristic Engine (100% offline, zero external dependency)
        return self._evaluate_deterministic(title, service_name, raw_logs, error_count)

    async def _call_groq(
        self, title: str, service: str, logs: str, count: int
    ) -> IncidentTriageResult:
        prompt = f"""
        You are an elite Site Reliability Engineering (SRE) Incident Commander.
        Analyze this production incident and return ONLY valid JSON matching this schema:
        {{
            "severity": "P1_CRITICAL" | "P2_HIGH" | "P3_MEDIUM" | "P4_LOW",
            "root_cause": "technical explanation of what failed",
            "mitigation_steps": "step-by-step commands or actions to restore service",
            "confidence_score": float between 0.0 and 1.0,
            "suggested_runbook_url": "https://wiki.internal/runbooks/service-name",
            "executive_summary": "1-sentence business-level summary of the outage",
            "estimated_impact_minutes": integer
        }}

        Incident Details:
        Title: {title}
        Service: {service}
        Error Count: {count}
        Raw Logs / Stack Trace:
        \"\"\"{logs[:2000]}\"\"\"
        """
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.groq_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "llama-3.1-8b-instant",
                    "messages": [
                        {"role": "system", "content": "You are a production SRE AI. Return ONLY JSON."},
                        {"role": "user", "content": prompt},
                    ],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.1,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            return IncidentTriageResult(**parsed)

    def _evaluate_deterministic(
        self, title: str, service: str, logs: str, count: int
    ) -> IncidentTriageResult:
        """
        SRE heuristic analyzer parsing stack traces for OOM, Deadlocks, Timeouts, and Auth errors.
        """
        text = f"{title} {logs}".lower()

        if any(w in text for w in ["oom", "out of memory", "heap", "killed process", "sigkill"]):
            severity = IncidentSeverity.P1_CRITICAL
            root_cause = f"Memory exhaustion in {service}. JVM/Node heap limit exceeded due to unbounded cache or memory leak."
            mitigation = "1. Scale container memory limits by 2x. 2. Restart crashed pods with restart policy. 3. Inspect recent deployment diff for memory leaks."
            confidence = 0.96
            summary = f"Critical service degradation in {service} due to system Out-Of-Memory termination."
            impact_min = 40

        elif any(w in text for w in ["deadlock", "connection pool", "too many connections", "pool exhausted", "database"]):
            severity = IncidentSeverity.P1_CRITICAL if count > 50 else IncidentSeverity.P2_HIGH
            root_cause = f"Database connection pool starvation or lock contention on primary database cluster."
            mitigation = "1. Terminate long-running idle transactions using pg_terminate_backend. 2. Temporarily increase max_connections in PgBouncer pool. 3. Enable read-replica routing."
            confidence = 0.94
            summary = f"Database pool bottleneck causing transaction backpressure on {service}."
            impact_min = 35

        elif any(w in text for w in ["timeout", "gateway", "504", "502", "connection reset", "econnrefused"]):
            severity = IncidentSeverity.P2_HIGH
            root_cause = f"Upstream dependency connection timeout or gateway latency spike."
            mitigation = "1. Verify network security group rules and upstream health. 2. Enable circuit breaker to shed load. 3. Flush downstream edge DNS caches."
            confidence = 0.91
            summary = f"Network timeouts between {service} and upstream microservices."
            impact_min = 25

        elif any(w in text for w in ["unauthorized", "expired token", "invalid signature", "401", "403"]):
            severity = IncidentSeverity.P3_MEDIUM
            root_cause = f"Authentication signature mismatch or rotated secret desynchronization."
            mitigation = "1. Verify JWT public key rotation sync in Redis. 2. Roll back corrupted auth service config map."
            confidence = 0.95
            summary = f"Client authentication rejection spike in {service}."
            impact_min = 15

        else:
            severity = IncidentSeverity.P2_HIGH if count > 10 else IncidentSeverity.P3_MEDIUM
            root_cause = f"Unhandled application exception in {service} runtime environment."
            mitigation = "1. Roll back to previous container image tag. 2. Collect full debug core dump. 3. File urgent P1 issue in JIRA."
            confidence = 0.88
            summary = f"Operational fault detected in {service} requiring engineering investigation."
            impact_min = 30

        return IncidentTriageResult(
            severity=severity,
            root_cause=root_cause,
            mitigation_steps=mitigation,
            confidence_score=confidence,
            suggested_runbook_url=f"https://wiki.internal/sre/runbooks/{service.lower()}",
            executive_summary=summary,
            estimated_impact_minutes=impact_min,
        )


ai_commander = AICommander()
