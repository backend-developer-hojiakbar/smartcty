"""
Management command to generate QR codes for all waste bins
"""
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from smartcity_app.models import WasteBin
import qrcode
from io import BytesIO
from django.core.files import File


class Command(BaseCommand):
    help = 'Generate QR codes for all waste bins'

    def handle(self, *args, **options):
        self.stdout.write('Generating QR codes for waste bins...')
        
        # Create QR codes directory if it doesn't exist
        qr_codes_dir = os.path.join(settings.MEDIA_ROOT, 'qr_codes')
        os.makedirs(qr_codes_dir, exist_ok=True)
        
        bins = WasteBin.objects.all()
        for bin_obj in bins:
            # Create QR code with bin ID
            qr_data = f"https://t.me/tozafargonabot?start={bin_obj.id}"
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(qr_data)
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")
            
            # Save the QR code image
            qr_filename = f"bin_{bin_obj.id}_qr.png"
            qr_path = os.path.join(qr_codes_dir, qr_filename)
            
            img.save(qr_path)
            
            # Update the bin's QR code URL field
            qr_url = f"http://127.0.0.1:8000/media/qr_codes/{qr_filename}"
            
            # Update the bin object with the QR code URL
            bin_obj.qr_code_url = qr_url
            bin_obj.save()
            
            self.stdout.write(f'Generated QR code for bin {bin_obj.id}: {qr_filename}')
            self.stdout.write(f'QR Code URL: {qr_url}')
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully generated QR codes for {bins.count()} waste bins!'
            )
        )