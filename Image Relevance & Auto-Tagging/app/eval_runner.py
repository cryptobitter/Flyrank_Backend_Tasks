"""
Evaluation Runner & Quality Benchmarking Suite.

Measures Top-1 Precision against the labeled evaluation dataset (data/eval_dataset.json):
- Evaluates fox vs. wolf boundary defense
- Evaluates rejection of posts with no matching imagery
- Reports precision percentage for README and audit validation
"""

import json
import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from typing import Any, Dict, List

from app.database import get_db
from app.embeddings import embedding_engine
from app.guard import mismatch_guard

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(CURRENT_DIR), "data")
EVAL_DATASET_PATH = os.path.join(DATA_DIR, "eval_dataset.json")


def run_evaluation() -> Dict[str, Any]:
    """Execute evaluation run across labeled ground-truth dataset."""
    if not os.path.exists(EVAL_DATASET_PATH):
        raise FileNotFoundError(f"Evaluation dataset not found at {EVAL_DATASET_PATH}")

    with open(EVAL_DATASET_PATH, "r", encoding="utf-8") as f:
        eval_cases = json.load(f)

    results = []
    correct_count = 0

    # Pre-fetch images mapping into memory to prevent database locks during evaluation
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM images").fetchall()
        images_by_id = {r["id"]: dict(r) for r in rows}

    for case in eval_cases:
        post_id = case["post_id"]
        title = case["title"]
        content = case["content"]
        expected_id = case.get("expected_image_id")
        expected_subject = case.get("expected_subject")
        expected_decision = case.get("expected_decision")

        combined_post_text = f"{title}. {content}"
        post_vec = embedding_engine.generate_embedding(
            text=combined_post_text,
            entity_id=post_id,
            entity_type="post",
        )

        # Retrieve top candidates
        raw_candidates = embedding_engine.rank_candidates(post_vector=post_vec, top_k=5)

        recommended = None
        first_accepted = None
        reasons = []

        for cand_id, sim in raw_candidates:
            img_dict = images_by_id.get(cand_id)
            if not img_dict:
                continue
            accepted, reason = mismatch_guard.evaluate_candidate(
                post_text=combined_post_text,
                image_metadata=img_dict,
                similarity_score=sim,
            )
            if accepted and first_accepted is None:
                first_accepted = {
                    "image_id": cand_id,
                    "subject": img_dict["subject"],
                    "similarity": sim,
                    "reason": reason,
                }
            elif not accepted:
                reasons.append(f"{cand_id}: {reason}")

        # Determine match verdict
        if first_accepted:
            system_decision = "ACCEPTED"
            recommended_id = first_accepted["image_id"]
            recommended_subject = first_accepted["subject"]
        else:
            system_decision = "NO_CONFIDENT_MATCH"
            recommended_id = None
            recommended_subject = None

        # Verify if decision matches ground-truth evaluation expectation
        is_correct = False
        if expected_decision == "NO_CONFIDENT_MATCH" and system_decision == "NO_CONFIDENT_MATCH":
            is_correct = True
        elif expected_decision == "ACCEPTED" and system_decision == "ACCEPTED":
            # Matches either exact ID or exact subject category
            if recommended_id == expected_id or (expected_subject and expected_subject in recommended_subject.lower()):
                is_correct = True

        if is_correct:
            correct_count += 1

        results.append({
            "post_id": post_id,
            "title": title,
            "expected_decision": expected_decision,
            "expected_id": expected_id,
            "system_decision": system_decision,
            "recommended_id": recommended_id,
            "recommended_subject": recommended_subject,
            "is_correct": is_correct,
        })

    total = len(eval_cases)
    top_1_precision = round((correct_count / total) * 100.0, 1) if total > 0 else 0.0

    return {
        "total_test_cases": total,
        "correct_predictions": correct_count,
        "top_1_precision_pct": top_1_precision,
        "benchmark_summary": f"{correct_count}/{total} correct ({top_1_precision}%)",
        "detailed_results": results,
    }


if __name__ == "__main__":
    report = run_evaluation()
    print("=" * 60)
    print("           EVALUATION DATASET REPORT")
    print("=" * 60)
    print(f"Total Cases:       {report['total_test_cases']}")
    print(f"Correct Top-1:     {report['correct_predictions']}")
    print(f"Top-1 Precision:   {report['top_1_precision_pct']}%")
    print("=" * 60)
    for r in report["detailed_results"]:
        status_str = "PASS" if r["is_correct"] else "FAIL"
        print(f"[{status_str}] {r['post_id']}: {r['title'][:40]:<42} -> {r['system_decision']} (Rec: {r['recommended_id']})")
