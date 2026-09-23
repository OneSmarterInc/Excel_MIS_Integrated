"""The rubric an instructor marks with, and what it means for tracking progress.

Instructors do not start from a blank page. There is a standard list of terms here, each
with a plain description and a default importance, and the instructor's job is to say how
much each one counts on their course. They can add terms of their own and edit or drop any
of them.

Terms come in two kinds. A measured term is worked out from what the student has actually
done in the platform, so progress tracking is scored against the instructor's own rubric
rather than against a fixed idea of what matters. A judged term is one only a person can
mark, and it waits for the instructor to enter a score.
"""
from __future__ import annotations

CATALOGUE = [
    {
        "key": "quiz_accuracy",
        "name": "Quiz accuracy",
        "descriptor": "Marks earned across every quiz taken on this course.",
        "points": 10,
        "source": "measured",
    },
    {
        "key": "formula_accuracy",
        "name": "Formula accuracy",
        "descriptor": "Multiple choice answers about formulas, references and functions.",
        "points": 8,
        "source": "measured",
    },
    {
        "key": "applied_analysis",
        "name": "Applied analysis",
        "descriptor": "The long business questions, where the answer is worked out in the sheet.",
        "points": 8,
        "source": "measured",
    },
    {
        "key": "coverage",
        "name": "Course coverage",
        "descriptor": "How much of the material the student has actually worked through.",
        "points": 6,
        "source": "measured",
    },
    {
        "key": "persistence",
        "name": "Persistence",
        "descriptor": "Coming back to a section after a weak attempt and improving on it.",
        "points": 4,
        "source": "measured",
    },
    {
        "key": "formatting",
        "name": "Worksheet presentation",
        "descriptor": "Formats that match the meaning of the data, and a readable layout.",
        "points": 6,
        "source": "judged",
    },
    {
        "key": "recommendation",
        "name": "Management recommendation",
        "descriptor": "One sentence naming an action, the evidence for it, and what would change it.",
        "points": 6,
        "source": "judged",
    },
    {
        "key": "participation",
        "name": "Participation",
        "descriptor": "Contribution in class and to the group work.",
        "points": 4,
        "source": "judged",
    },
]

CATALOGUE_BY_KEY = {item["key"]: item for item in CATALOGUE}

FORMULA_SKILLS = (
    "sum", "average", "count", "min", "max", "if", "sumif", "countif", "vlookup", "lookup",
    "reference", "round", "order of operations", "percentage", "autofill", "formula",
)


def normalise(criteria: list) -> list:
    """Fill in the parts of a criterion the instructor did not have to type.

    An instructor picking a standard term only chooses its importance, so the name, the
    description and whether it is measured or judged come from the catalogue. A term of
    their own is judged unless they say otherwise, because the platform has no way to
    measure something it has never heard of.
    """
    cleaned = []
    for item in criteria or []:
        if isinstance(item, str):
            item = {"name": item}
        key = str(item.get("key", "")).strip()
        standard = CATALOGUE_BY_KEY.get(key, {})
        name = str(item.get("name") or standard.get("name") or "").strip()
        if not name:
            continue
        try:
            points = int(item.get("points", standard.get("points", 5)) or 0)
        except (TypeError, ValueError):
            points = standard.get("points", 5)
        source = item.get("source") or standard.get("source") or "judged"
        cleaned.append({
            "key": key or "",
            "name": name[:120],
            "descriptor": str(item.get("descriptor") or standard.get("descriptor") or "")[:400],
            "points": max(0, points),
            "source": "measured" if source == "measured" and key in CATALOGUE_BY_KEY else "judged",
        })
    return cleaned


def _fraction(correct: int, asked: int) -> float | None:
    return (correct / asked) if asked else None


def measure(key: str, facts: dict) -> float | None:
    """Return how far along a student is on one measured term, from 0 to 1, or None.

    None means there is nothing to go on yet, which is different from doing badly and is
    reported that way rather than as a zero.
    """
    if key == "quiz_accuracy":
        return _fraction(facts["score"], facts["total"])
    if key == "formula_accuracy":
        return _fraction(facts["formula_correct"], facts["formula_asked"])
    if key == "applied_analysis":
        return _fraction(facts["business_correct"], facts["business_asked"])
    if key == "coverage":
        # A student who has not started has nothing to measure. Reporting zero coverage
        # would read as a mark against them rather than as an empty page.
        if not facts["attempts"]:
            return None
        return _fraction(facts["sections_touched"], facts["sections_available"])
    if key == "persistence":
        if facts["attempts"] < 2:
            return None
        # Improving on your own earlier attempt is what this term is about, so a student
        # who started strong and stayed there is not penalised for having little to gain.
        gain = facts["best_percentage"] - facts["first_percentage"]
        headroom = max(100 - facts["first_percentage"], 1)
        return max(0.0, min(1.0, gain / headroom)) if headroom > 5 else 1.0
    return None


def gather_facts(attempts, questions, sections_available: int) -> dict:
    """Everything the measured terms need, taken from the student's own attempts."""
    submitted = [attempt for attempt in attempts if attempt.submitted_at]
    score = sum(attempt.score for attempt in submitted)
    total = sum(attempt.total for attempt in submitted)
    formula_asked = formula_correct = business_asked = business_correct = 0
    for question in questions:
        skill = (question.skill or "").lower()
        if question.kind == "BUSINESS":
            business_asked += 1
            business_correct += 1 if question.is_correct else 0
        elif any(word in skill for word in FORMULA_SKILLS):
            formula_asked += 1
            formula_correct += 1 if question.is_correct else 0
    ordered = sorted(submitted, key=lambda attempt: attempt.submitted_at)
    sections = {
        (attempt.module_id or f"c{attempt.chapter_id}") for attempt in submitted
    }
    return {
        "attempts": len(submitted),
        "score": score,
        "total": total,
        "formula_asked": formula_asked,
        "formula_correct": formula_correct,
        "business_asked": business_asked,
        "business_correct": business_correct,
        "sections_touched": len(sections),
        "sections_available": max(sections_available, 1),
        "first_percentage": ordered[0].percentage if ordered else 0,
        "best_percentage": max((a.percentage for a in submitted), default=0),
    }


def score_against(rubric_criteria: list, facts: dict, judged_scores: dict | None = None) -> dict:
    """Mark one student against one rubric.

    Measured terms are worked out from the facts. Judged terms use whatever the instructor
    has entered for that student, and are left out of the running total until they do, so
    an unmarked term does not read as a zero.
    """
    judged_scores = judged_scores or {}
    rows, awarded, possible, waiting = [], 0.0, 0.0, []

    for item in normalise(rubric_criteria):
        points = item["points"]
        if item["source"] == "measured":
            fraction = measure(item["key"], facts)
            if fraction is None:
                rows.append({**item, "awarded": None, "fraction": None,
                             "note": "Nothing to measure yet."})
                waiting.append(item["name"])
                continue
            earned = round(points * fraction, 1)
        else:
            given = judged_scores.get(item["name"].lower())
            if given is None:
                rows.append({**item, "awarded": None, "fraction": None,
                             "note": "Waiting for you to mark it."})
                waiting.append(item["name"])
                continue
            earned = round(min(float(given), points), 1)
            fraction = earned / points if points else 0
        awarded += earned
        possible += points
        rows.append({**item, "awarded": earned, "fraction": round(fraction, 3), "note": ""})

    return {
        "criteria": rows,
        "awarded": round(awarded, 1),
        "possible": round(possible, 1),
        "percentage": round(awarded / possible * 100, 1) if possible else None,
        "waiting_on": waiting,
    }
