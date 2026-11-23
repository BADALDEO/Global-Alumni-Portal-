from django.contrib import admin

from .models import Application, Job


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ("title", "company_name", "job_type", "location", "posted_by", "is_active", "created_at")
    list_filter = ("job_type", "is_active")
    search_fields = ("title", "company_name", "skills_required")


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ("student", "job", "status", "applied_at")
    list_filter = ("status",)
