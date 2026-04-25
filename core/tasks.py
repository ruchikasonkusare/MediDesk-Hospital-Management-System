"""
MediDesk Celery Tasks
======================
Start worker:    celery -A medidesk worker --loglevel=info
Start scheduler: celery -A medidesk beat   --loglevel=info
"""
from celery import shared_task
from django.utils import timezone
from datetime import date, timedelta, datetime
import logging

logger = logging.getLogger(__name__)


# ── Appointment Reminder Email ────────────────────────────────────────────────

@shared_task(bind=True, max_retries=3)
def send_appointment_reminder_email(self, appointment_id):
    """Send email 24h before appointment."""
    try:
        from core.models import Appointment
        from django.core.mail import send_mail
        from django.conf import settings

        appt = Appointment.objects.select_related('patient', 'doctor').get(pk=appointment_id)
        if appt.status in ('cancelled', 'completed', 'no_show'):
            return f'Skipped — status: {appt.status}'

        email = appt.patient.email
        if not email:
            return 'No email on file'

        body = (
            f"Dear {appt.patient.name},\n\n"
            f"Reminder for your appointment:\n\n"
            f"  Doctor  : Dr. {appt.doctor.name} ({appt.doctor.get_specialization_display()})\n"
            f"  Date    : {appt.appointment_date.strftime('%A, %d %B %Y')}\n"
            f"  Time    : {appt.appointment_time.strftime('%I:%M %p')}\n"
            f"  Token   : #{appt.token_number}\n"
            f"  Type    : {appt.get_appointment_type_display()}\n\n"
            f"Please arrive 10 minutes early with any previous reports.\n"
            f"To reschedule, call us at least 2 hours before.\n\n"
            f"— MediDesk Team"
        )
        send_mail('Appointment Reminder – MediDesk', body,
                  settings.DEFAULT_FROM_EMAIL, [email], fail_silently=False)
        logger.info(f'Reminder email sent → appointment #{appointment_id}')
        return f'Email sent to {email}'
    except Exception as exc:
        logger.error(f'Email failed for appointment #{appointment_id}: {exc}')
        raise self.retry(exc=exc, countdown=300)


# ── Appointment Reminder SMS ──────────────────────────────────────────────────

@shared_task(bind=True, max_retries=3)
def send_appointment_reminder_sms(self, appointment_id):
    """Send SMS via Twilio. Requires TWILIO_* settings."""
    try:
        from core.models import Appointment
        from django.conf import settings

        appt = Appointment.objects.select_related('patient', 'doctor').get(pk=appointment_id)
        if appt.status in ('cancelled', 'completed'):
            return 'Skipped'

        if not getattr(settings, 'TWILIO_ACCOUNT_SID', ''):
            return 'Twilio not configured — set TWILIO_ACCOUNT_SID in settings.py'

        from twilio.rest import Client
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        msg = (
            f"MediDesk: Appointment with Dr. {appt.doctor.name} on "
            f"{appt.appointment_date.strftime('%d %b')} at "
            f"{appt.appointment_time.strftime('%I:%M %p')}. "
            f"Token #{appt.token_number}."
        )
        result = client.messages.create(
            body=msg, from_=settings.TWILIO_FROM,
            to=f'+91{appt.patient.phone}',
        )
        logger.info(f'SMS sent: {result.sid}')
        return f'SMS sent: {result.sid}'
    except Exception as exc:
        logger.error(f'SMS failed for appointment #{appointment_id}: {exc}')
        raise self.retry(exc=exc, countdown=600)


# ── Beat: Schedule Reminders ──────────────────────────────────────────────────

