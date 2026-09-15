"""The five question sets that sit behind every chapter and module.

A set is built once and then belongs to the instructor: they can rewrite any question in
it, and whatever they leave there is what students sit. All five sets are built from the
same list of skills in the same order, so set three asks about the same things as set one
and only the company names, figures and scenarios differ. That keeps them level, which is
the point of handing them out in turn.
"""
from __future__ import annotations

import random

from django.utils import timezone

from .ai_questions import questions_from_text
from .business import BUSINESS_PER_QUIZ, BUSINESS_TEMPLATES, generate_business_questions
from .generator import (
    QUESTIONS_PER_QUIZ,
    TEMPLATES,
    choose_templates,
    generate_questions,
)
from .models import QuestionSet, SetAssignment, SetQuestion

SETS_PER_SECTION = QuestionSet.SETS_PER_SECTION


def _target_filter(chapter=None, module=None) -> dict:
    """Sets hang off a module when there is one, otherwise off the chapter."""
    return {"module": module, "chapter": None} if module else {"chapter": chapter, "module": None}


def build_paper_from(templates, business_templates, seed: int, context: str,
                     written: list[dict] | None = None) -> list[dict]:
    """One paper: the model's questions about this section first, then the template bank.

    Whatever the model wrote from the section's own text leads the paper, because those are
    the questions about what the student just read. The template bank fills the rest, so a
    paper is always the same length whether or not a model was running.
    """
    rng = random.Random(seed)
    questions = []
    written = list(written or [])
    for position in range(1, len(templates) + 1):
        if written:
            question = dict(written.pop(0))
        else:
            question = templates[position - 1](rng)
            question["kind"] = "MCQ"
        question["order"] = position
        question["context"] = context
        questions.append(question)
    for offset, template in enumerate(business_templates):
        from .business import add_answer_cell

        question = add_answer_cell(template(rng))
        question["order"] = QUESTIONS_PER_QUIZ + 1 + offset
        question["kind"] = "BUSINESS"
        question["context"] = context
        questions.append(question)
    return questions


def build_sets(chapter=None, module=None, context: str = "", source_text: str = "",
               replace: bool = False) -> list[QuestionSet]:
    """Return the five sets for this section, building only what is missing.

    There are five and only five per section, for the life of the section. Once they exist
    this returns them untouched, so an instructor's rewording survives every later visit;
    the only thing that discards it is the deliberate rebuild.
    """
    where = _target_filter(chapter, module)
    existing = list(QuestionSet.objects.filter(**where).order_by("number", "id"))

    if replace:
        QuestionSet.objects.filter(**where).delete()
        existing = []
    else:
        # SQLite treats two NULLs as different, so the unique constraint cannot stop a
        # duplicate on a section that has no module. Keep the oldest of each number.
        seen, extra = set(), []
        for item in existing:
            if item.number in seen:
                extra.append(item.id)
            else:
                seen.add(item.number)
        if extra:
            QuestionSet.objects.filter(id__in=extra).delete()
            existing = [item for item in existing if item.id not in extra]
        if len(existing) == SETS_PER_SECTION:
            return existing

    # The skills are chosen once, against the text of this section, and every set uses
    # them in the same order.
    picker = random.Random()
    skills = choose_templates(TEMPLATES, QUESTIONS_PER_QUIZ, picker, f"{context} {source_text}")
    business_skills = choose_templates(
        BUSINESS_TEMPLATES, BUSINESS_PER_QUIZ, picker, f"{context} {source_text}"
    )

    have = {item.number: item for item in existing}
    made = []
    for number in range(1, SETS_PER_SECTION + 1):
        if number in have:
            made.append(have[number])
            continue
        # Each set gets its own questions from the model, written from the same passage, so
        # the five stay about the section and still differ from one another.
        written = questions_from_text(
            context or "this section", source_text, QUESTIONS_PER_QUIZ,
            seed_hint=f"this is set {number} of {SETS_PER_SECTION}",
        )
        question_set = QuestionSet.objects.create(number=number, **where)
        for question in build_paper_from(skills, business_skills,
                                         seed=picker.randrange(1, 10_000_000), context=context,
                                         written=written):
            business = question["kind"] == "BUSINESS"
            SetQuestion.objects.create(
                question_set=question_set,
                order=question["order"],
                kind="BUSINESS" if business else "MCQ",
                prompt=question["prompt"],
                options=[] if business else question["options"],
                correct_index=-1 if business else question["correct_index"],
                expected_answer=str(question["expected"]) if business else "",
                answer_format=question.get("format", "") if business else "",
                tolerance=question.get("tolerance", 0) if business else 0,
                steps=question.get("steps", "") if business else "",
                explanation=question["explanation"],
                skill=question["skill"],
                workbook=question["workbook"],
            )
        made.append(question_set)
    return made


def set_for_student(student, chapter=None, module=None, context: str = "",
                    source_text: str = "", taken_before: int = 0) -> QuestionSet:
    """Which of the five sets this student sits now.

    The first student on a section gets set one, the second gets set two, and the sixth
    comes back round to set one. That starting point is remembered, so it does not shuffle
    between visits. A retake moves the same student on to the next set, so a second attempt
    is a different paper of the same difficulty and a sixth attempt returns to their first.
    """
    sets = build_sets(chapter, module, context, source_text)
    where = _target_filter(chapter, module)

    assignment = SetAssignment.objects.filter(student=student, **where).first()
    if assignment is None:
        taken = SetAssignment.objects.filter(**where).count()
        number = (taken % SETS_PER_SECTION) + 1
        assignment = SetAssignment.objects.create(student=student, number=number, **where)

    wanted = ((assignment.number - 1 + taken_before) % SETS_PER_SECTION) + 1
    return next((item for item in sets if item.number == wanted), sets[0])


def touch(question_set: QuestionSet) -> None:
    question_set.edited_at = timezone.now()
    question_set.save(update_fields=["edited_at"])
