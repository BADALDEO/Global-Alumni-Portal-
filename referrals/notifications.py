from django.conf import settings
from django.core.mail import send_mail


def _send(to_user, subject, body):
    if not to_user.email:
        return
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [to_user.email], fail_silently=True)


def notify_new_request(referral):
    _send(
        referral.alumni,
        f"New referral request from {referral.student.display_name}",
        f"Hi {referral.alumni.display_name},\n\n"
        f"{referral.student.display_name} asked you for a referral for "
        f"{referral.job_title} at {referral.company_name}.\n\n"
        f"Message:\n{referral.message}\n\n"
        "Log in to Global Alumni Portal to accept or decline.",
    )


def notify_response(referral):
    outcome = "accepted" if referral.status == "accepted" else "declined"
    reply = f"\n\nTheir reply:\n{referral.alumni_reply}" if referral.alumni_reply else ""
    _send(
        referral.student,
        f"Your referral request was {outcome}",
        f"Hi {referral.student.display_name},\n\n"
        f"{referral.alumni.display_name} has {outcome} your referral request for "
        f"{referral.job_title} at {referral.company_name}.{reply}",
    )
