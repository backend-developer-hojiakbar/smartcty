from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.conf import settings

User = get_user_model()

class Command(BaseCommand):
    help = 'Creates a superuser and superadmin if they don\'t exist'

    def handle(self, *args, **options):
        # Create superuser (Django admin)
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser(
                username='admin',
                email='admin@example.com',
                password='123',
                first_name='Admin',
                last_name='User',
                is_staff=True,
                is_superuser=True
            )
            self.stdout.write(self.style.SUCCESS('Superuser created: admin/123'))
        else:
            self.stdout.write('Superuser already exists. Username: admin')

        # Create superadmin (application superadmin)
        if not User.objects.filter(username='superadmin').exists():
            User.objects.create_user(
                username='superadmin',
                email='superadmin@example.com',
                password='123',
                first_name='Super',
                last_name='Admin',
                role='SUPERADMIN',
                is_active=True
            )
            self.stdout.write(self.style.SUCCESS('Superadmin created: superadmin/123'))
        else:
            self.stdout.write('Superadmin already exists. Username: superadmin')

        # Set up default settings if needed
        from django.conf import settings
        if not hasattr(settings, 'TELEGRAM_BOT_TOKEN'):
            self.stdout.write(self.style.WARNING('TELEGRAM_BOT_TOKEN is not set in settings'))
            self.stdout.write(self.style.WARNING('Please add TELEGRAM_BOT_TOKEN to your .env file'))
