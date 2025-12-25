from django.apps import AppConfig
import threading
import time
from django.core.management import call_command


class SmartcityAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'smartcity_app'

    def ready(self):
        # Start the background task to analyze waste bins every 30 minutes
        from django.conf import settings
        if settings.DEBUG:  # Only run in development
            thread = threading.Thread(target=self.run_periodic_analysis, daemon=True)
            thread.start()

    def run_periodic_analysis(self):
        """Run waste bin analysis every 30 minutes"""
        import time
        from django.utils import timezone
        
        print("Starting automated waste bin analysis service...")
        
        while True:
            try:
                # Wait for 30 minutes (30 * 60 seconds)
                time.sleep(30 * 60)
                
                # Run the analysis command
                print(f"[{timezone.now()}] Running automated waste bin analysis...")
                call_command('analyze_waste_bins')
                print(f"[{timezone.now()}] Waste bin analysis completed.")
                
            except Exception as e:
                print(f"Error in periodic analysis: {e}")
                # Wait for a shorter time before retrying
                time.sleep(5 * 60)  # Wait 5 minutes before retrying