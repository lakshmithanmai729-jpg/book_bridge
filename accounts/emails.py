"""Email helpers: address verification and transactional notifications."""
import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, send_mail
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.template.loader import render_to_string
from django.urls import reverse

logger = logging.getLogger(__name__)

SALT = 'bookbridge.email-verify'
MAX_AGE = 60 * 60 * 24 * 3          # verification links live for 3 days

# Backends that accept a message and throw it away. On a free host the default
# is the console backend, so "check your inbox" would be a lie — the signup,
# login and password-reset screens use this to say so up front.
NO_DELIVERY_BACKENDS = ('console', 'dummy', 'locmem', 'filebased')


def email_delivery_configured():
    """True when this deployment can actually deliver mail to a member."""
    backend = getattr(settings, 'EMAIL_BACKEND', '') or ''
    return not any(marker in backend.lower() for marker in NO_DELIVERY_BACKENDS)


def make_verification_token(user):
    return TimestampSigner(salt=SALT).sign(str(user.pk))


def read_verification_token(token):
    """Return the user id inside ``token`` or ``None`` when invalid/expired."""
    try:
        return int(TimestampSigner(salt=SALT).unsign(token, max_age=MAX_AGE))
    except (BadSignature, SignatureExpired, ValueError):
        return None


def verification_url(user, request=None):
    path = reverse('accounts:verify_email', args=[make_verification_token(user)])
    if request is not None:
        return request.build_absolute_uri(path)
    return f'{settings.SITE_URL.rstrip("/")}{path}' if getattr(settings, 'SITE_URL', '') else path


def send_verification_email(user, request=None):
    """Send the "confirm your email" message. Returns True when it was sent."""
    profile = getattr(user, 'profile', None)
    if not user.email:
        return False

    url = verification_url(user, request)
    context = {
        'user': user,
        'url': url,
        'name': (profile.name if profile and profile.name else user.username),
        'expires_days': MAX_AGE // 86400,
    }

    subject = 'Confirm your BookBridge email address'
    text_body = render_to_string('emails/verify_email.txt', context)
    html_body = render_to_string('emails/verify_email.html', context)

    try:
        message = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
        )
        message.attach_alternative(html_body, 'text/html')
        message.send(fail_silently=False)
        return True
    except Exception:
        logger.exception('Could not send verification email to %s', user.email)
        return False


def notify_new_message(recipient, sender, book, text):
    """Tell a user by email that they received a new in-app chat message."""
    if not recipient.email or not getattr(recipient, 'profile', None):
        return False
    if getattr(settings, 'DISABLE_CHAT_EMAILS', False):
        return False

    profile = recipient.profile
    if not profile.email_verified:
        return False

    url = f'{getattr(settings, "SITE_URL", "").rstrip("/")}'
    try:
        from django.urls import reverse as _reverse
        url = f'{url}{_reverse("accounts:chat_detail", args=[sender.pk])}'
    except Exception:
        pass

    subject = f'New message from {sender.username} on BookBridge'
    body = (
        f'Hi {profile.name or recipient.username},\n\n'
        f'{sender.username} sent you a message'
        + (f' about "{book.title}"' if book else '')
        + f':\n\n"{text[:400]}"\n\n'
        f'Reply on BookBridge: {url}\n\n'
        'Your phone number was not shared.'
    )
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [recipient.email], fail_silently=True)
        return True
    except Exception:
        logger.exception('Could not send chat notification to %s', recipient.email)
        return False


def mark_verified(user):
    profile = getattr(user, 'profile', None)
    if profile is None:
        from .models import UserProfile
        profile, _ = UserProfile.objects.get_or_create(user=user)
    profile.email_verified = True
    profile.save(update_fields=['email_verified'])
    return profile
