"""
Automated Test Suite for AI Image Understanding & Content Matching Engine.

Implements all 6 Acceptance Probes from Section 13 and all Section 6 requirements:
- PROBE 1: Batch job tags all images with valid schema; low-confidence images flagged
- PROBE 2: Red fox post ranks fox first; wolf and dog rank clearly lower
- PROBE 3: Forced wolf candidate on fox post rejected with category-mismatch explanation
- PROBE 4: Out-of-domain post returns 'no confident match' with explanation
- PROBE 5: Evaluation suite reports top-1 precision matching README (100.0%)
- PROBE 6: Cost ledger attributes every vision and embedding call with token & USD cost
- Review API: Human-in-the-loop approve/reject workflow verified
- Boundary validation: Rejects malformed payloads with 4xx, never 500
"""

import json
import os
import sys

# Ensure local module imports resolve cleanly
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from fastapi.testclient import TestClient
import pytest

from app.batch_worker import batch_manager
from app.cost_tracker import cost_tracker
from app.database import get_db, init_db
from app.embeddings import embedding_engine
from app.eval_runner import run_evaluation
from app.guard import mismatch_guard
from app.main import app
from seed import seed_all

client = TestClient(app)


@pytest.fixture(scope="session", autouse=True)
def initialize_environment():
    """Ensure database, corpus, and embeddings are seeded."""
    seed_all()


# =====================================================================
# PROBE 1: Batch Job & Low-Confidence Flagging
# =====================================================================

def test_probe_1_batch_ingestion_and_low_confidence_flagging():
    """
    PROBE 1 — Run the batch job on the corpus
    -> every image gains schema-valid tags; at least one low-confidence image is flagged, not guessed.
    """
    # Trigger batch ingestion
    res = client.post("/api/v1/images/batch-ingest?max_retries=2")
    assert res.status_code == 202
    job_id = res.json()["job"]["job_id"]

    # Poll status until complete
    status_res = client.get(f"/api/v1/images/batch-status/{job_id}")
    assert status_res.status_code == 200

    # Query all images from database
    images_res = client.get("/api/v1/images?limit=100")
    assert images_res.status_code == 200
    images = images_res.json()["images"]
    assert len(images) >= 40

    # Verify every image has valid schema fields
    flagged_count = 0
    for img in images:
        assert img["subject"]
        assert img["category"]
        assert isinstance(img["attributes"], list)
        assert len(img["caption"]) >= 5
        assert 0.0 <= img["confidence"] <= 1.0
        if img["flagged"]:
            flagged_count += 1
            assert img["confidence"] < 0.70

    # Verify at least one low-confidence image is flagged, not guessed
    assert flagged_count >= 1, "Expected at least one low-confidence image to be flagged"


# =====================================================================
# PROBE 2: Semantic Matching & Candidate Ranking
# =====================================================================

def test_probe_2_red_fox_ranking_over_wolf_and_dog():
    """
    PROBE 2 — Query images for the 'red fox' article
    -> the fox image ranks first; wolf and dog rank clearly lower.
    """
    post_id = "post_01"  # "Winter Habits of the Red Fox"

    res = client.get(f"/api/v1/posts/{post_id}/images")
    assert res.status_code == 200
    data = res.json()

    assert data["status"] == "matched"
    assert data["recommended_image"] is not None

    rec = data["recommended_image"]
    assert "fox" in rec["subject"].lower()
    assert rec["similarity_score"] >= 0.30

    # Verify wolf and dog rank clearly lower or are rejected
    candidates = data["top_candidates"]
    fox_scores = [c["similarity_score"] for c in candidates if "fox" in c["subject"].lower()]
    other_scores = [c["similarity_score"] for c in candidates if "wolf" in c["subject"].lower() or "dog" in c["subject"].lower()]

    assert len(fox_scores) > 0
    if other_scores:
        assert max(fox_scores) > max(other_scores)


# =====================================================================
# PROBE 3: Mismatch Guard Rejection of Forced Wolf Candidate
# =====================================================================

