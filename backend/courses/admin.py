from django.contrib import admin

from .models import Book, Chapter, Course, Enrollment, Module

admin.site.register([Course, Enrollment, Book, Chapter, Module])
