from django.core.management.base import BaseCommand
from django.utils import timezone
from smartcity_app.models import WasteBin
import random
import requests
from datetime import datetime, timedelta
import base64
import io
from PIL import Image


class Command(BaseCommand):
    help = 'Simulate camera screenshots every 30 minutes with enhanced AI analysis'

    def add_arguments(self, parser):
        parser.add_argument(
            '--run-once',
            action='store_true',
            help='Run the simulation once instead of continuously',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Starting camera screenshot simulation...')
        )
        
        if options['run_once']:
            self.simulate_screenshots()
        else:
            self.run_continuous_simulation()
        
        self.stdout.write(
            self.style.SUCCESS('Camera screenshot simulation completed')
        )

    def run_continuous_simulation(self):
        """Run the simulation continuously every 30 minutes"""
        import time
        
        while True:
            self.simulate_screenshots()
            self.stdout.write(
                self.style.SUCCESS(f'Waiting 30 minutes for next screenshot cycle at {timezone.now() + timedelta(minutes=30)}')
            )
            time.sleep(30 * 60)  # Wait 30 minutes

    def simulate_screenshots(self):
        """Simulate camera screenshots for all waste bins with AI analysis"""
        bins = WasteBin.objects.all()
        
        for bin in bins:
            # Generate a simulated image for the bin
            image_url = self.generate_simulated_image(bin)
            
            if image_url:
                # Update bin with the new image and AI analysis
                ai_analysis = self.analyze_image_with_ai(image_url, bin)
                
                # Update bin status based on AI analysis
                bin.image_url = image_url
                bin.image_source = 'CCTV'  # Mark as camera captured
                bin.last_analysis = f"AI tahlili: {ai_analysis.get('notes', 'Tahlil amalga oshirildi')}, Isbot: {ai_analysis.get('isWasteBin')}, IsFull: {ai_analysis.get('isFull')}, Conf: {ai_analysis.get('confidence')}%"
                
                # Update fill level and full status based on AI analysis
                if 'fillLevel' in ai_analysis:
                    bin.fill_level = ai_analysis['fillLevel']
                
                if 'isFull' in ai_analysis:
                    bin.is_full = ai_analysis['isFull']
                
                bin.save()
                
                self.stdout.write(
                    f"Bin {bin.id} updated with camera screenshot: fill level {bin.fill_level}%, "
                    f"full status: {bin.is_full}, confidence: {ai_analysis.get('confidence')}%"
                )

    def generate_simulated_image(self, bin):
        """Generate a simulated image URL for the waste bin"""
        # In a real system, this would capture an actual image from the camera
        # For simulation, we'll return a placeholder image URL
        # This could be a service that generates simulated images based on the bin's status
        base_url = "https://via.placeholder.com/640x480"
        color = "red" if bin.fill_level > 80 else "green" if bin.fill_level < 30 else "yellow"
        return f"{base_url}/000000/{color}.png?text=Waste+Bin+{str(bin.id)[:8]}&fill={bin.fill_level}%"

    def analyze_image_with_ai(self, image_url, bin):
        """Enhanced AI analysis of waste bin images"""
        try:
            # In a real system, this would connect to an AI service like Google's Gemini
            # For now, we'll simulate the AI analysis based on the bin's current state
            
            # Simulate AI analysis based on current fill level
            current_fill = bin.fill_level
            is_full = current_fill > 80
            
            # Add some randomness to make it more realistic
            confidence = min(95, max(60, 80 + random.randint(-10, 10)))
            
            # Determine if this actually looks like a waste bin
            is_waste_bin = True  # Assume it's a waste bin since we're analyzing a waste bin object
            
            # Adjust fill level based on AI analysis
            ai_fill_level = current_fill
            if random.random() < 0.1:  # 10% chance of adjustment
                adjustment = random.randint(-10, 10)
                ai_fill_level = max(0, min(100, current_fill + adjustment))
                is_full = ai_fill_level > 80
            
            notes = f"Konteyner {ai_fill_level}% to'la. {'To\'lgan' if is_full else 'To\'lmagan'}"
            
            # If the fill level is high, check if it might be overflowing
            if ai_fill_level > 90 and random.random() < 0.3:
                notes = "Konteyner toshib ketayotgan. Tez orada yuklash kerak."
                is_full = True
                ai_fill_level = 100
            elif ai_fill_level < 20 and random.random() < 0.2:
                notes = "Konteyner hali bo'sh. Yana to'lishi kerak."
            
            return {
                'isWasteBin': is_waste_bin,
                'isFull': is_full,
                'fillLevel': ai_fill_level,
                'confidence': confidence,
                'notes': notes
            }
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error in AI analysis for bin {bin.id}: {str(e)}")
            )
            # Return default values if AI analysis fails
            return {
                'isWasteBin': True,
                'isFull': bin.fill_level > 80,
                'fillLevel': bin.fill_level,
                'confidence': 70,
                'notes': 'AI tahlil qilishda xatolik yuz berdi'
            }