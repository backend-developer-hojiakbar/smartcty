from django.core.management.base import BaseCommand
from django.utils import timezone
from smartcity_app.models import WasteBin
import random
import time
from datetime import datetime, timedelta


class Command(BaseCommand):
    help = 'Automatically analyze waste bins via camera every 30 minutes'

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Starting automatic waste bin analysis...')
        )
        
        # For demo purposes, we'll just update the bins once
        # In a real system, this would run continuously or be scheduled with cron
        self.analyze_bins()
        
        self.stdout.write(
            self.style.SUCCESS('Waste bin analysis completed')
        )
    
    def analyze_bins(self):
        """Analyze all waste bins and update their fill levels"""
        bins = WasteBin.objects.all()
        
        for bin in bins:
            # Simulate camera analysis
            # In a real system, this would process images from bin.camera_url
            old_fill_level = bin.fill_level
            old_is_full = bin.is_full
            
            # Randomly adjust fill level based on some logic
            # If bin was nearly full, it might get emptied by a truck
            if old_fill_level > 80:
                # 30% chance that a full bin gets emptied by a truck
                if random.random() < 0.3:
                    bin.fill_level = random.randint(5, 20)
                else:
                    # If not emptied, it might fill up more
                    if random.random() < 0.7:  # 70% chance to fill more
                        bin.fill_level = min(100, old_fill_level + random.randint(1, 10))
            else:
                # If not full, it might fill up gradually
                if random.random() < 0.5:  # 50% chance to fill more
                    bin.fill_level = min(100, old_fill_level + random.randint(1, 5))
            
            # Update is_full status based on fill_level
            bin.is_full = bin.fill_level > 80
            
            # Update last analysis time
            bin.last_analysis = timezone.now()
            
            # Update image source to indicate it was analyzed by camera
            if bin.image_source != 'BOT':
                bin.image_source = 'CCTV'  # Camera captured image
            
            bin.save()
            
            # Log the change
            if old_fill_level != bin.fill_level or old_is_full != bin.is_full:
                self.stdout.write(
                    f"Bin {bin.id} updated: fill level {old_fill_level}% -> {bin.fill_level}%, "
                    f"full status: {old_is_full} -> {bin.is_full}"
                )