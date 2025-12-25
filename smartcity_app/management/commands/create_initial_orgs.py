from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from smartcity_app.models import Organization, Region, District, Coordinate
from django.core.management import BaseCommand
import uuid


class Command(BaseCommand):
    help = 'Create initial organizations for the Smart City application'

    def handle(self, *args, **options):
        # Create a coordinate for the region center
        region_center, created = Coordinate.objects.get_or_create(
            lat=40.3734,
            lng=71.7978,
            defaults={'lat': 40.3734, 'lng': 71.7978}
        )
        
        # Get or create regions and districts
        fergana_region, created = Region.objects.get_or_create(
            name="Farg'ona Viloyati",
            defaults={
                'id': uuid.uuid4(),
                'center': region_center
            }
        )
        
        district_center, created = Coordinate.objects.get_or_create(
            lat=40.3734,
            lng=71.7978,
            defaults={'lat': 40.3734, 'lng': 71.7978}
        )
        
        fergana_city_district, created = District.objects.get_or_create(
            name="Farg'ona Shahar",
            defaults={
                'id': uuid.uuid4(),
                'region': fergana_region,  # Add the region reference
                'center': district_center
            }
        )
        
        # Create initial organizations
        org_data = [
            {
                'name': "Farg'ona Shahar (Chiqindi Monitoringi)",
                'type': 'HOKIMIYAT',
                'login': 'fergana_admin',
                'password': '123',
                'enabled_modules': ['DASHBOARD', 'WASTE'],
                'lat': 40.3734,
                'lng': 71.7978
            },
            {
                'name': "Marg'ilon Shahar",
                'type': 'HOKIMIYAT',
                'login': 'margilon_admin',
                'password': '123',
                'enabled_modules': ['DASHBOARD', 'WASTE', 'AIR'],
                'lat': 40.4772,
                'lng': 71.7214
            },
            {
                'name': "Qo'qon Shahar",
                'type': 'HOKIMIYAT',
                'login': 'kokand_admin',
                'password': '123',
                'enabled_modules': ['DASHBOARD', 'WASTE', 'SECURITY'],
                'lat': 40.5286,
                'lng': 70.9426
            },
            {
                'name': "Andijon Shahar",
                'type': 'AGENCY',
                'login': 'andijan_admin',
                'password': '123',
                'enabled_modules': ['DASHBOARD', 'ECO_CONTROL', 'AIR'],
                'lat': 40.7821,
                'lng': 72.3442
            },
            {
                'name': "Toshkent Shahar",
                'type': 'ENTERPRISE',
                'login': 'tashkent_admin',
                'password': '123',
                'enabled_modules': ['DASHBOARD', 'WASTE', 'AIR', 'SECURITY', 'ECO_CONTROL'],
                'lat': 41.2995,
                'lng': 69.2401
            }
        ]
        
        created_count = 0
        for org_info in org_data:
            # Create a coordinate for each organization
            org_center, created = Coordinate.objects.get_or_create(
                lat=org_info['lat'],
                lng=org_info['lng'],
                defaults={'lat': org_info['lat'], 'lng': org_info['lng']}
            )
            
            org, created = Organization.objects.get_or_create(
                name=org_info['name'],
                defaults={
                    'id': uuid.uuid4(),
                    'type': org_info['type'],
                    'login': org_info['login'],
                    'password': org_info['password'],
                    'enabled_modules': org_info['enabled_modules'],
                    'region': fergana_region,
                    'district': fergana_city_district,
                    'center': org_center
                }
            )
            if created:
                created_count += 1
                self.stdout.write(f"Created organization: {org.name}")
            else:
                self.stdout.write(f"Organization already exists: {org.name}")
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created_count} organizations')
        )