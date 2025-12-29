from django.core.management.base import BaseCommand
from smartcity_app.models import Room, Boiler, IoTDevice, Coordinate
import random
import uuid


class Command(BaseCommand):
    help = 'Associate existing rooms and boilers with IoT devices for temperature and humidity monitoring'

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Starting IoT device association...')
        )
        
        # Create IoT devices for rooms
        self.associate_rooms_with_iot_devices()
        
        # Create IoT devices for boilers
        self.associate_boilers_with_iot_devices()
        
        self.stdout.write(
            self.style.SUCCESS('IoT device association completed')
        )

    def associate_rooms_with_iot_devices(self):
        """Associate rooms with temperature and humidity sensors"""
        rooms = Room.objects.all()
        
        for room in rooms:
            # Create a coordinate near the facility's center for the IoT device
            # For this demo, we'll use the facility's location if available, otherwise create a random one
            facility = room.facility
            if facility:
                # Create a coordinate near the facility's center
                base_lat = 40.3853  # Farg'ona latitude
                base_lng = 71.7797  # Farg'ona longitude
                
                # Add small random offset for each room
                lat_offset = random.uniform(-0.001, 0.001)
                lng_offset = random.uniform(-0.001, 0.001)
                
                coordinate = Coordinate.objects.create(
                    lat=base_lat + lat_offset,
                    lng=base_lng + lng_offset
                )
            else:
                # Create a default coordinate if no facility
                coordinate = Coordinate.objects.create(
                    lat=40.3853 + random.uniform(-0.01, 0.01),
                    lng=71.7797 + random.uniform(-0.01, 0.01)
                )
            
            # Create IoT device for the room
            device_id = f"ESP-{uuid.uuid4().hex[:8].upper()}"
            
            iot_device, created = IoTDevice.objects.get_or_create(
                device_id=device_id,
                defaults={
                    'device_type': 'BOTH',  # Temperature and humidity sensor
                    'room': room,
                    'location': coordinate,
                    'is_active': True
                }
            )
            
            if created:
                self.stdout.write(
                    f"Created IoT device {device_id} for room {room.name} in {room.facility.name if room.facility else 'Unknown Facility'}"
                )
            else:
                # If device already exists, just update the room association
                iot_device.room = room
                iot_device.save()
                self.stdout.write(
                    f"Updated IoT device {device_id} to associate with room {room.name}"
                )

    def associate_boilers_with_iot_devices(self):
        """Associate boilers with temperature and humidity sensors"""
        boilers = Boiler.objects.all()
        
        for boiler in boilers:
            # Create a coordinate near the facility's center for the IoT device
            # Since boilers don't have a direct facility link, we'll create a random coordinate
            coordinate = Coordinate.objects.create(
                lat=40.3853 + random.uniform(-0.01, 0.01),
                lng=71.7797 + random.uniform(-0.01, 0.01)
            )
            
            # Create IoT device for the boiler
            device_id = f"ESP-{uuid.uuid4().hex[:8].upper()}"
            
            iot_device, created = IoTDevice.objects.get_or_create(
                device_id=device_id,
                defaults={
                    'device_type': 'BOTH',  # Temperature and humidity sensor
                    'boiler': boiler,
                    'location': coordinate,
                    'is_active': True
                }
            )
            
            if created:
                self.stdout.write(
                    f"Created IoT device {device_id} for boiler {boiler.name}"
                )
            else:
                # If device already exists, just update the boiler association
                iot_device.boiler = boiler
                iot_device.save()
                self.stdout.write(
                    f"Updated IoT device {device_id} to associate with boiler {boiler.name}"
                )