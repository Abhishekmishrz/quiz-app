"""Seed script entrypoint: `python -m scripts.seed`.

Connects via pymongo (sync -- this is a one-off batch job, not a server
process) using the MONGO_URI/DB_NAME env vars, wipes existing collections
in the target DB, then generates structural content, users (with hidden
skill profiles), and historical events, in that order. Prints progress
counts throughout.
"""
import os
import random
import sys
from datetime import datetime, timezone

from pymongo import MongoClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.generators.fake_content import generate_exams_subjects_chapters_questions
from scripts.generators.fake_events import generate_events
from scripts.generators.fake_users import generate_users

SEED = 42


def main() -> None:
    mongo_uri = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
    db_name = os.environ.get("DB_NAME", "quiz_app")

    print(f"Connecting to {mongo_uri} / db={db_name} ...")
    client = MongoClient(mongo_uri)
    db = client[db_name]

    print("Wiping existing collections ...")
    for coll_name in ["users", "exams", "subjects", "chapters", "questions", "quiz_attempts", "question_events"]:
        db[coll_name].delete_many({})

    rng = random.Random(SEED)
    now = datetime.now(timezone.utc)

    print("Generating structural content (exams/subjects/chapters/questions) ...")
    content = generate_exams_subjects_chapters_questions(rng, now)
    exams, subjects, chapters, questions = (
        content["exams"],
        content["subjects"],
        content["chapters"],
        content["questions"],
    )
    db.exams.insert_many(exams)
    db.subjects.insert_many(subjects)
    db.chapters.insert_many(chapters)
    db.questions.insert_many(questions)
    print(f"  exams={len(exams)} subjects={len(subjects)} chapters={len(chapters)} questions={len(questions)}")

    print("Generating users + hidden skill profiles ...")
    users, skill_profiles = generate_users(rng, now, count=50)
    db.users.insert_many(users)
    print(f"  users={len(users)}")

    print("Generating historical quiz_attempts + question_events (this may take a moment) ...")
    quiz_attempts, question_events = generate_events(rng, now, users, skill_profiles, chapters, questions)

    # Bulk insert in chunks to keep individual insert_many payloads reasonable.
    CHUNK = 5000
    db.quiz_attempts.insert_many(quiz_attempts)
    for i in range(0, len(question_events), CHUNK):
        db.question_events.insert_many(question_events[i : i + CHUNK])
    print(f"  quiz_attempts={len(quiz_attempts)} question_events={len(question_events)}")

    print("Creating indexes ...")
    db.subjects.create_index("exam_id")
    db.chapters.create_index("subject_id")
    db.questions.create_index("chapter_id")
    db.quiz_attempts.create_index([("user_id", 1), ("status", 1)])
    db.quiz_attempts.create_index([("user_id", 1), ("started_at", -1)])
    db.question_events.create_index([("quiz_attempt_id", 1), ("question_id", 1)], unique=True)
    db.question_events.create_index([("quiz_attempt_id", 1), ("question_index", 1)])
    db.question_events.create_index([("user_id", 1), ("submitted_at", -1)])
    db.question_events.create_index("question_id")
    db.question_events.create_index("chapter_id")
    db.question_events.create_index([("exam_id", 1), ("subject_id", 1), ("chapter_id", 1)])
    db.question_events.create_index([("user_id", 1), ("chapter_id", 1)])
    db.users.create_index("email", unique=True)

    print("Seed complete.")
    client.close()


if __name__ == "__main__":
    main()