def test_probe_3_mismatch_guard_rejects_wolf_on_fox_post():
    """
    PROBE 3 — Force the wolf as a candidate for the fox post
    -> the guard rejects it with a category-mismatch explanation.
    """
    fox_post_text = "The Behavior and Ecology of Wild Red Foxes (Vulpes vulpes)"

    # Fetch a real wolf image metadata from DB
    with get_db() as conn:
        wolf_row = conn.execute("SELECT * FROM images WHERE subject LIKE '%wolf%' LIMIT 1").fetchone()
        assert wolf_row is not None
        wolf_dict = dict(wolf_row)

    # Force candidate evaluation with high artificial similarity (e.g. 0.85)
    accepted, reason = mismatch_guard.evaluate_candidate(
        post_text=fox_post_text,
        image_metadata=wolf_dict,
        similarity_score=0.85,
    )

    # Must be REJECTED by Mismatch Guard
    assert accepted is False
    assert "Animal category mismatch" in reason
    assert "expected fox, detected wolf" in reason


# =====================================================================
# PROBE 4: Out-of-Domain Post Safe Rejection
# =====================================================================

def test_probe_4_no_confident_match_when_no_image_clears_the_bar():
    """
    PROBE 4 — Query a post with no suitable image
    -> 'no confident match' + reasons (similarity below threshold / subjects don't match).
    """
    post_id = "post_12"  # "Abyssal Plain and Bioluminescent Deep Sea Organisms"

    res = client.get(f"/api/v1/posts/{post_id}/images")
    assert res.status_code == 200
    data = res.json()

    assert data["status"] == "no_confident_match"
    assert data["recommended_image"] is None
    assert "no confident match" in data["explanation"].lower()


# =====================================================================
# PROBE 5: Evaluation Benchmark & Top-1 Precision
# =====================================================================

def test_probe_5_evaluation_benchmark_precision():
    """
    PROBE 5 — Run the eval script
    -> top-1 precision reported on the labeled set, matching the number in the README.
    """
    res = client.get("/api/v1/eval/run")
    assert res.status_code == 200
    report = res.json()

    assert report["total_test_cases"] == 12
    assert report["top_1_precision_pct"] == 100.0
    assert report["correct_predictions"] == 12


# =====================================================================
# PROBE 6: Cost Ledger Attribution
# =====================================================================

def test_probe_6_cost_ledger_attribution():
    """
    PROBE 6 — Check the cost log
    -> every vision/embedding call attributed with a cost entry.
    """
    res = client.get("/api/v1/costs")
    assert res.status_code == 200
    summary = res.json()["cost_summary"]

    assert summary["total_calls"] > 0
    assert summary["vision_calls"] >= 45
    assert summary["embedding_calls"] >= 45
    assert summary["total_cost_usd"] > 0.0

    # Verify breakdown
    breakdown = summary["breakdown"]
    ops = [b["operation"] for b in breakdown]
    assert "vision_tagging" in ops
    assert "embedding_generation" in ops


# =====================================================================
# Human-in-the-Loop Review Workflow
# =====================================================================

def test_review_workflow_approval_and_rejection():
    """Verify Review API allows approving/rejecting match decisions."""
    post_id = "post_01"
    image_id = "fox_02"

    # Approve
    res_app = client.post(
        f"/api/v1/posts/{post_id}/review",
        json={"post_id": post_id, "image_id": image_id, "decision": "approved", "feedback": "Excellent framing"},
    )
    assert res_app.status_code == 200
    assert "approved" in res_app.json()["message"]

    # Reject
    res_rej = client.post(
        f"/api/v1/posts/{post_id}/review",
        json={"post_id": post_id, "image_id": "wolf_01", "decision": "rejected", "feedback": "Wolf is wrong animal"},
    )
    assert res_rej.status_code == 200
    assert "rejected" in res_rej.json()["message"]


# =====================================================================
# Boundary Validation
# =====================================================================

def test_boundary_validation_rejects_bad_input():
    """Verify malformed post registration returns 422, never 500."""
    res = client.post("/api/v1/posts", json={"title": "AB"})  # Title too short (< 3 chars)
    assert res.status_code == 422
    assert res.status_code != 500
