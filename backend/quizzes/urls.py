from django.urls import path

from . import views

urlpatterns = [
    path("quizzes/start/", views.start_quiz),
    path("quizzes/preview/", views.preview_quiz),
    path("quizzes/attempts/", views.attempt_list),
    path("quizzes/sets/", views.question_sets),
    path("quizzes/sets/questions/<int:pk>/", views.edit_set_question),
    path("quizzes/<int:pk>/", views.attempt_detail),
    path("quizzes/<int:pk>/submit/", views.submit_quiz),
    path("quizzes/<int:pk>/check/", views.check_answer),
    path("courses/<int:pk>/performance/", views.course_performance),
]
