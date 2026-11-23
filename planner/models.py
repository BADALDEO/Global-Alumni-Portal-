from django.conf import settings
from django.core.validators import FileExtensionValidator, MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class Resume(models.Model):
    """A saved resume version the student can attach to applications."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="resumes")
    title = models.CharField(max_length=120, help_text="e.g. Backend developer resume")
    version = models.CharField(max_length=30, blank=True, help_text="e.g. v2 or Jan 2026")
    target_role = models.CharField(max_length=120, blank=True, help_text="Role this version is written for")
    file = models.FileField(
        upload_to="resumes/library/",
        validators=[FileExtensionValidator(["pdf", "doc", "docx"])],
    )
    notes = models.TextField(blank=True, help_text="What changed in this version?")
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_default", "-created_at"]

    def __str__(self):
        return self.label

    @property
    def label(self):
        return f"{self.title} {self.version}".strip()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_default:
            Resume.objects.filter(user=self.user).exclude(pk=self.pk).update(is_default=False)


class SearchGoal(models.Model):
    """Daily targets that drive the job search plan."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="search_goal")
    daily_application_target = models.PositiveSmallIntegerField(
        default=5, validators=[MinValueValidator(1), MaxValueValidator(30)]
    )
    daily_networking_target = models.PositiveSmallIntegerField(
        default=3, validators=[MaxValueValidator(30)], help_text="Set 0 to switch the networking target off"
    )
    active_days_per_week = models.PositiveSmallIntegerField(
        default=6, validators=[MinValueValidator(1), MaxValueValidator(7)]
    )

    def __str__(self):
        return f"Goals of {self.user}"

    @classmethod
    def for_user(cls, user):
        goal, _ = cls.objects.get_or_create(user=user)
        return goal

    @property
    def weekly_application_target(self):
        return self.daily_application_target * self.active_days_per_week

    @property
    def weekly_networking_target(self):
        return self.daily_networking_target * self.active_days_per_week


class NetworkingActivity(models.Model):
    """One networking action: a connection request, message, meeting..."""

    class Platform(models.TextChoices):
        LINKEDIN = "linkedin", "LinkedIn"
        GITHUB = "github", "GitHub"
        LEETCODE = "leetcode", "LeetCode"
        COLLEGE = "college", "College Network"
        OTHER = "other", "Other"

    class Activity(models.TextChoices):
        CONNECT = "connect", "Sent connection request"
        CONNECTED = "connected", "Connection accepted"
        MESSAGE = "message", "Sent a message"
        REPLY = "reply", "Got a reply"
        MEETING = "meeting", "Call / meeting"
        EXPLORE = "explore", "Explored profile or projects"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="networking_activities"
    )
    platform = models.CharField(max_length=10, choices=Platform.choices, default=Platform.LINKEDIN)
    activity = models.CharField(max_length=10, choices=Activity.choices, default=Activity.CONNECT)
    contact_name = models.CharField(max_length=150)
    contact_role = models.CharField(max_length=150, blank=True, help_text="e.g. Senior Engineer at TCS")
    profile_url = models.URLField(blank=True)
    is_alumni = models.BooleanField(default=False, verbose_name="This person is an alumnus")
    alumni = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="networked_by", limit_choices_to={"role": "alumni"},
    )
    date = models.DateField(default=timezone.localdate)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-created_at"]

    def __str__(self):
        return f"{self.get_activity_display()}: {self.contact_name}"
