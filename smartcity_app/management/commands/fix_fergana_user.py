from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from smartcity_app.models import Organization, Region, District, Coordinate
from django.db import transaction

class Command(BaseCommand):
    help = 'Create or fix the fergana user as an Organization with admin privileges'

    def handle(self, *args, **options):
        username = 'fergana'
        password = '123'
        email = 'fergana@example.com'
        
        # Create a default region and district if they don't exist
        with transaction.atomic():
            # Create a default coordinate for the region
            region_coord, _ = Coordinate.objects.get_or_create(
                lat=40.3864,
                lng=71.7864,
                defaults={'lat': 40.3864, 'lng': 71.7864}
            )
            
            # Create a default region
            region, _ = Region.objects.get_or_create(
                name="Farg'ona viloyati",
                defaults={
                    'name': "Farg'ona viloyati",
                    'center': region_coord
                }
            )
            
            # Create a default district coordinate
            district_coord, _ = Coordinate.objects.get_or_create(
                lat=40.3864,
                lng=71.7864,
                defaults={'lat': 40.3864, 'lng': 71.7864}
            )
            
            # Create a default district
            district, _ = District.objects.get_or_create(
                name="Farg'ona tumani",
                region=region,
                defaults={
                    'name': "Farg'ona tumani",
                    'region': region,
                    'center': district_coord
                }
            )
            
            # Create a default organization coordinate
            org_coord, _ = Coordinate.objects.get_or_create(
                lat=40.3864,
                lng=71.7864,
                defaults={'lat': 40.3864, 'lng': 71.7864}
            )
            
            # Create or update the organization
            org, created = Organization.objects.update_or_create(
                login=username,
                defaults={
                    'name': 'Fergana Admin',
                    'type': 'HOKIMIYAT',
                    'password': password,  # In production, use set_password()
                    'region': region,
                    'district': district,
                    'center': org_coord,
                    'enabled_modules': ['DASHBOARD', 'WASTE', 'CLIMATE']  # Only WASTE and CLIMATE for Farg'ona
                }
            )
            
            # Also create a regular user for Django admin if needed
            User = get_user_model()
            user, user_created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': email,
                    'first_name': 'Fergana',
                    'last_name': 'Admin',
                    'is_staff': True,
                    'is_superuser': True
                }
            )
            
            if not user_created:
                # Update existing user
                user.email = email
                user.first_name = 'Fergana'
                user.last_name = 'Admin'
                user.is_staff = True
                user.is_superuser = True
                user.save()
            
            # Set password for the user (this will hash it properly)
            user.set_password(password)
            user.save()
            
            # Set password for the organization (in production, use proper hashing)
            # This is just for development
            org.password = password
            org.save()
            
            if created:
                self.stdout.write(self.style.SUCCESS(f'Successfully created organization "{username}" with password "{password}"'))
            else:
                self.stdout.write(self.style.SUCCESS(f'Successfully updated organization "{username}" with password "{password}"'))
            
            self.stdout.write('\n' + '='*50)
            self.stdout.write(self.style.SUCCESS('Organization created/updated successfully!'))
            self.stdout.write('='*50)
            self.stdout.write(f'Login: {username}')
            self.stdout.write(f'Password: {password}')
            self.stdout.write(f'Role: {org.type}')
            self.stdout.write('='*50)
            self.stdout.write('\nYou can now log in with these credentials at http://localhost:3000')
