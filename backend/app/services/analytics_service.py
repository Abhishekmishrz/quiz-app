"""The four analytics formulas: Learning Velocity Index, Fatigue Analysis,
Question Difficulty Index, and Chapter/Subject Mastery Score.

Repositories (app/repositories/event_repo.py) do the per-entity MongoDB
`$group`/`$avg`/`$stdDevPop` aggregation and return small lists of dicts
(at most ~500 rows at this app's scale). Everything here is the
cross-sectional math over that small result set: normalization, Bayesian
shrinkage, ranking, regression slopes. Kept as plain, directly-unit-testable
functions (no Mongo/FastAPI dependency) per the layering rule: services own
all math and validation.
"""
from typing import Any, Dict, List, Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import settings
from app.core.errors import NotFoundError, ValidationAppError
from app.repositories import chapter_repo, event_repo, question_repo, subject_repo, user_repo
from app.utils.stats import bayesian_shrink, coefficient_of_variation, linear_regression_slope, min_max_normalize

BUCKET_SIZE = 5


# ---------------------------------------------------------------------------
# 1. Learning Velocity Index
# ---------------------------------------------------------------------------

def compute_lvi_rows(user_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Pure function: given per-user {total, correct, avg_time_ms, std_time_ms}
    rows (user_id already attached), compute accuracy/speed/consistency/LVI
    for each and return them ranked descending by LVI. Directly unit-testable.
    """
    if not user_rows:
        return []

    raw_times = [r["avg_time_ms"] for r in user_rows]
    speed_scores = min_max_normalize(raw_times, invert=True, clip_percentiles=(5, 95))

    results = []
    for row, speed_score in zip(user_rows, speed_scores):
        total = row["total"]
        correct = row["correct"]
        accuracy = correct / total if total else 0.0
        mean_t = row["avg_time_ms"] or 0.0
        std_t = row["std_time_ms"] or 0.0
        cv = coefficient_of_variation(mean_t, std_t)
        consistency_score = 1.0 if mean_t == 0 else 1.0 / (1.0 + cv)

        lvi = 100 * (
            settings.LVI_WEIGHT_ACCURACY * accuracy
            + settings.LVI_WEIGHT_SPEED * speed_score
            + settings.LVI_WEIGHT_CONSISTENCY * consistency_score
        )
        results.append(
            {
                "user_id": row["user_id"],
                "accuracy": accuracy,
                "avg_response_time_ms": mean_t,
                "consistency_score": consistency_score,
                "lvi": lvi,
            }
        )

    results.sort(key=lambda r: r["lvi"], reverse=True)
    for i, r in enumerate(results, start=1):
        r["rank"] = i
    return results


async def get_learning_velocity(db: AsyncIOMotorDatabase) -> List[Dict[str, Any]]:
    raw_rows = await event_repo.per_user_stats(db)
    if not raw_rows:
        return []

    rows = [
        {
            "user_id": str(r["_id"]),
            "total": r["total"],
            "correct": r["correct"],
            "avg_time_ms": r["avg_time_ms"],
            "std_time_ms": r["std_time_ms"],
        }
        for r in raw_rows
    ]
    computed = compute_lvi_rows(rows)

    user_ids = [ObjectId(r["user_id"]) for r in computed]
    users_by_id = await user_repo.get_users_by_ids(db, user_ids)

    for r in computed:
        user_doc = users_by_id.get(r["user_id"])
        r["user_name"] = user_doc["name"] if user_doc else "Unknown"
    return computed


# ---------------------------------------------------------------------------
# 2. Fatigue Analysis
# ---------------------------------------------------------------------------

def _bucket_label(bucket_index: int) -> str:
    start = bucket_index * BUCKET_SIZE + 1
    end = start + BUCKET_SIZE - 1
    return f"Q{start}-{end}"


def compute_fatigue_buckets(
    raw_buckets: List[Dict[str, Any]], min_attempts_contributing: int = 0
) -> Dict[str, Any]:
    """Pure function: given raw per-bucket {bucket_index, total, correct,
    avg_time_ms, [n_attempts_contributing]} rows, compute the bucket table
    plus deltas/slopes. `min_attempts_contributing` (>=3 for the per-user
    cross-attempt view) filters which buckets feed the trend-slope
    regression -- one long outlier quiz shouldn't dominate a late bucket.
    """
    buckets = []
    for row in sorted(raw_buckets, key=lambda r: r["bucket_index"]):
        bucket_index = int(row["bucket_index"])
        total = row["total"]
        correct = row["correct"]
        accuracy = correct / total if total else 0.0
        buckets.append(
            {
                "bucket_index": bucket_index,
                "bucket_label": _bucket_label(bucket_index),
                "accuracy": accuracy,
                "avg_response_time_ms": row["avg_time_ms"] or 0.0,
                "n_attempts_contributing": row.get("n_attempts_contributing"),
            }
        )

    if not buckets:
        return {
            "buckets": [],
            "accuracy_delta": None,
            "time_delta": None,
            "accuracy_slope": None,
            "time_slope": None,
        }

    trend_eligible = [
        b for b in buckets if (b["n_attempts_contributing"] is None or b["n_attempts_contributing"] >= min_attempts_contributing)
    ]

    accuracy_delta = None
    time_delta = None
    accuracy_slope = None
    time_slope = None
    if len(trend_eligible) >= 2:
        first, last = trend_eligible[0], trend_eligible[-1]
        accuracy_delta = last["accuracy"] - first["accuracy"]
        time_delta = last["avg_response_time_ms"] - first["avg_response_time_ms"]
        xs = [b["bucket_index"] for b in trend_eligible]
        accuracy_slope = linear_regression_slope(xs, [b["accuracy"] for b in trend_eligible])
        time_slope = linear_regression_slope(xs, [b["avg_response_time_ms"] for b in trend_eligible])

    return {
        "buckets": buckets,
        "accuracy_delta": accuracy_delta,
        "time_delta": time_delta,
        "accuracy_slope": accuracy_slope,
        "time_slope": time_slope,
    }


async def get_fatigue(
    db: AsyncIOMotorDatabase, quiz_attempt_id: Optional[str] = None, user_id: Optional[str] = None
) -> Dict[str, Any]:
    if not quiz_attempt_id and not user_id:
        raise ValidationAppError("Provide either quiz_attempt_id or user_id.", code="missing_filter")

    if quiz_attempt_id:
        if not ObjectId.is_valid(quiz_attempt_id):
            raise NotFoundError("Quiz attempt not found.", code="attempt_not_found")
        raw = await event_repo.fatigue_single_attempt(db, ObjectId(quiz_attempt_id))
        raw = [{"bucket_index": r["_id"], **{k: v for k, v in r.items() if k != "_id"}} for r in raw]
        computed = compute_fatigue_buckets(raw, min_attempts_contributing=0)
        computed["mode"] = "quiz_attempt"
        return computed

    if not ObjectId.is_valid(user_id):
        raise NotFoundError("User not found.", code="user_not_found")
    raw = await event_repo.fatigue_user_across_attempts(db, ObjectId(user_id))
    raw = [{"bucket_index": r["_id"], **{k: v for k, v in r.items() if k != "_id"}} for r in raw]
    computed = compute_fatigue_buckets(raw, min_attempts_contributing=3)
    computed["mode"] = "user"
    return computed


# ---------------------------------------------------------------------------
# 3. Question Difficulty Index
# ---------------------------------------------------------------------------

def _confidence_tag(total_attempts: int) -> str:
    if total_attempts < 5:
        return "low"
    if total_attempts < 20:
        return "medium"
    return "high"


def compute_qdi_rows(
    question_rows: List[Dict[str, Any]],
    global_mean_accuracy: float,
    chapter_mean_times: Dict[str, float],
    k: float,
) -> List[Dict[str, Any]]:
    """Pure function: given per-question raw stats plus the global accuracy
    prior and per-chapter time priors, compute shrunk accuracy/time and QDI,
    normalizing time within each chapter's own cohort of questions.
    """
    if not question_rows:
        return []

    # Compute shrunk_accuracy / shrunk_time first (chapter-time-normalize needs shrunk_time).
    enriched = []
    for row in question_rows:
        total = row["total"]
        correct = row["correct"]
        raw_accuracy = correct / total if total else 0.0
        chapter_id = str(row["chapter_id"])
        chapter_mean_time = chapter_mean_times.get(chapter_id, row["avg_time_ms"] or 0.0)

        shrunk_accuracy = bayesian_shrink(correct, total, global_mean_accuracy, k)
        shrunk_time = bayesian_shrink(total * (row["avg_time_ms"] or 0.0), total, chapter_mean_time, k)

        enriched.append(
            {
                "question_id": str(row["_id"]),
                "chapter_id": chapter_id,
                "total_attempts": total,
                "raw_accuracy": raw_accuracy,
                "shrunk_accuracy": shrunk_accuracy,
                "avg_response_time_ms": row["avg_time_ms"] or 0.0,
                "shrunk_time_ms": shrunk_time,
            }
        )

    # Normalize shrunk_time within each chapter's cohort of questions.
    by_chapter: Dict[str, List[int]] = {}
    for idx, row in enumerate(enriched):
        by_chapter.setdefault(row["chapter_id"], []).append(idx)

    norm_time_by_index: Dict[int, float] = {}
    for chapter_id, indices in by_chapter.items():
        times = [enriched[i]["shrunk_time_ms"] for i in indices]
        normalized = min_max_normalize(times, invert=False)
        for i, n in zip(indices, normalized):
            norm_time_by_index[i] = n

    results = []
    for idx, row in enumerate(enriched):
        norm_time = norm_time_by_index[idx]
        qdi = 100 * (
            settings.QDI_WEIGHT_ACCURACY * (1 - row["shrunk_accuracy"]) + settings.QDI_WEIGHT_TIME * norm_time
        )
        results.append(
            {
                **row,
                "qdi": qdi,
                "confidence": _confidence_tag(row["total_attempts"]),
            }
        )

    results.sort(key=lambda r: r["qdi"], reverse=True)
    for i, r in enumerate(results, start=1):
        r["rank"] = i
    return results


async def get_question_difficulty(
    db: AsyncIOMotorDatabase,
    exam_id: Optional[str] = None,
    subject_id: Optional[str] = None,
    chapter_id: Optional[str] = None,
    min_attempts: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
) -> Dict[str, Any]:
    exam_oid = ObjectId(exam_id) if exam_id else None
    subject_oid = ObjectId(subject_id) if subject_id else None
    chapter_oid = ObjectId(chapter_id) if chapter_id else None

    global_stats = await event_repo.global_accuracy_stats(db)
    raw_rows = await event_repo.per_question_stats(db, exam_oid, subject_oid, chapter_oid)
    chapter_times = await event_repo.chapter_mean_times(db)

    computed = compute_qdi_rows(raw_rows, global_stats["mean_accuracy"], chapter_times, settings.SHRINKAGE_K)

    if min_attempts is not None:
        computed = [r for r in computed if r["total_attempts"] >= min_attempts]
        for i, r in enumerate(computed, start=1):
            r["rank"] = i

    total = len(computed)
    page = computed[offset : offset + limit]

    question_ids = [ObjectId(r["question_id"]) for r in page]
    questions_by_id = await question_repo.get_questions_by_ids(db, question_ids)
    for r in page:
        q_doc = questions_by_id.get(r["question_id"])
        r["question_text"] = q_doc["text"] if q_doc else ""

    return {"items": page, "total": total, "limit": limit, "offset": offset}


# ---------------------------------------------------------------------------
# 4. Chapter / Subject Mastery Score
# ---------------------------------------------------------------------------

def compute_mastery_rows(
    pair_rows: List[Dict[str, Any]],
    cohort_mean_accuracy: Dict[str, float],
    k: float,
    prior_key: str,
    speed_scores: Optional[List[float]] = None,
) -> List[Dict[str, Any]]:
    """Pure function: given (user,chapter) pair stats and a mean-accuracy
    prior keyed by `prior_key` (looked up per-row, e.g. "chapter_id"),
    compute shrunk_accuracy_uc / speed_score_uc / MasteryScore for each row.

    `speed_scores`, if given, must be a list positionally aligned with
    `pair_rows` -- this lets callers control exactly which cohort speed is
    normalized within (e.g. a per-chapter cohort across all users, vs. a
    single chapter's own set of user rows). If omitted, speed is normalized
    directly across `pair_rows` itself (correct when pair_rows already IS
    one chapter's full cohort, as in the ?chapter_id= view).
    """
    if not pair_rows:
        return []

    if speed_scores is None:
        raw_times = [r["avg_time_ms"] or 0.0 for r in pair_rows]
        speed_scores = min_max_normalize(raw_times, invert=True, clip_percentiles=(5, 95))

    results = []
    for row, speed_score in zip(pair_rows, speed_scores):
        total = row["total"]
        correct = row["correct"]
        accuracy = correct / total if total else 0.0
        prior = cohort_mean_accuracy.get(row.get(prior_key), 0.5)
        shrunk_accuracy = bayesian_shrink(correct, total, prior, k)

        mastery = 100 * (
            settings.MASTERY_WEIGHT_ACCURACY * shrunk_accuracy + settings.MASTERY_WEIGHT_SPEED * speed_score
        )
        results.append(
            {
                **row,
                "accuracy": accuracy,
                "shrunk_accuracy": shrunk_accuracy,
                "avg_response_time_ms": row["avg_time_ms"] or 0.0,
                "mastery_score": mastery,
            }
        )
    return results


async def get_chapter_mastery_for_user(db: AsyncIOMotorDatabase, user_id: str) -> Dict[str, Any]:
    if not ObjectId.is_valid(user_id):
        raise NotFoundError("User not found.", code="user_not_found")

    rows = await event_repo.user_chapter_stats(db, user_id=ObjectId(user_id))
    if not rows:
        return {"user_id": user_id, "chapters": [], "subjects": []}

    chapter_ids = [r["chapter_id"] for r in rows]
    cohort_accuracy = await event_repo.chapter_cohort_accuracy(db, chapter_ids)

    # speed_score_uc must be normalized within EACH chapter's own cohort of
    # (user,chapter) pairs -- not across this one user's different chapters,
    # and not against a global pool. Pull every user's stats for each of
    # these chapters and, per chapter, locate this user's position in that
    # chapter's own normalized speed distribution.
    cohort_pairs = await event_repo.chapter_cohort_pairs(db, chapter_ids)
    pairs_by_chapter: Dict[str, List[Dict[str, Any]]] = {}
    for p in cohort_pairs:
        pairs_by_chapter.setdefault(str(p["chapter_id"]), []).append(p)

    target_uid = user_id
    pair_rows = []
    speed_scores = []
    for r in rows:
        cid = str(r["chapter_id"])
        chapter_cohort = pairs_by_chapter.get(cid, [])
        times = [p["avg_time_ms"] or 0.0 for p in chapter_cohort]
        normalized = min_max_normalize(times, invert=True, clip_percentiles=(5, 95))
        my_speed_score = 0.5
        for p, n in zip(chapter_cohort, normalized):
            if str(p["user_id"]) == target_uid:
                my_speed_score = n
                break
        speed_scores.append(my_speed_score)
        pair_rows.append(
            {
                "chapter_id": cid,
                "subject_id": str(r["subject_id"]),
                "total": r["total"],
                "correct": r["correct"],
                "avg_time_ms": r["avg_time_ms"],
            }
        )
    computed = compute_mastery_rows(
        pair_rows, cohort_accuracy, settings.SHRINKAGE_K, "chapter_id", speed_scores=speed_scores
    )

    chapters_meta = await chapter_repo.get_chapters_by_ids(db, [ObjectId(r["chapter_id"]) for r in computed])
    subjects_meta = await subject_repo.get_subjects_by_ids(db, [ObjectId(r["subject_id"]) for r in computed])

    chapter_entries = []
    for r in computed:
        ch = chapters_meta.get(r["chapter_id"])
        chapter_entries.append(
            {
                "chapter_id": r["chapter_id"],
                "chapter_name": ch["name"] if ch else None,
                "subject_id": r["subject_id"],
                "total_attempts": r["total"],
                "accuracy": r["accuracy"],
                "shrunk_accuracy": r["shrunk_accuracy"],
                "avg_response_time_ms": r["avg_time_ms"] or 0.0,
                "mastery_score": r["mastery_score"],
            }
        )

    # Subject rollup: attempt-count-weighted mean of chapter mastery scores.
    subject_agg: Dict[str, Dict[str, float]] = {}
    for r in computed:
        sid = r["subject_id"]
        agg = subject_agg.setdefault(sid, {"weighted_sum": 0.0, "weight": 0.0})
        agg["weighted_sum"] += r["mastery_score"] * r["total"]
        agg["weight"] += r["total"]

    subject_rollups = []
    for sid, agg in subject_agg.items():
        subj = subjects_meta.get(sid)
        score = agg["weighted_sum"] / agg["weight"] if agg["weight"] else 0.0
        subject_rollups.append(
            {
                "subject_id": sid,
                "subject_name": subj["name"] if subj else None,
                "mastery_score": score,
                "total_attempts": int(agg["weight"]),
            }
        )
    subject_rollups.sort(key=lambda r: r["mastery_score"], reverse=True)
    chapter_entries.sort(key=lambda r: r["mastery_score"], reverse=True)

    return {"user_id": user_id, "chapters": chapter_entries, "subjects": subject_rollups}


async def get_chapter_mastery_for_chapter(db: AsyncIOMotorDatabase, chapter_id: str) -> Dict[str, Any]:
    if not ObjectId.is_valid(chapter_id):
        raise NotFoundError("Chapter not found.", code="chapter_not_found")

    rows = await event_repo.user_chapter_stats(db, chapter_id=ObjectId(chapter_id))
    if not rows:
        return {"chapter_id": chapter_id, "users": []}

    cohort_accuracy = await event_repo.chapter_cohort_accuracy(db, [ObjectId(chapter_id)])

    pair_rows = [
        {
            "user_id": str(r["user_id"]),
            "chapter_id": str(r["chapter_id"]),
            "total": r["total"],
            "correct": r["correct"],
            "avg_time_ms": r["avg_time_ms"],
        }
        for r in rows
    ]
    computed = compute_mastery_rows(pair_rows, cohort_accuracy, settings.SHRINKAGE_K, "chapter_id")
    computed.sort(key=lambda r: r["mastery_score"], reverse=True)

    users_by_id = await user_repo.get_users_by_ids(db, [ObjectId(r["user_id"]) for r in computed])

    entries = []
    for i, r in enumerate(computed, start=1):
        user_doc = users_by_id.get(r["user_id"])
        entries.append(
            {
                "user_id": r["user_id"],
                "user_name": user_doc["name"] if user_doc else "Unknown",
                "total_attempts": r["total"],
                "accuracy": r["accuracy"],
                "shrunk_accuracy": r["shrunk_accuracy"],
                "avg_response_time_ms": r["avg_time_ms"] or 0.0,
                "mastery_score": r["mastery_score"],
                "rank": i,
            }
        )

    return {"chapter_id": chapter_id, "users": entries}
