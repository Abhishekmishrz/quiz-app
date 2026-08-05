"""Generates historical quiz_attempts + question_events for every user so a
freshly seeded DB already has rich, non-flat analytics data.

Design notes (see the implementation plan for full rationale):
  - Zipf-weighted chapter selection so some chapters/questions get far more
    attempts than others -- this is what gives QDI's Bayesian shrinkage
    something real to demonstrate (low-attempt questions get pulled toward
    the global mean).
  - is_correct ~ Bernoulli(p) where p combines the user's base_accuracy,
    the question's hidden seed_difficulty, a within-quiz fatigue penalty
    that grows with question_index (scaled by the user's fatigue_tendency),
    and a small improvement bonus for more recent attempts (scaled by the
    user's improvement_trend).
  - response_duration_ms ~ Lognormal parameterized from the user's speed
    profile (mean/std converted to lognormal mu/sigma via method of
    moments), inflated by fatigue as question_index grows, floored so it's
    never negative (or implausibly ~0).
  - A fixed reference `now` and a seeded `random.Random` are threaded through
    everything for reproducibility -- no bare `datetime.now()` calls deep in
    generation logic.
"""
import math
import random
from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple

from bson import ObjectId

OPTION_KEYS = ["A", "B", "C", "D"]
LOOKBACK_DAYS = 60


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def _logit(p: float) -> float:
    p = min(max(p, 1e-4), 1 - 1e-4)
    return math.log(p / (1 - p))


def _lognormal_params(mean: float, std: float) -> Tuple[float, float]:
    """Method-of-moments conversion from linear-space (mean, std) to the
    (mu, sigma) parameters of the underlying normal in log-space."""
    mean = max(mean, 1.0)
    std = max(std, 1.0)
    sigma_sq = math.log(1 + (std / mean) ** 2)
    sigma = math.sqrt(sigma_sq)
    mu = math.log(mean) - sigma_sq / 2
    return mu, sigma


def _zipf_weight_map(rng: random.Random, ids: List[Any]) -> Dict[Any, float]:
    """Assign each id a Zipf(s=1) weight after a random rank shuffle, so
    which chapters end up "popular" vs. "rare" isn't just insertion order."""
    shuffled = ids[:]
    rng.shuffle(shuffled)
    return {item: 1.0 / rank for rank, item in enumerate(shuffled, start=1)}


def generate_events(
    rng: random.Random,
    now: datetime,
    users: List[Dict[str, Any]],
    skill_profiles: Dict[str, Dict[str, float]],
    chapters: List[Dict[str, Any]],
    questions: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Returns (quiz_attempts, question_events) ready for insert_many."""

    questions_by_chapter: Dict[str, List[Dict[str, Any]]] = {}
    for q in questions:
        questions_by_chapter.setdefault(str(q["chapter_id"]), []).append(q)

    # Only chapters that actually have questions can be attempted.
    attemptable_chapters = [c for c in chapters if questions_by_chapter.get(str(c["_id"]))]
    chapter_weights = _zipf_weight_map(rng, [c["_id"] for c in attemptable_chapters])
    chapters_by_id = {c["_id"]: c for c in attemptable_chapters}

    weighted_chapter_ids = list(chapter_weights.keys())
    weights = [chapter_weights[cid] for cid in weighted_chapter_ids]

    quiz_attempts: List[Dict[str, Any]] = []
    question_events: List[Dict[str, Any]] = []

    for user in users:
        user_id = user["_id"]
        profile = skill_profiles[str(user_id)]
        base_accuracy = profile["base_accuracy"]
        fatigue_tendency = profile["fatigue_tendency"]
        improvement_trend = profile["improvement_trend"]
        mu_speed, sigma_speed = _lognormal_params(profile["base_speed_mean_ms"], profile["base_speed_std_ms"])

        n_attempts = rng.randint(15, 40)

        # Spread attempt ages over the last ~60 days; sort so index 0 is the
        # oldest (least "recent") attempt.
        ages_days = sorted(rng.uniform(0.1, LOOKBACK_DAYS) for _ in range(n_attempts))

        for age_days in ages_days:
            chosen_chapter_id = rng.choices(weighted_chapter_ids, weights=weights, k=1)[0]
            chapter = chapters_by_id[chosen_chapter_id]
            chapter_questions = questions_by_chapter[str(chosen_chapter_id)]

            quiz_length = min(10, len(chapter_questions))
            sampled_questions = rng.sample(chapter_questions, quiz_length)
            sampled_ids = [q["_id"] for q in sampled_questions]

            option_order: Dict[str, List[str]] = {}
            for q in sampled_questions:
                keys = [opt["key"] for opt in q["options"]]
                shuffled = keys[:]
                rng.shuffle(shuffled)
                option_order[str(q["_id"])] = shuffled

            started_at = now - timedelta(days=age_days, seconds=rng.randint(0, 86400))
            recency_score = max(0.0, 1.0 - age_days / LOOKBACK_DAYS)

            attempt_id = ObjectId()
            cursor_time = started_at

            for q_index, question in enumerate(sampled_questions):
                seed_difficulty = question["seed_difficulty"]

                # --- correctness probability ---
                base_logit = _logit(base_accuracy)
                difficulty_effect = -3.0 * (seed_difficulty - 0.5)
                fatigue_effect = -fatigue_tendency * (q_index / max(quiz_length - 1, 1)) * 2.0
                improvement_effect = improvement_trend * recency_score * 1.5
                p_correct = _sigmoid(base_logit + difficulty_effect + fatigue_effect + improvement_effect)
                is_correct = rng.random() < p_correct

                # --- response duration ---
                duration = math.exp(rng.gauss(mu_speed, sigma_speed))
                duration *= 1 + 0.3 * seed_difficulty
                duration *= 1 + fatigue_tendency * (q_index / max(quiz_length - 1, 1)) * 0.5
                duration_ms = max(duration, 800.0)  # floor: never ~0 / negative

                shown_at = cursor_time
                submitted_at = shown_at + timedelta(milliseconds=duration_ms)
                cursor_time = submitted_at

                correct_option = question["correct_option"]
                if is_correct:
                    selected_option = correct_option
                else:
                    wrong_keys = [opt["key"] for opt in question["options"] if opt["key"] != correct_option]
                    selected_option = rng.choice(wrong_keys) if wrong_keys else correct_option

                question_events.append(
                    {
                        "_id": ObjectId(),
                        "quiz_attempt_id": attempt_id,
                        "user_id": user_id,
                        "question_id": question["_id"],
                        "exam_id": question["exam_id"],
                        "subject_id": question["subject_id"],
                        "chapter_id": question["chapter_id"],
                        "question_index": q_index,
                        "shown_at": shown_at,
                        "submitted_at": submitted_at,
                        "response_duration_ms": duration_ms,
                        "selected_option": selected_option,
                        "is_correct": is_correct,
                    }
                )

            completed_at = cursor_time
            quiz_attempts.append(
                {
                    "_id": attempt_id,
                    "user_id": user_id,
                    "exam_id": chapter["exam_id"],
                    "subject_id": chapter["subject_id"],
                    "chapter_id": chapter["_id"],
                    "question_ids": sampled_ids,
                    "option_order": option_order,
                    "status": "completed",
                    "total_questions": quiz_length,
                    "started_at": started_at,
                    "completed_at": completed_at,
                }
            )

    return quiz_attempts, question_events
