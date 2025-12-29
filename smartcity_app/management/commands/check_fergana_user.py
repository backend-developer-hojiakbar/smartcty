from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Check and fix fergana user with proper permissions'

    def handle(self, *args, **options):
        username = 'fergana'
        password = '123'
        email = 'fergana@example.com'
        
        try:
            user = User.objects.get(username=username)
            self.stdout.write(self.style.SUCCESS(f'User "{username}" exists'))
            
            # Check and update password if needed
            if not user.check_password(password):
                user.set_password(password)
                user.save()
                self.stdout.write(self.style.SUCCESS('Password updated to "123"'))
            
            # Ensure user is active
            if not user.is_active:
                user.is_active = True
                user.save()
                self.stdout.write(self.style.SUCCESS('User activated'))
                
            # Ensure user has a role
            if not hasattr(user, 'role') or not user.role:
                user.role = 'ADMIN'  # or whatever role is appropriate
                user.save()
                self.stdout.write(self.style.SUCCESS(f'Assigned {user.role} role to user'))
                
            self.stdout.write('\n' + '='*50)
            self.stdout.write(self.style.SUCCESS('User Information:'))
            self.stdout.write('='*50)
            self.stdout.write(f'Username: {user.username}')
            self.stdout.write(f'Email: {user.email}')
            self.stdout.write(f'Active: {user.is_active}')
            self.stdout.write(f'Role: {getattr(user, "role", "Not set")}')
            self.stdout.write('='*50)
            
        except User.DoesNotExist:
            # Create the user if doesn't exist
            user = User.objects.create_user(
                username=username,
                password=password,
                email=email,
                first_name='Fergana',
                last_name='User',
                is_active=True
            )
            user.role = 'ADMIN'  # Set appropriate role
            user.save()
            
            self.stdout.write(self.style.SUCCESS(f'Successfully created user "{username}" with password "{password}"'))
            self.stdout.write('\n' + '='*50)
            self.stdout.write(self.style.SUCCESS('User created successfully!'))
            self.stdout.write('='*50)
            self.stdout.write(f'Username: {username}')
            self.stdout.write(f'Password: {password}')
            self.stdout.write(f'Role: {user.role}')
            self.stdout.write('='*50)
