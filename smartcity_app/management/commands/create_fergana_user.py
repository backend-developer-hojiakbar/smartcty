from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Create a regular user with username "fergana" and password "123"'

    def handle(self, *args, **options):
        username = 'fergana'
        password = '123'
        email = 'fergana@example.com'
        
        if User.objects.filter(username=username).exists():
            self.stdout.write(
                self.style.WARNING(f'User "{username}" already exists')
            )
        else:
            user = User.objects.create_user(
                username=username,
                password=password,
                email=email,
                first_name='Fergana',
                last_name='User',
                is_active=True
            )
            self.stdout.write(
                self.style.SUCCESS(f'Successfully created user "{username}" with password "{password}"')
            )
            
            # Print login information
            self.stdout.write('\n' + '='*50)
            self.stdout.write(self.style.SUCCESS('User created successfully!'))
            self.stdout.write('='*50)
            self.stdout.write(f'Username: {username}')
            self.stdout.write(f'Password: {password}')
            self.stdout.write('='*50)
