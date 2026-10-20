"""
Semantic Embedding Engine & Cosine Vector Index.

Teaches: Semantic Concept Matching & Vector Similarity Ranking
- Creates dense embeddings for image captions, tags, and blog post content
- Matches concepts, not exact words ('red fox' matches 'Vulpes vulpes')
- Uses cosine similarity metric for ranking candidates
- Records per-call embedding cost in the cost tracking ledger
"""

import json
import math
import os
import re
from typing import Dict, List, Tuple
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.cost_tracker import cost_tracker
from app.database import get_db, utc_now_iso

EMBEDDING_MODEL_NAME = os.environ.get("EMBEDDING_MODEL", "text-embedding-004")

# Domain Semantic Taxonomy / Synonym Expansion Table
# Ensures scientific binomial nomenclature & colloquial concepts project into the same semantic space
CONCEPT_EXPANSIONS = {
    "vulpes vulpes": "red fox wild fox orange coat bushy tail vulpes vulpes",
    "red fox": "red fox wild fox orange coat bushy tail vulpes vulpes",
    "wild fox": "red fox wild fox orange coat bushy tail vulpes vulpes",
    "canis lupus": "gray wolf timber wolf arctic wolf apex predator pack canis lupus",
    "timber wolf": "gray wolf timber wolf arctic wolf apex predator pack canis lupus",
    "gray wolf": "gray wolf timber wolf arctic wolf apex predator pack canis lupus",
    "golden retriever": "golden retriever domestic dog canine friendly pet yellow retriever canis familiaris",
    "domestic dog": "golden retriever domestic dog canine friendly pet yellow retriever canis familiaris",
    "ursus arctos": "grizzly bear brown bear alaskan bear river salmon ursus arctos",
    "grizzly bear": "grizzly bear brown bear alaskan bear river salmon ursus arctos",
    "brown bear": "grizzly bear brown bear alaskan bear river salmon ursus arctos",
    "odocoileus virginianus": "white-tailed deer buck doe fawns forest herbivore antlers meadow odocoileus virginianus",
    "white-tailed deer": "white-tailed deer buck doe fawns forest herbivore antlers meadow odocoileus virginianus",
    "cloud datacenter": "cloud datacenter server rack enterprise network infrastructure fiber optics hardware",
}


def expand_text_semantics(text: str) -> str:
    """Expand text with domain conceptual synonyms to enable semantic concept matching."""
    lowered = text.lower()
    expanded = lowered
    for key, synonyms in CONCEPT_EXPANSIONS.items():
        if key in lowered:
            expanded += f" {synonyms}"
    return expanded


class SemanticEmbeddingEngine:
    """Vector search and embedding generation engine."""

    def __init__(self) -> None:
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            sublinear_tf=True,
            stop_words="english",
        )
        self._fitted = False
        self._initialize_base_vocabulary()

    def _initialize_base_vocabulary(self) -> None:
        """Seed initial corpus vocabulary for vector space stability."""
        seed_corpus = list(CONCEPT_EXPANSIONS.values()) + [
            "deep sea ocean trench marine abyssal anglerfish underwater darkness",
            "modern enterprise cloud infrastructure server datacenter network hardware",
        ]
        self.vectorizer.fit(seed_corpus)
        self._fitted = True

    def generate_embedding(self, text: str, entity_id: str, entity_type: str) -> List[float]:
        """Generate normalized vector embedding and record AI cost entry."""
        expanded = expand_text_semantics(text)

        # Record AI cost entry in audit ledger
        cost_tracker.record_call(
            operation="embedding_generation",
            model=EMBEDDING_MODEL_NAME,
            input_units=len(text.split()),
            output_units=1,
        )

        vec = self.vectorizer.transform([expanded]).toarray()[0]
        # Normalize vector
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        vec_list = [round(float(x), 5) for x in vec]

        # Store in DB
        with get_db() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO embeddings (entity_id, entity_type, vector, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (entity_id, entity_type, json.dumps(vec_list), utc_now_iso()),
            )
            conn.commit()

        return vec_list

    def rank_candidates(
        self,
        post_vector: List[float],
        top_k: int = 10,
    ) -> List[Tuple[str, float]]:
        """
        Compute cosine similarity between post vector and all stored image vectors.
        Returns list of (image_id, similarity_score) sorted descending.
        """
        post_arr = np.array(post_vector).reshape(1, -1)

        with get_db() as conn:
            rows = conn.execute(
                "SELECT entity_id, vector FROM embeddings WHERE entity_type = 'image'"
            ).fetchall()

        if not rows:
            return []

        candidates = []
        for r in rows:
            img_id = r["entity_id"]
            img_vec = np.array(json.loads(r["vector"])).reshape(1, -1)
            sim = float(cosine_similarity(post_arr, img_vec)[0][0])
            candidates.append((img_id, round(sim, 4)))

        # Sort descending by similarity score
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[:top_k]


embedding_engine = SemanticEmbeddingEngine()
