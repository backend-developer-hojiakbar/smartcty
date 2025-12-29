from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Create superuser (admin/123) and superadmin (superadmin/123) accounts'

    def handle(self, *args, **options):
        # Create regular admin user (Django administrator)
        admin_username = 'admin'
        admin_password = '123'
        
        if User.objects.filter(username=admin_username).exists():
            self.stdout.write(
                self.style.WARNING(f'Admin user "{admin_username}" already exists')
            )
        else:
            admin_user = User.objects.create_user(
                username=admin_username,
                password=admin_password
            )
            admin_user.is_staff = True
            admin_user.is_superuser = True
            admin_user.save()
            self.stdout.write(
                self.style.SUCCESS(f'Successfully created admin user "{admin_username}" with password "{admin_password}"')
            )

        # Create superadmin user (application superadmin)
        superadmin_username = 'superadmin'
        superadmin_password = '123'
        
        if User.objects.filter(username=superadmin_username).exists():
            self.stdout.write(
                self.style.WARNING(f'Superadmin user "{superadmin_username}" already exists')
            )
        else:
            superadmin_user = User.objects.create_user(
                username=superadmin_username,
                password=superadmin_password
            )
            superadmin_user.is_staff = True
            superadmin_user.is_superuser = True
            superadmin_user.save()
            self.stdout.write(
                self.style.SUCCESS(f'Successfully created superadmin user "{superadmin_username}" with password "{superadmin_password}"')
            )