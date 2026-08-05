"""Generates structural content: exams, subjects, chapters, questions.

3 exams -> 10 subjects (distributed across exams) -> 30 chapters
(distributed across subjects) -> 500 questions (distributed across
chapters, 4 options each keyed A-D, one correct_option, a hidden
seed_difficulty in [0,1] drawn from a Beta distribution skewed toward
0.3-0.6 so most questions are "medium", with a long tail of easy/hard ones).
"""
import random
from datetime import datetime, timezone
from typing import Any, Dict, List

from bson import ObjectId
from faker import Faker

fake = Faker()

OPTION_KEYS = ["A", "B", "C", "D"]

EXAM_NAMES = ["JEE Main", "NEET", "UPSC CSE Prelims"]

SUBJECT_POOL = {
    "JEE Main": ["Physics", "Chemistry", "Mathematics"],
    "NEET": ["Biology", "Physics", "Chemistry"],
    "UPSC CSE Prelims": ["History", "Polity", "Geography", "Economics"],
}

CHAPTER_POOL = {
    "Physics": ["Kinematics", "Laws of Motion", "Thermodynamics", "Optics"],
    "Chemistry": ["Atomic Structure", "Chemical Bonding", "Organic Chemistry Basics"],
    "Mathematics": ["Algebra", "Calculus", "Trigonometry", "Probability"],
    "Biology": ["Cell Biology", "Genetics", "Human Physiology"],
    "History": ["Ancient India", "Modern India", "World History"],
    "Polity": ["Constitution Basics", "Union Government", "Judiciary"],
    "Geography": ["Physical Geography", "Indian Geography"],
    "Economics": ["Microeconomics Basics", "Indian Economy"],
}


def _make_options(correct_text: str, distractors: List[str]) -> (List[Dict[str, str]], str):
    texts = [correct_text] + distractors[:3]
    while len(texts) < 4:
        texts.append(fake.sentence(nb_words=4))
    random.shuffle(texts)
    correct_key = None
    options = []
    for key, text in zip(OPTION_KEYS, texts):
        options.append({"key": key, "text": text})
        if text == correct_text:
            correct_key = key
    return options, correct_key


def generate_exams_subjects_chapters_questions(rng: random.Random, now: datetime) -> Dict[str, List[Dict[str, Any]]]:
    """Returns dict with keys: exams, subjects, chapters, questions -- each a
    list of ready-to-insert Mongo documents (with pre-assigned _id ObjectIds
    so downstream generators, e.g. fake_events.py, can reference them before
    they're actually inserted).
    """
    exams: List[Dict[str, Any]] = []
    subjects: List[Dict[str, Any]] = []
    chapters: List[Dict[str, Any]] = []
    questions: List[Dict[str, Any]] = []

    for exam_name in EXAM_NAMES:
        exam_id = ObjectId()
        exams.append(
            {
                "_id": exam_id,
                "name": exam_name,
                "code": exam_name.replace(" ", "_").upper()[:12],
                "created_at": now,
            }
        )

        subject_names = SUBJECT_POOL[exam_name]
        for order, subject_name in enumerate(subject_names):
            subject_id = ObjectId()
            subjects.append(
                {
                    "_id": subject_id,
                    "exam_id": exam_id,
                    "name": subject_name,
                    "code": subject_name.replace(" ", "_").upper()[:12],
                    "order": order,
                }
            )

            # Exactly 3 chapters per subject -> 10 subjects * 3 = 30 chapters total.
            pool = CHAPTER_POOL.get(subject_name, [])
            chapter_names = pool[:3]
            while len(chapter_names) < 3:
                chapter_names.append(f"{subject_name} Topic {len(chapter_names) + 1}")

            for c_order, chapter_name in enumerate(chapter_names):
                chapter_id = ObjectId()
                chapters.append(
                    {
                        "_id": chapter_id,
                        "subject_id": subject_id,
                        "exam_id": exam_id,
                        "name": chapter_name,
                        "order": c_order,
                    }
                )

    # Now distribute exactly 500 questions across all chapters, roughly evenly.
    total_chapters = len(chapters)
    base_count = 500 // total_chapters
    remainder = 500 - base_count * total_chapters

    for i, chapter in enumerate(chapters):
        n_questions = base_count + (1 if i < remainder else 0)
        for _ in range(n_questions):
            correct_text = fake.sentence(nb_words=6)
            distractors = [fake.sentence(nb_words=6) for _ in range(3)]
            options, correct_key = _make_options(correct_text, distractors)
            # Beta(2,3) skews toward ~0.3-0.5 with some spread into [0,1].
            seed_difficulty = rng.betavariate(2, 3)
            questions.append(
                {
                    "_id": ObjectId(),
                    "chapter_id": chapter["_id"],
                    "subject_id": chapter["subject_id"],
                    "exam_id": chapter["exam_id"],
                    "text": f"({chapter['name']}) {fake.sentence(nb_words=10)}?",
                    "options": options,
                    "correct_option": correct_key,
                    "seed_difficulty": seed_difficulty,
                    "created_at": now,
                }
            )

    return {"exams": exams, "subjects": subjects, "chapters": chapters, "questions": questions}
