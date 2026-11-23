from django.contrib import admin

from .models import ExternalApplication


@admin.register(ExternalApplication)
class ExternalApplicationAdmin(admin.ModelAdmin):
    list_display = ("job_title", "company_name", "platform", "status", "applied_date", "user")
    list_filter = ("platform", "status")
    search_fields = ("job_title", "company_name", "user__username")
