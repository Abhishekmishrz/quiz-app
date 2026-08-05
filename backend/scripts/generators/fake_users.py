"""Generates 50 Faker users plus, for each, a hidden skill profile used only
by fake_events.py to drive realistic Bernoulli/Lognormal event generation.
The skill profile is NEVER stored on the user document itself.
"""
import random
from datetime import datetime
from typing import Any, Dict, List, Tuple

from bson import ObjectId
from faker import Faker

fake = Faker()


def generate_users(rng: random.Random, now: datetime, count: int = 50) -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, float]]]:
    """Returns (user_docs, skill_profiles) where skill_profiles is keyed by
    the string form of each user's _id.

    Skill profile fields:
      - base_accuracy: Beta-distributed, spread ~0.35-0.90 across the cohort
      - base_speed_mean_ms / base_speed_std_ms: covers fast/slow x accurate/erratic combos
      - fatigue_tendency: in [0,1]
      - improvement_trend: in [-1,1]-ish, positive = gets better with more recent attempts
    """
    users: List[Dict[str, Any]] = []
    skill_profiles: Dict[str, Dict[str, float]] = {}

    for _ in range(count):
        user_id = ObjectId()
        name = fake.name()
        email = fake.unique.email()

        users.append(
            {
                "_id": user_id,
                "name": name,
                "email": email,
                "avatar_seed": fake.user_name(),
                "created_at": now,
            }
        )

        # Beta(5,5) centered at 0.5, rescaled into [0.35, 0.90] for spread
        # across accurate/inaccurate users.
        raw = rng.betavariate(5, 5)
        base_accuracy = 0.35 + raw * (0.90 - 0.35)

        # Speed profile: pick one of several archetypes so the cohort covers
        # fast/slow x accurate/erratic quadrants, not just accuracy-correlated speed.
        archetype = rng.choice(["fast_steady", "slow_steady", "fast_erratic", "slow_erratic", "average"])
        if archetype == "fast_steady":
            mean_ms, std_ms = rng.uniform(6000, 10000), rng.uniform(1000, 2000)
        elif archetype == "slow_steady":
            mean_ms, std_ms = rng.uniform(20000, 28000), rng.uniform(2000, 4000)
        elif archetype == "fast_erratic":
            mean_ms, std_ms = rng.uniform(7000, 12000), rng.uniform(6000, 10000)
        elif archetype == "slow_erratic":
            mean_ms, std_ms = rng.uniform(18000, 26000), rng.uniform(8000, 14000)
        else:
            mean_ms, std_ms = rng.uniform(12000, 18000), rng.uniform(3000, 6000)

        fatigue_tendency = rng.betavariate(2, 3)  # skewed toward lower fatigue, long tail
        improvement_trend = rng.uniform(-0.3, 0.5)  # slightly biased toward improving

        skill_profiles[str(user_id)] = {
            "base_accuracy": base_accuracy,
            "base_speed_mean_ms": mean_ms,
            "base_speed_std_ms": std_ms,
            "fatigue_tendency": fatigue_tendency,
            "improvement_trend": improvement_trend,
        }

    return users, skill_profiles
