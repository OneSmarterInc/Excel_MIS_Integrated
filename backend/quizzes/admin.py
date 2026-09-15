from django.contrib import admin

from .models import Attempt, AttemptQuestion

admin.site.register([Attempt, AttemptQuestion])