@shared_task
def schedule_appointment_reminders():
    """
    Runs every hour via Celery Beat.
    Queues email+SMS for appointments 23-25 hours from now.
    """
    from core.models import Appointment
    tomorrow = date.today() + timedelta(days=1)
    now = datetime.now()
    window_start = now + timedelta(hours=23)
    window_end   = now + timedelta(hours=25)

    appts = Appointment.objects.filter(
        appointment_date=tomorrow,
        status__in=['scheduled', 'confirmed'],
    )
    count = 0
    for appt in appts:
        appt_dt = datetime.combine(appt.appointment_date, appt.appointment_time)
        if window_start <= appt_dt <= window_end:
            send_appointment_reminder_email.delay(appt.id)
            send_appointment_reminder_sms.delay(appt.id)
            count += 1

    logger.info(f'Queued {count} appointment reminders')
    return f'Queued {count} reminders'


# ── Beat: Overdue Bill Alerts ─────────────────────────────────────────────────

@shared_task
def send_overdue_bill_alerts():
    """Runs daily. Alerts admin about bills unpaid for 7+ days."""
    from core.models import Bill, Notification
    from django.contrib.auth.models import User

    cutoff  = date.today() - timedelta(days=7)
    overdue = Bill.objects.filter(
        payment_status__in=['unpaid', 'partial'],
        bill_date__lte=cutoff,
    ).select_related('patient')

    if not overdue.exists():
        return 'No overdue bills'

    count     = overdue.count()
    total_due = sum(float(b.balance_due) for b in overdue)

    for admin in User.objects.filter(is_superuser=True):
        Notification.objects.create(
            user=admin,
            title=f'{count} Overdue Bill(s)',
            message=(
                f'{count} bill(s) overdue by 7+ days. '
                f'Total outstanding: ₹{total_due:,.2f}.'
            ),
            notif_type='billing',
            link='/billing/?status=unpaid',
        )
    return f'{count} overdue bills, ₹{total_due:.2f}'


# ── Beat: Nightly Risk Scores ─────────────────────────────────────────────────

@shared_task
def compute_risk_scores_batch():
    """Runs nightly. Pre-computes risk scores for all patients."""
    from core.models import Patient
    from core.ml.risk_model import predict_risk
    from django.core.cache import cache

    patients  = Patient.objects.all()
    high_risk = []
    for p in patients:
        try:
            score, factors = predict_risk(p)
            if score is not None:
                cache.set(f'risk_{p.id}', {'score': score, 'factors': factors}, 86400)
                if score >= 0.7:
                    high_risk.append(p.name)
        except Exception as e:
            logger.error(f'Risk score failed for {p}: {e}')

    logger.info(f'Risk scores done. High risk: {len(high_risk)}')
    return f'Computed {patients.count()} scores. High risk: {len(high_risk)}'


# ── Beat: Daily Digest ────────────────────────────────────────────────────────

@shared_task
def send_daily_digest():
    """Runs every morning. Emails summary to superusers."""
    from core.models import Appointment, Bill, Patient
    from django.core.mail import send_mail
    from django.conf import settings
    from django.contrib.auth.models import User
    from django.db.models import Sum

    today     = date.today()
    yesterday = today - timedelta(days=1)

    appts_today = Appointment.objects.filter(appointment_date=today).count()
    rev_today   = Bill.objects.filter(bill_date=today).aggregate(
        s=Sum('amount_paid'))['s'] or 0
    new_pts     = Patient.objects.filter(registered_at__date=today).count()

    body = (
        f"MediDesk Daily Digest — {today.strftime('%d %B %Y')}\n\n"
        f"  Appointments today : {appts_today}\n"
        f"  New patients today : {new_pts}\n"
        f"  Revenue today      : ₹{float(rev_today):,.2f}\n\n"
        f"— MediDesk Automated Digest"
    )
    emails = [u.email for u in User.objects.filter(is_superuser=True) if u.email]
    if emails and getattr(settings, 'DEFAULT_FROM_EMAIL', ''):
        send_mail('MediDesk Daily Digest', body,
                  settings.DEFAULT_FROM_EMAIL, emails)
    return f'Digest sent to {len(emails)} admin(s)'
