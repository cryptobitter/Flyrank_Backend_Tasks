"""
FastAPI Server for AI Image Understanding & Content Matching Engine.

Implements:
1. Batch image ingestion with schema validation & low-confidence flagging
2. Semantic concept matching & vector similarity ranking
3. Mismatch Guard: rejects wrong candidates (e.g. wolf for fox) with explanations
4. Safe 'no confident match' responses when no image clears the bar
5. Human-in-the-loop Review API (approve / reject / inspect why)
6. Per-call AI cost tracking ledger
"""

import json
import os
import sys
import uuid
from typing import Any, Dict, List, Optional

# Ensure local module imports resolve cleanly
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from fastapi import FastAPI, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.batch_worker import batch_manager
from app.cost_tracker import cost_tracker
from app.database import get_db, init_db, utc_now_iso
from app.embeddings import embedding_engine
from app.eval_runner import run_evaluation
from app.guard import mismatch_guard
from app.models import (
    BlogPostCreate,
    CandidateMatch,
    CostLogEntry,
    MatchResponse,
    ReviewAction,
)

# Initialize schema on startup
init_db()

app = FastAPI(
    title="FlyRank AI Image Understanding & Content Matching Engine",
    description="Vision AI auto-tagging with Mismatch Guard protection — good suggestions when confident, safe rejection when not.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =====================================================================
# 1. Batch Image Ingestion & Management
# =====================================================================

@app.post("/api/v1/images/batch-ingest", status_code=status.HTTP_202_ACCEPTED, tags=["Batch Processing"])
def trigger_batch_ingest(max_retries: int = Query(default=2, ge=0, le=5)) -> Dict[str, Any]:
    """
    Trigger asynchronous batch processing over corpus images.
    - Runs vision tagging with Pydantic schema validation
    - Automatically flags low-confidence images (< 0.70)
    - Generates vector embeddings for semantic search
    - Returns job_id for progress polling
    """
    job = batch_manager.trigger_corpus_ingestion(max_retries=max_retries)
    return {
        "message": "Batch image understanding pipeline launched in background.",
        "job": job.to_dict(),
    }


@app.get("/api/v1/images/batch-status/{job_id}", tags=["Batch Processing"])
def get_batch_status(job_id: str) -> Dict[str, Any]:
    """Inspect progress and metrics of a running batch ingestion job."""
    job = batch_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Batch job '{job_id}' not found.")
    return {"job": job.to_dict()}


@app.get("/api/v1/images", tags=["Images"])
def list_images(
    category: Optional[str] = None,
    flagged: Optional[bool] = None,
    limit: int = 50,
) -> Dict[str, Any]:
    """List ingested images with structured metadata and confidence flags."""
    with get_db() as conn:
        query = "SELECT * FROM images WHERE 1=1"
        params: List[Any] = []

        if category:
            query += " AND category = ?"
            params.append(category)
        if flagged is not None:
            query += " AND flagged = ?"
            params.append(1 if flagged else 0)

        query += " ORDER BY id ASC LIMIT ?"
        params.append(limit)

        rows = conn.execute(query, tuple(params)).fetchall()

        results = []
        for r in rows:
            d = dict(r)
            d["attributes"] = json.loads(d["attributes"]) if d["attributes"] else []
            d["flagged"] = bool(d["flagged"])
            results.append(d)

        return {"total": len(results), "images": results}


# =====================================================================
# 2. Blog Posts & Semantic Matching with Mismatch Guard
# =====================================================================

@app.post("/api/v1/posts", status_code=status.HTTP_201_CREATED, tags=["Posts"])
def create_blog_post(payload: BlogPostCreate) -> Dict[str, Any]:
    """Register a new blog post and generate its vector embedding."""
    post_id = payload.id or f"post_{uuid.uuid4().hex[:8]}"
    now = utc_now_iso()

    with get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO posts (id, title, content, created_at) VALUES (?, ?, ?, ?)",
            (post_id, payload.title, payload.content, now),
        )
        conn.commit()

    # Generate semantic embedding
    combined_text = f"{payload.title}. {payload.content}"
    embedding_engine.generate_embedding(
        text=combined_text,
        entity_id=post_id,
        entity_type="post",
    )

    return {"message": "Blog post registered successfully.", "post_id": post_id}


