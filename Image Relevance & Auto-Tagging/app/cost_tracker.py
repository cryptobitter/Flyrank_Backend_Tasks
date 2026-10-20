"""
Per-Call AI Cost Tracking Module.

Ensures every vision and embedding call is attributed with token count and cost,
fulfilling the core requirement: 'Track costs per call, even inside a free tier.'
"""

import os
import threading
import uuid
from typing import Any, Dict, List, Literal, Optional

from app.database import get_db, utc_now_iso

# Default pricing parameters (USD)
VISION_CALL_COST = float(os.environ.get("COST_PER_VISION_CALL_USD", "0.0001"))
EMBED_CALL_COST = float(os.environ.get("COST_PER_EMBED_CALL_USD", "0.00002"))


class CostTracker:
    """Thread-safe cost tracking ledger."""

    def __init__(self) -> None:
        self._lock = threading.Lock()

    def record_call(
        self,
        operation: Literal["vision_tagging", "embedding_generation"],
        model: str,
        input_units: int,
        output_units: int = 1,
        custom_cost_usd: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Record an individual AI call with token units and financial cost."""
        entry_id = f"cost_{uuid.uuid4().hex[:12]}"
        now = utc_now_iso()

        if custom_cost_usd is not None:
            cost = custom_cost_usd
        elif operation == "vision_tagging":
            cost = VISION_CALL_COST
        else:
            cost = EMBED_CALL_COST

        with self._lock:
            with get_db() as conn:
                conn.execute(
                    """
                    INSERT INTO cost_logs (
                        id, operation, model, input_units, output_units, cost_usd, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (entry_id, operation, model, input_units, output_units, cost, now),
                )
                conn.commit()

        return {
            "id": entry_id,
            "operation": operation,
            "model": model,
            "cost_usd": cost,
            "timestamp": now,
        }

    def get_summary(self) -> Dict[str, Any]:
        """Return aggregated cost statistics across all recorded operations."""
        with get_db() as conn:
            summary = conn.execute(
                """
                SELECT
                    COUNT(*) AS total_calls,
                    ROUND(SUM(cost_usd), 6) AS total_cost_usd,
                    SUM(input_units) AS total_input_units,
                    SUM(CASE WHEN operation = 'vision_tagging' THEN 1 ELSE 0 END) AS vision_calls,
                    SUM(CASE WHEN operation = 'embedding_generation' THEN 1 ELSE 0 END) AS embedding_calls
                FROM cost_logs
                """
            ).fetchone()

            breakdown = conn.execute(
                """
                SELECT operation, model, COUNT(*) AS calls, ROUND(SUM(cost_usd), 6) AS cost
                FROM cost_logs
                GROUP BY operation, model
                """
            ).fetchall()

            return {
                "total_calls": summary["total_calls"] or 0,
                "total_cost_usd": summary["total_cost_usd"] or 0.0,
                "total_input_units": summary["total_input_units"] or 0,
                "vision_calls": summary["vision_calls"] or 0,
                "embedding_calls": summary["embedding_calls"] or 0,
                "breakdown": [dict(r) for r in breakdown],
            }


cost_tracker = CostTracker()
