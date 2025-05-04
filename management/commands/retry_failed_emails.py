from django.core.management.base import BaseCommand
from django.utils import timezone
from accounts.models import FailedEmail
from core.utils import send_html_email

class Command(BaseCommand):
    help = 'Retry sending failed emails'

    def handle(self, *args, **options):
        threshold_time = timezone.now() - timezone.timedelta(hours=1)

        for failed_email in FailedEmail.objects.filter(
            last_attempt__lt=threshold_time,
            attempts__lt=3,
        ):
            try:
                send_html_email(
                    subject=failed_email.subject,
                    recipient_list=failed_email.recipient_list,
                    template=failed_email.template_name,
                    context=failed_email.context
                )
                failed_email.delete()
                self.stdout.write(self.style.SUCCESS(f'Successfully resent email to {failed_email.recipient_list}'))
            except Exception as e:
                failed_email.attempt_count += 1
                failed_email.error_message = str(e)
                failed_email.save()
                self.stderr.write(self.style.ERROR(f'Failed to resend email to {failed_email.recipient_list}: {e}'))