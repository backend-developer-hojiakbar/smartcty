from django.core.management.base import BaseCommand
from django.utils import timezone
from smartcity_app.models import IoTDevice, Room, Boiler
import random
import requests
import time
from datetime import datetime
import json


class Command(BaseCommand):
    help = 'Simulate IoT sensor data updates for temperature and humidity'

    def add_arguments(self, parser):
        parser.add_argument(
            '--run-once',
            action='store_true',
            help='Run the simulation once instead of continuously',
        )
        parser.add_argument(
            '--interval',
            type=int,
            default=60,  # Default to 60 seconds
            help='Interval between sensor updates in seconds (default: 60)',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Starting IoT sensor simulation...')
        )
        
        if options['run_once']:
            self.simulate_sensor_updates()
        else:
            self.run_continuous_simulation(options['interval'])
        
        self.stdout.write(
            self.style.SUCCESS('IoT sensor simulation completed')
        )

    def run_continuous_simulation(self, interval):
        """Run the simulation continuously at specified intervals"""
        while True:
            self.simulate_sensor_updates()
            self.stdout.write(
                self.style.SUCCESS(f'Waiting {interval} seconds for next sensor update cycle at {timezone.now()}')
            )
            time.sleep(interval)

    def simulate_sensor_updates(self):
        """Simulate IoT sensor data updates for all devices"""
        devices = IoTDevice.objects.filter(is_active=True)
        
        for device in devices:
            # Generate simulated sensor data
            sensor_data = self.generate_sensor_data(device)
            
            # Update the device and its associated room or boiler
            self.update_device_data(device, sensor_data)
            
            self.stdout.write(
                f"Device {device.device_id} updated: temp {sensor_data['temperature']}°C, "
                f"humidity {sensor_data['humidity']}%"
            )

    def generate_sensor_data(self, device):
        """Generate simulated sensor data based on the device type and location"""
        # Base temperature and humidity values
        if device.room:
            # Room temperature typically between 18-24°C
            base_temp = 21.0
            base_humidity = 50.0
        elif device.boiler:
            # Boiler area might be warmer and more humid
            base_temp = 25.0
            base_humidity = 60.0
        else:
            # Default values if not associated with room or boiler
            base_temp = 20.0
            base_humidity = 45.0
        
        # Add some random variation
        temperature = round(base_temp + random.uniform(-5, 5), 1)
        humidity = round(max(0, min(100, base_humidity + random.uniform(-20, 20))), 1)
        
        # Add some correlation between temperature and humidity
        if temperature > 25:
            humidity = min(100, humidity + 5)  # Higher temp might mean higher humidity in some cases
        elif temperature < 15:
            humidity = max(0, humidity - 5)    # Lower temp might mean lower humidity
        
        return {
            'device_id': device.device_id,
            'temperature': temperature,
            'humidity': humidity,
            'sleep_seconds': 2000,  # Fixed sleep time
            'timestamp': int(timezone.now().timestamp())
        }

    def update_device_data(self, device, sensor_data):
        """Update the IoT device and its associated room or boiler with sensor data"""
        # Update device's last seen time
        device.last_seen = timezone.now()
        device.save()
        
        # Update associated room or boiler
        if device.room:
            device.room.temperature = sensor_data['temperature']
            device.room.humidity = sensor_data['humidity']
            device.room.last_updated = timezone.now()
            device.room.save()
        elif device.boiler:
            device.boiler.temperature = sensor_data['temperature']
            device.boiler.humidity = sensor_data['humidity']
            device.boiler.last_updated = timezone.now()
            device.boiler.save()