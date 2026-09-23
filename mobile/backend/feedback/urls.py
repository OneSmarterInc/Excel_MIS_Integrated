from django.urls import path

from . import views

urlpatterns = [
    path("feedback/", views.feedback_list),
    path("feedback/<int:pk>/reply/", views.faculty_reply),
    path("feedback/course/<int:pk>/", views.course_feedback),
]
