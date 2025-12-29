"""
Management command to populate Farg'ona city data for waste management and temperature control modules
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from smartcity_app.models import (
    Region, District, Organization, Coordinate, 
    WasteBin, Truck, Facility, Room, Boiler, DeviceHealth
)
import uuid
from django.utils import timezone


class Command(BaseCommand):
    help = 'Populate Farg\'ona city data for waste management and temperature control modules'

    def handle(self, *args, **options):
        self.stdout.write('Starting to populate Farg\'ona city data...')

        # Create Farg'ona region
        fargona_region, created = Region.objects.get_or_create(
            name="Farg'ona",
            defaults={
                'center': Coordinate.objects.create(lat=40.3775, lng=71.7861)
            }
        )
        if created:
            self.stdout.write(f'Created region: {fargona_region.name}')
        else:
            self.stdout.write(f'Using existing region: {fargona_region.name}')

        # Create Farg'ona districts
        districts_data = [
            {"name": "Farg'ona Shahri", "lat": 40.3775, "lng": 71.7861},
            {"name": "Qo'shtepa", "lat": 40.5123, "lng": 71.4567},
            {"name": "Buvayda", "lat": 40.2345, "lng": 71.9876},
            {"name": "Yozyovon", "lat": 40.1234, "lng": 71.6543},
        ]

        districts = []
        for district_data in districts_data:
            district, created = District.objects.get_or_create(
                name=district_data["name"],
                region=fargona_region,
                defaults={
                    'center': Coordinate.objects.create(
                        lat=district_data["lat"], 
                        lng=district_data["lng"]
                    )
                }
            )
            districts.append(district)
            if created:
                self.stdout.write(f'Created district: {district.name}')
            else:
                self.stdout.write(f'Using existing district: {district.name}')

        # Create organizations for waste management
        waste_org, created = Organization.objects.get_or_create(
            name="Farg'ona Tozalik Agenligi",
            type="AGENCY",
            login="fargona_tozalik",
            password="pbkdf2_sha256$600000$...$...",  # This would be a hashed password in real scenario
            region=fargona_region,
            district=districts[0],
            center=Coordinate.objects.create(lat=40.3780, lng=71.7870),
            defaults={
                'enabled_modules': ['WASTE', 'CLIMATE']
            }
        )
        if created:
            self.stdout.write(f'Created waste management organization: {waste_org.name}')
        else:
            self.stdout.write(f'Using existing waste management organization: {waste_org.name}')

        # Create organization for temperature control
        climate_org, created = Organization.objects.get_or_create(
            name="Farg'ona Ta'lim Aholi Yashash Shartlari Boshqarmasi",
            type="HOKIMIYAT",
            login="fargona_climate",
            password="pbkdf2_sha256$600000$...$...",
            region=fargona_region,
            district=districts[0],
            center=Coordinate.objects.create(lat=40.3785, lng=71.7875),
            defaults={
                'enabled_modules': ['CLIMATE', 'WASTE']
            }
        )
        if created:
            self.stdout.write(f'Created climate control organization: {climate_org.name}')
        else:
            self.stdout.write(f'Using existing climate control organization: {climate_org.name}')

        # Create waste bins for Farg'ona
        waste_bins_data = [
            {"address": "Farg'ona shahar, Mustaqillik ko'chasi 15-uy", "lat": 40.3770, "lng": 71.7850, "toza_hudud": "1-sonli Toza Hudud"},
            {"address": "Farg'ona shahar, Beruniy ko'chasi 8-uy", "lat": 40.3780, "lng": 71.7860, "toza_hudud": "1-sonli Toza Hudud"},
            {"address": "Farg'ona shahar, Navoiy ko'chasi 22-uy", "lat": 40.3790, "lng": 71.7870, "toza_hudud": "2-sonli Toza Hudud"},
            {"address": "Qo'shtepa tumani, Markaziy maydon", "lat": 40.5100, "lng": 71.4500, "toza_hudud": "3-sonli Toza Hudud"},
            {"address": "Buvayda tumani, Boshkvartir", "lat": 40.2300, "lng": 71.9800, "toza_hudud": "4-sonli Toza Hudud"},
        ]

        for bin_data in waste_bins_data:
            waste_bin, created = WasteBin.objects.get_or_create(
                address=bin_data["address"],
                organization=waste_org,
                defaults={
                    'location': Coordinate.objects.create(
                        lat=bin_data["lat"],
                        lng=bin_data["lng"]
                    ),
                    'toza_hudud': bin_data["toza_hudud"],
                    'fill_level': 45,  # Random initial fill level
                    'is_full': False,
                    'device_health': {
                        'battery_level': 95,
                        'signal_strength': 85,
                        'last_ping': timezone.now().isoformat(),
                        'firmware_version': 'v1.0',
                        'is_online': True
                    }
                }
            )
            if created:
                self.stdout.write(f'Created waste bin: {waste_bin.address}')
            else:
                self.stdout.write(f'Using existing waste bin: {waste_bin.address}')

        # Create trucks for waste collection
        truck_data = [
            {"driver_name": "Rahimov Akmal", "plate_number": "FA 777 AA", "phone": "+998901234567", "toza_hudud": "1-sonli Toza Hudud"},
            {"driver_name": "Karimov Jonibek", "plate_number": "FA 778 AA", "phone": "+998901234568", "toza_hudud": "2-sonli Toza Hudud"},
            {"driver_name": "Habibov Oybek", "plate_number": "FA 779 AA", "phone": "+998901234569", "toza_hudud": "3-sonli Toza Hudud"},
        ]

        for truck_datum in truck_data:
            truck, created = Truck.objects.get_or_create(
                plate_number=truck_datum["plate_number"],
                organization=waste_org,
                defaults={
                    'driver_name': truck_datum["driver_name"],
                    'phone': truck_datum["phone"],
                    'toza_hudud': truck_datum["toza_hudud"],
                    'location': Coordinate.objects.create(lat=40.3775, lng=71.7861),  # Starting from center
                    'status': 'IDLE',
                    'fuel_level': 85,
                    'login': f"driver_{truck_datum['plate_number'].replace(' ', '_').lower()}",
                    'password': '123'
                }
            )
            if created:
                self.stdout.write(f'Created truck: {truck.plate_number}')
            else:
                self.stdout.write(f'Using existing truck: {truck.plate_number}')

        # Create schools, kindergartens, and hospitals with temperature control
        facilities_data = [
            {
                "name": "Farg'ona 1-maktab",
                "type": "SCHOOL",
                "mfy": "Farg'ona Shahri",
                "lat": 40.3760,
                "lng": 71.7840,
                "manager_name": "Karimova Gulnora"
            },
            {
                "name": "Farg'ona 5-maktab",
                "type": "SCHOOL",
                "mfy": "Farg'ona Shahri", 
                "lat": 40.3795,
                "lng": 71.7885,
                "manager_name": "Rahimov Asliddin"
            },
            {
                "name": "Farg'ona 1-bog'cha",
                "type": "KINDERGARTEN",
                "mfy": "Farg'ona Shahri",
                "lat": 40.3750,
                "lng": 71.7830,
                "manager_name": "Hakimova Malika"
            },
            {
                "name": "Farg'ona 3-bog'cha", 
                "type": "KINDERGARTEN",
                "mfy": "Qo'shtepa",
                "lat": 40.5110,
                "lng": 71.4550,
                "manager_name": "Muminova Dildora"
            },
            {
                "name": "Farg'ona Shahar Bosh Shifoxonasi",
                "type": "HOSPITAL",
                "mfy": "Farg'ona Shahri",
                "lat": 40.3800,
                "lng": 71.7890,
                "manager_name": "Tursunov Davron"
            },
            {
                "name": "Qo'shtepa Tuman Bemorxonas", 
                "type": "HOSPITAL",
                "mfy": "Qo'shtepa",
                "lat": 40.5130,
                "lng": 71.4570,
                "manager_name": "Rashidov Javlon"
            }
        ]

        for facility_data in facilities_data:
            facility, created = Facility.objects.get_or_create(
                name=facility_data["name"],
                type=facility_data["type"],
                mfy=facility_data["mfy"],
                defaults={
                    'overall_status': 'OPTIMAL',
                    'energy_usage': 75,
                    'efficiency_score': 85,
                    'manager_name': facility_data["manager_name"],
                    'last_maintenance': timezone.now(),
                    'history': [75, 76, 74, 78, 77, 80, 79, 76, 75, 77],
                }
            )
            if created:
                self.stdout.write(f'Created facility: {facility.name}')
                
                # Create a device health object for the boiler
                device_health = DeviceHealth.objects.create(
                    battery_level=90,
                    signal_strength=95,
                    last_ping=timezone.now(),
                    firmware_version='v1.0',
                    is_online=True
                )
                
                # Create a boiler for the facility
                boiler, boiler_created = Boiler.objects.get_or_create(
                    name=f"{facility.name} Qozonxonasi",
                    defaults={
                        'target_humidity': 50,
                        'humidity': 48,
                        'status': 'OPTIMAL',
                        'trend': [45, 46, 47, 48, 49, 50, 51, 50, 49, 48],
                        'device_health': device_health
                    }
                )
                if boiler_created:
                    self.stdout.write(f'Created boiler for {facility.name}')
                
                # Create rooms for the facility
                for i in range(3):  # Create 3 rooms per facility
                    room, room_created = Room.objects.get_or_create(
                        name=f"{facility.name} Xona {i+101}",
                        defaults={
                            'target_humidity': 50,
                            'humidity': 47 + i,  # Slightly different humidity for each room
                            'status': 'OPTIMAL',
                            'trend': [45, 46, 47, 48, 49, 50, 51, 50, 49, 48]
                        }
                    )
                    if room_created:
                        self.stdout.write(f'Created room: {room.name}')
                    
                    # Add the room to the boiler
                    boiler.connected_rooms.add(room)
                
                # Add the boiler to the facility
                facility.boilers.add(boiler)
                
            else:
                self.stdout.write(f'Using existing facility: {facility.name}')

        self.stdout.write(
            self.style.SUCCESS(
                'Successfully populated Farg\'ona city data for both waste management and temperature control modules!'
            )
        )