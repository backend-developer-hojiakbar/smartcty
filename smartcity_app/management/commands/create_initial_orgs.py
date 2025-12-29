from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from smartcity_app.models import Organization, Region, District, Coordinate
from django.core.management import BaseCommand
import uuid


class Command(BaseCommand):
    help = 'Create initial organizations for the Smart City application'

    def handle(self, *args, **options):
        # This command is disabled to prevent automatic organization creation.
        # Organizations should only be created via the API by authorized users.
        self.stdout.write(
            self.style.WARNING('This command is disabled. Organizations must be created via API.')
        )