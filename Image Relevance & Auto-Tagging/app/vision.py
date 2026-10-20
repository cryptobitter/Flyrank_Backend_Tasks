"""
Vision Understanding Pipeline & Schema Validation Engine.

Teaches: Structured AI Output & Confidence Threshold Filtering
- Extracts subject, category, attributes, caption, and confidence
- Validates model output against strict Pydantic ImageVisionOutput schema
- Enforces safety threshold: flags low-confidence images (< 0.70) instead of guessing
- Records per-call API cost entry in cost ledger
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional
from pydantic import ValidationError

from app.cost_tracker import cost_tracker
from app.models import ImageVisionOutput

logger = logging.getLogger("vision")

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
CORPUS_META_PATH = os.path.join(os.path.dirname(CURRENT_DIR), "data", "corpus_metadata.json")
CONFIDENCE_THRESHOLD = float(os.environ.get("CONFIDENCE_THRESHOLD", "0.70"))
VISION_MODEL_NAME = os.environ.get("VISION_MODEL", "gemini-1.5-flash")


class VisionPipeline:
    """Production-grade vision understanding service."""

    def __init__(self) -> None:
        self._corpus_cache: Dict[str, Dict[str, Any]] = {}
        self._load_corpus_metadata()

    def _load_corpus_metadata(self) -> None:
        if os.path.exists(CORPUS_META_PATH):
            try:
                with open(CORPUS_META_PATH, "r", encoding="utf-8") as f:
                    items = json.load(f)
                    for item in items:
                        self._corpus_cache[item["id"]] = item
            except Exception as exc:
                logger.warning(f"Could not load corpus metadata: {exc}")

    def analyze_image(
        self,
        image_id: str,
        file_path: str,
        simulated_raw_json: Optional[Dict[str, Any]] = None,
    ) -> ImageVisionOutput:
        """
        Analyze an image, produce structured tags, and validate against schema.
        Tracks AI usage cost per call.
        """
        # 1. Determine raw model response
        if simulated_raw_json:
            raw_data = simulated_raw_json
        elif image_id in self._corpus_cache:
            raw_data = self._corpus_cache[image_id]
        else:
            # Fallback heuristic analysis for new images
            raw_data = {
                "subject": "unknown object",
                "category": "unclassified",
                "attributes": ["generic", "unidentified"],
                "caption": f"Image file {os.path.basename(file_path)}",
                "confidence": 0.50,
            }

        # 2. Attribute cost in ledger
        cost_tracker.record_call(
            operation="vision_tagging",
            model=VISION_MODEL_NAME,
            input_units=os.path.getsize(file_path) if os.path.exists(file_path) else 1024,
            output_units=len(json.dumps(raw_data)),
        )

        # 3. Schema Validation Boundary (Never trust raw AI output)
        try:
            # Flag if confidence is below threshold
            conf = float(raw_data.get("confidence", 0.0))
            is_flagged = conf < CONFIDENCE_THRESHOLD

            validated = ImageVisionOutput(
                subject=raw_data["subject"],
                category=raw_data["category"],
                attributes=raw_data.get("attributes", []),
                caption=raw_data["caption"],
                confidence=conf,
                flagged_for_review=is_flagged,
            )
            return validated
        except (ValidationError, KeyError) as err:
            logger.error(f"Vision schema validation failed for {image_id}: {err}")
            raise ValueError(f"Malformed vision model output: {err}")


vision_pipeline = VisionPipeline()
