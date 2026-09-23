from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import IsFaculty
from courses.models import Course
from courses.views import can_read_course
from quizzes.models import Attempt, AttemptQuestion

from .models import Feedback


class FeedbackSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.name", read_only=True)
    course_code = serializers.CharField(source="course.code", read_only=True)

    class Meta:
        model = Feedback
        fields = ["id", "course", "course_code", "student_name", "rating", "comment",
                  "faculty_reply", "created_at"]
        read_only_fields = ["id", "created_at", "faculty_reply"]


@api_view(["GET", "POST"])
def feedback_list(request):
    if request.method == "POST":
        serializer = FeedbackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        course = serializer.validated_data["course"]
        if not can_read_course(request.user, course):
            return Response({"detail": "Join the course before leaving feedback."}, status=403)
        feedback = serializer.save(student=request.user)
        return Response(FeedbackSerializer(feedback).data, status=201)

    queryset = Feedback.objects.select_related("course", "student")
    if request.user.is_faculty:
        queryset = queryset.filter(course__faculty=request.user)
    else:
        queryset = queryset.filter(student=request.user)
    course_id = request.query_params.get("course_id")
    if course_id:
        queryset = queryset.filter(course_id=course_id)
    return Response(FeedbackSerializer(queryset, many=True).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsFaculty])
def faculty_reply(request, pk):
    try:
        feedback = Feedback.objects.get(pk=pk, course__faculty=request.user)
    except Feedback.DoesNotExist:
        return Response({"detail": "Feedback not found."}, status=404)
    feedback.faculty_reply = request.data.get("faculty_reply", "")
    feedback.save(update_fields=["faculty_reply"])
    return Response(FeedbackSerializer(feedback).data)


@api_view(["GET"])
def course_feedback(request, pk):
    """Course wise feedback: what the quizzes say about this student, section by section."""
    try:
        course = Course.objects.get(pk=pk)
    except Course.DoesNotExist:
        return Response({"detail": "Course not found."}, status=404)
    if not can_read_course(request.user, course):
        return Response({"detail": "You do not have access to this course."}, status=403)

    attempts = Attempt.objects.filter(
        course=course, student=request.user, submitted_at__isnull=False
    ).select_related("chapter", "module")

    sections = []
    for attempt in attempts:
        sections.append({
            "attempt_id": attempt.id,
            "label": attempt.label,
            "score": attempt.score,
            "total": attempt.total,
            "percentage": attempt.percentage,
            "taken_at": attempt.submitted_at,
        })

    skill_rows: dict = {}
    for question in AttemptQuestion.objects.filter(attempt__in=attempts):
        row = skill_rows.setdefault(question.skill or "General", {"skill": question.skill,
                                                                  "asked": 0, "correct": 0})
        row["asked"] += 1
        row["correct"] += 1 if question.is_correct else 0
    skills = []
    for row in skill_rows.values():
        row["accuracy"] = round(row["correct"] / max(row["asked"], 1) * 100, 1)
        skills.append(row)
    skills.sort(key=lambda r: r["accuracy"])

    total_score = sum(s["score"] for s in sections)
    total_marks = sum(s["total"] for s in sections)
    overall = round(total_score / max(total_marks, 1) * 100, 1)

    if not sections:
        message = ("No quiz has been submitted for this course yet. Open a chapter, read the "
                   "easy explanation, then take the quiz to see feedback here.")
    elif overall >= 85:
        message = (f"You are averaging {overall} percent across {len(sections)} "
                   f"{'quiz' if len(sections) == 1 else 'quizzes'}. "
                   "Keep going into the later chapters, the formulas get longer but the habit "
                   "of reading the worksheet first is the same.")
    elif overall >= 60:
        message = (f"You are averaging {overall} percent across {len(sections)} "
                   f"{'quiz' if len(sections) == 1 else 'quizzes'}. "
                   f"The weakest area is {skills[0]['skill'] if skills else 'not yet clear'}, "
                   "so rebuild that worksheet by hand before your next attempt.")
    else:
        message = (f"You are averaging {overall} percent across {len(sections)} "
                   f"{'quiz' if len(sections) == 1 else 'quizzes'}. "
                   "Slow down and work through the easy explanations again, one module at a "
                   "time, then retake each quiz for a fresh set of questions.")

    return Response({
        "course": {"id": course.id, "code": course.code, "name": course.name},
        "overall_percentage": overall,
        "marks": f"{total_score} / {total_marks}",
        "message": message,
        "sections": sections,
        "skills": skills,
        "comments": FeedbackSerializer(
            Feedback.objects.filter(course=course, student=request.user), many=True
        ).data,
    })
