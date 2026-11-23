from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = "student", "Student"
        ALUMNI = "alumni", "Alumni"
        COMPANY = "company", "Company"

    role = models.CharField(max_length=10, choices=Role.choices, default=Role.STUDENT)
    company_name = models.CharField(max_length=150, blank=True)
    designation = models.CharField(max_length=120, blank=True, help_text="Your current job title")
    graduation_year = models.PositiveIntegerField(null=True, blank=True)
    linkedin_url = models.URLField(blank=True, verbose_name="LinkedIn URL")
    github_url = models.URLField(blank=True, verbose_name="GitHub URL")
    leetcode_url = models.URLField(blank=True, verbose_name="LeetCode URL")
    open_to_mentorship = models.BooleanField(default=False, verbose_name="Open to mentoring students")
    bio = models.TextField(blank=True, max_length=600, help_text="A short intro about you")
    # False for people who joined with Google until they pick a role
    profile_completed = models.BooleanField(default=True)

    @property
    def display_name(self):
        return self.get_full_name() or self.username

    @property
    def is_student(self):
        return self.role == self.Role.STUDENT

    @property
    def is_alumni(self):
        return self.role == self.Role.ALUMNI

    @property
    def is_company(self):
        return self.role == self.Role.COMPANY

    @property
    def can_post_jobs(self):
        return self.role in (self.Role.ALUMNI, self.Role.COMPANY)
