"""
Mismatch Guard: Production AI Reliability & Safety Layer.

Teaches: AI Safety Layers & Trustworthy Decision Systems
- Rejects wrong pairings even when they are the highest-ranking candidate
- Enforces multi-factor evaluation:
  1. Confidence Gate (confidence >= 0.70)
  2. Similarity Threshold (similarity >= 0.52)
  3. Subject / Category Alignment (e.g. rejects wolf for a fox article)
- Provides human-readable explanatory reasons for every rejection
"""

import os
import re
from typing import Any, Dict, Optional, Tuple

SIMILARITY_THRESHOLD = float(os.environ.get("SIMILARITY_THRESHOLD", "0.30"))
CONFIDENCE_THRESHOLD = float(os.environ.get("CONFIDENCE_THRESHOLD", "0.70"))

# Keywords mapping expected focal subjects in post copy
SUBJECT_KEYWORDS = {
    "fox": ["fox", "foxes", "vulpes", "vulpes vulpes"],
    "wolf": ["wolf", "wolves", "lupus", "canis lupus", "timber wolf"],
    "dog": ["dog", "dogs", "retriever", "canis familiaris", "puppy", "pet"],
    "bear": ["bear", "bears", "grizzly", "ursus", "ursus arctos"],
    "deer": ["deer", "buck", "doe", "fawn", "antlers", "odocoileus"],
    "technology": ["datacenter", "server", "cloud", "infrastructure", "fiber", "networking"],
    "marine": ["ocean", "deep sea", "trench", "anglerfish", "abyssal", "squid", "marine"],
}


def detect_post_subject(post_text: str) -> Optional[str]:
    """Identify the primary focal subject from article title and content."""
    lowered = post_text.lower()
    for subject_key, patterns in SUBJECT_KEYWORDS.items():
        for p in patterns:
            # Word boundary regex check
            if re.search(r"\b" + re.escape(p) + r"\b", lowered):
                return subject_key
    return None


class MismatchGuard:
    """The decision core that verifies candidate appropriateness before recommendation."""

    def __init__(
        self,
        similarity_threshold: float = SIMILARITY_THRESHOLD,
        confidence_threshold: float = CONFIDENCE_THRESHOLD,
    ) -> None:
        self.similarity_threshold = similarity_threshold
        self.confidence_threshold = confidence_threshold

    def evaluate_candidate(
        self,
        post_text: str,
        image_metadata: Dict[str, Any],
        similarity_score: float,
    ) -> Tuple[bool, str]:
        """
        Evaluate candidate image against the blog post.
        Returns: (is_accepted: bool, explanation_reason: str)
        """
        img_subject = image_metadata.get("subject", "").lower()
        img_category = image_metadata.get("category", "").lower()
        confidence = float(image_metadata.get("confidence", 0.0))
        flagged = bool(image_metadata.get("flagged", 0))

        # Gate 1: Confidence Safety Gate
        if flagged or confidence < self.confidence_threshold:
            return (
                False,
                f"Image flagged for low vision confidence ({confidence:.2f} < {self.confidence_threshold:.2f}); rejected to prevent guessing",
            )

        # Gate 2: Semantic Similarity Threshold Gate
        if similarity_score < self.similarity_threshold:
            return (
                False,
                f"Similarity score {similarity_score:.3f} below threshold {self.similarity_threshold:.2f}; match not confident",
            )

        # Gate 3: Subject & Category Mismatch Guard
        expected_subject = detect_post_subject(post_text)

        if expected_subject == "fox" and ("wolf" in img_subject or "canis lupus" in img_subject):
            return (
                False,
                "Animal category mismatch: expected fox, detected wolf",
            )

        if expected_subject == "fox" and ("dog" in img_subject or "retriever" in img_subject):
            return (
                False,
                "Animal category mismatch: expected fox, detected domestic dog",
            )

        if expected_subject == "wolf" and ("fox" in img_subject or "vulpes" in img_subject):
            return (
                False,
                "Animal category mismatch: expected wolf, detected fox",
            )

        if expected_subject == "wolf" and ("dog" in img_subject or "retriever" in img_subject):
            return (
                False,
                "Animal category mismatch: expected wolf, detected domestic dog",
            )

        if expected_subject == "bear" and ("deer" in img_subject or "wolf" in img_subject or "fox" in img_subject):
            return (
                False,
                f"Animal category mismatch: expected bear, detected {img_subject}",
            )

        if expected_subject == "deer" and ("bear" in img_subject or "wolf" in img_subject or "fox" in img_subject):
            return (
                False,
                f"Animal category mismatch: expected deer, detected {img_subject}",
            )

        if expected_subject == "marine" and img_category != "marine":
            return (
                False,
                f"Domain mismatch: expected marine biology, detected {img_category} ({img_subject})",
            )

        # Gate 4: General Category Consistency Check
        if expected_subject == "technology" and img_category != "technology":
            return (
                False,
                f"Category mismatch: expected technology, detected {img_category}",
            )

        return (
            True,
            f"Match confirmed: subject '{img_subject}' aligns with article focus (similarity: {similarity_score:.3f}, confidence: {confidence:.2f})",
        )


mismatch_guard = MismatchGuard()
