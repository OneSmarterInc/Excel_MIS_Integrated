from django.urls import path

from . import admin_views, teaching_views, views

urlpatterns = [
    # Editing and reshaping what was extracted
    path("chapters/<int:pk>/edit/", teaching_views.edit_chapter),
    path("chapters/<int:pk>/split/", teaching_views.split_chapter),
    path("chapters/<int:pk>/submit/", teaching_views.submit_chapter),
    path("chapters/<int:pk>/publish/", teaching_views.publish_chapter),
    path("chapters/<int:pk>/download/", teaching_views.download_chapter),
    path("chapters/merge/", teaching_views.merge_chapters),
    path("modules/<int:pk>/edit/", teaching_views.edit_module),
    path("modules/<int:pk>/download/", teaching_views.download_module),
    path("books/<int:pk>/reorder/", teaching_views.reorder_chapters),
    path("books/<int:pk>/download/", teaching_views.download_book),

    # Material an instructor hangs off a chapter or module
    path("resources/", teaching_views.resources),
    path("resources/<int:pk>/", teaching_views.delete_resource),
    path("demonstrations/", teaching_views.demonstrations),
    path("demonstrations/<int:pk>/", teaching_views.edit_demonstration),

    # Marking and watching progress
    path("rubrics/catalogue/", teaching_views.rubric_catalogue),
    path("rubrics/", teaching_views.rubrics),
    path("rubrics/<int:pk>/", teaching_views.edit_rubric),
    path("evaluations/", teaching_views.evaluations),
    path("courses/<int:pk>/progress/", teaching_views.course_progress),
    path("courses/<int:pk>/progress/<int:student_id>/", teaching_views.student_progress),

    # Admin
    path("admin/dashboard/", admin_views.dashboard),
    path("admin/users/", admin_views.users),
    path("admin/users/<int:pk>/", admin_views.user_detail),
    path("admin/courses/", admin_views.courses),
    path("admin/courses/<int:pk>/", admin_views.course_detail),
    path("admin/books/", admin_views.books),
    path("admin/books/<int:pk>/", admin_views.book_tree),
    path("admin/review/", admin_views.review_queue),
    path("admin/review/<int:pk>/", admin_views.review_chapter),
    path("admin/analytics/", admin_views.analytics),

    path("courses/", views.CourseListView.as_view()),
    path("courses/<int:pk>/", views.CourseDetailView.as_view()),
    path("courses/<int:pk>/books/", views.BookUploadView.as_view()),
    path("courses/<int:pk>/generate-book/", views.BookGenerateView.as_view()),
    path("courses/<int:pk>/invitations/", views.course_invitations),
    path("invitations/<int:pk>/", views.delete_invitation),
    path("invitations/<int:pk>/respond/", views.respond_to_invitation),
    path("my-invitations/", views.my_invitations),
    path("courses/<int:pk>/students/", views.course_students),
    path("books/<int:pk>/", views.delete_book),
    path("chapters/<int:pk>/", views.ChapterView.as_view()),
    path("modules/<int:pk>/", views.ModuleView.as_view()),
    path("ai-status/", views.ai_status),
    path("course-codes/", views.course_codes),
    path("join-course/", views.join_course),
    path("faculty/dashboard/", views.faculty_dashboard),
    path("student/dashboard/", views.student_dashboard),
]