@app.get("/api/v1/posts/{post_id}/images", response_model=MatchResponse, tags=["Matching Engine"])
def match_image_for_post(post_id: str) -> MatchResponse:
    """
    Core Content Matching Pipeline:
    1. Fetches post and retrieves/generates its semantic embedding
    2. Ranks candidate images using cosine similarity
    3. Evaluates candidates through Mismatch Guard (confidence + threshold + category alignment)
    4. Returns recommended image if confident, or 'no_confident_match' with explanation
    """
    with get_db() as conn:
        post_row = conn.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
        if not post_row:
            raise HTTPException(status_code=404, detail=f"Blog post '{post_id}' not found.")

        post_title = post_row["title"]
        post_content = post_row["content"]
        combined_text = f"{post_title}. {post_content}"

        # Fetch or generate post embedding
        post_emb_row = conn.execute(
            "SELECT vector FROM embeddings WHERE entity_id = ? AND entity_type = 'post'",
            (post_id,),
        ).fetchone()

        if post_emb_row:
            post_vec = json.loads(post_emb_row["vector"])
        else:
            post_vec = embedding_engine.generate_embedding(
                text=combined_text,
                entity_id=post_id,
                entity_type="post",
            )

        # Retrieve top 8 ranked candidates by cosine similarity
        raw_candidates = embedding_engine.rank_candidates(post_vector=post_vec, top_k=8)

        evaluated_candidates: List[CandidateMatch] = []
        recommended: Optional[CandidateMatch] = None
        rejection_reasons: List[str] = []

        for img_id, sim_score in raw_candidates:
            img_row = conn.execute("SELECT * FROM images WHERE id = ?", (img_id,)).fetchone()
            if not img_row:
                continue

            img_dict = dict(img_row)
            accepted, reason = mismatch_guard.evaluate_candidate(
                post_text=combined_text,
                image_metadata=img_dict,
                similarity_score=sim_score,
            )

            candidate_obj = CandidateMatch(
                image_id=img_id,
                subject=img_dict["subject"],
                category=img_dict["category"],
                caption=img_dict["caption"],
                confidence=img_dict["confidence"],
                similarity_score=sim_score,
                guard_decision="ACCEPTED" if accepted else "REJECTED",
                rejection_reason=None if accepted else reason,
            )
            evaluated_candidates.append(candidate_obj)

            if accepted and recommended is None:
                recommended = candidate_obj
            elif not accepted:
                rejection_reasons.append(f"Candidate {img_id} ({img_dict['subject']}): {reason}")

        # Record suggestion in DB
        decision_label = "ACCEPTED" if recommended else "REJECTED"
        verdict_reason = recommended.rejection_reason if recommended else "; ".join(rejection_reasons[:2])
        conn.execute(
            """
            INSERT INTO suggestions (id, post_id, image_id, similarity_score, decision, reason, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"sug_{uuid.uuid4().hex[:10]}",
                post_id,
                recommended.image_id if recommended else "none",
                recommended.similarity_score if recommended else 0.0,
                decision_label,
                verdict_reason or "No match passed guard",
                utc_now_iso(),
            ),
        )
        conn.commit()

        if recommended:
            return MatchResponse(
                post_id=post_id,
                post_title=post_title,
                status="matched",
                recommended_image=recommended,
                top_candidates=evaluated_candidates,
                explanation=f"Selected '{recommended.image_id}' ({recommended.subject}) with similarity {recommended.similarity_score:.3f}. All mismatch guard checks passed.",
            )
        else:
            return MatchResponse(
                post_id=post_id,
                post_title=post_title,
                status="no_confident_match",
                recommended_image=None,
                top_candidates=evaluated_candidates,
                explanation="No confident match found. Candidates evaluated were either below the similarity threshold or failed category alignment guard rules.",
            )


# =====================================================================
# 3. Human-in-the-Loop Review API
# =====================================================================

@app.post("/api/v1/posts/{post_id}/review", tags=["Review Workflow"])
def review_image_pairing(post_id: str, action: ReviewAction) -> Dict[str, Any]:
    """Human-in-the-loop review workflow to approve or reject suggested pairings."""
    with get_db() as conn:
        rev_id = f"rev_{uuid.uuid4().hex[:10]}"
        conn.execute(
            """
            INSERT INTO reviews (id, post_id, image_id, decision, feedback, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (rev_id, post_id, action.image_id, action.decision, action.feedback or "", utc_now_iso()),
        )
        conn.commit()

    return {
        "message": f"Pairing for post '{post_id}' marked as '{action.decision}'.",
        "review_id": rev_id,
    }


# =====================================================================
# 4. Cost Tracking & Evaluation Benchmarks
# =====================================================================

@app.get("/api/v1/costs", tags=["Cost Tracking"])
def get_cost_ledger() -> Dict[str, Any]:
    """Inspect all recorded AI vision and embedding calls and total USD costs."""
    return {"cost_summary": cost_tracker.get_summary()}


@app.get("/api/v1/eval/run", tags=["Evaluation"])
def run_evaluation_benchmark() -> Dict[str, Any]:
    """Execute evaluation run across the 12-case labeled dataset and report top-1 precision."""
    report = run_evaluation()
    return report


@app.get("/", tags=["System"])
def root_info() -> Dict[str, Any]:
    return {
        "service": "FlyRank AI Image Understanding & Content Matching Engine",
        "status": "operational",
        "endpoints": {
            "batch_ingest": "/api/v1/images/batch-ingest",
            "list_images": "/api/v1/images",
            "create_post": "/api/v1/posts",
            "match_image": "/api/v1/posts/{post_id}/images",
            "review": "/api/v1/posts/{post_id}/review",
            "costs": "/api/v1/costs",
            "evaluation": "/api/v1/eval/run",
            "docs": "/docs",
        },
    }
