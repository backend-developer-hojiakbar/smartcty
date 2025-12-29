from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.core.paginator import Paginator
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from .models import (
    Organization, WasteBin, Truck, MoistureSensor, Facility, AirSensor, 
    SOSColumn, EcoViolation, ConstructionSite, LightPole, Bus, CallRequest,
    Coordinate, Region, District, Room, Boiler, ConstructionMission, LightROI,
    ResponsibleOrg, CallRequestTimeline, Notification, ReportEntry, UtilityNode,
    DeviceHealth, IoTDevice
)
from .serializers import (
    OrganizationSerializer, WasteBinSerializer, TruckSerializer, 
    MoistureSensorSerializer, FacilitySerializer, AirSensorSerializer, 
    SOSColumnSerializer, EcoViolationSerializer, ConstructionSiteSerializer, 
    LightPoleSerializer, BusSerializer, CallRequestSerializer, 
    RegionSerializer, DistrictSerializer, RoomSerializer, BoilerSerializer,
    ConstructionMissionSerializer, LightROISerializer, ResponsibleOrgSerializer,
    CallRequestTimelineSerializer, NotificationSerializer, ReportEntrySerializer,
    UtilityNodeSerializer, DeviceHealthSerializer, IoTDeviceSerializer
)
import json
import uuid
import requests

# Authentication Views
@csrf_exempt
@api_view(['POST'])
@permission_classes([])  # Allow unauthenticated users to log in
def login_view(request):
    """
    Handle user authentication for different roles
    """
    try:
        data = json.loads(request.body)
        login_param = data.get('login')
        password = data.get('password')
        
        # First, try to find the user as an organization
        try:
            org = Organization.objects.get(login=login_param)
            if org.password == password:  # In production, use Django's password hashing
                # Create a user session for the organization
                user, created = User.objects.get_or_create(username=org.login)
                login(request, user)
                
                # Create or get authentication token
                token, created = Token.objects.get_or_create(user=user)
                
                # Add organization to user for context
                request.session['organization_id'] = str(org.id)
                
                return Response({
                    'success': True,
                    'token': token.key,
                    'user': {
                        'id': str(org.id),
                        'name': org.name,
                        'role': 'ORGANIZATION',
                        'enabled_modules': ['DASHBOARD', 'WASTE', 'CLIMATE']  # Only WASTE and CLIMATE for Farg'ona
                    }
                })
        except Organization.DoesNotExist:
            pass
        try:
            truck = Truck.objects.get(login=login_param)
            if truck.password == password:  # In production, use proper password hashing
                # Create a user session for the truck/driver
                user, created = User.objects.get_or_create(username=truck.login)
                login(request, user)
                
                # Create or get authentication token
                token, created = Token.objects.get_or_create(user=user)
                
                # Add truck to user for context
                request.session['truck_id'] = str(truck.id)
                
                return Response({
                    'success': True,
                    'token': token.key,
                    'user': {
                        'id': str(truck.id),
                        'name': truck.driver_name,
                        'role': 'DRIVER',
                        'enabled_modules': ['WASTE']  # Drivers typically only have waste module
                    }
                })
        except Truck.DoesNotExist:
            pass
        
        # Try superadmin credentials
        if login_param == 'superadmin' and password == '123':
            user, created = User.objects.get_or_create(username='superadmin')
            login(request, user)
            
            # Create or get authentication token
            token, created = Token.objects.get_or_create(user=user)
            
            return Response({
                'success': True,
                'token': token.key,
                'user': {
                    'id': 'superadmin',
                    'name': 'Super Admin',
                    'role': 'SUPERADMIN',
                    'enabled_modules': ['DASHBOARD', 'WASTE', 'CLIMATE']  # Only WASTE and CLIMATE for Farg'ona
                }
            })
        
        # Try authenticating with Django's built-in User model (for admin users)
        django_user = authenticate(username=login_param, password=password)
        if django_user is not None:
            login(request, django_user)
            
            # Create or get authentication token for Django user
            token, created = Token.objects.get_or_create(user=django_user)
            
            # Determine role based on user permissions
            role = 'SUPERADMIN' if django_user.is_superuser else 'ADMIN'
            
            return Response({
                'success': True,
                'token': token.key,
                'user': {
                    'id': str(django_user.id),
                    'name': django_user.username,
                    'role': role,
                    'enabled_modules': ['DASHBOARD', 'WASTE', 'CLIMATE']  # Only WASTE and CLIMATE for Farg'ona
                }
            })
        
        return Response({
            'success': False,
            'message': 'Invalid credentials'
        }, status=status.HTTP_401_UNAUTHORIZED)
        
    except json.JSONDecodeError:
        return Response({
            'success': False,
            'message': 'Invalid JSON'
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([])  # Allow unauthenticated users to validate tokens
def validate_token(request):
    """
    Validate if the token is still valid
    """
    # Check if the user is authenticated (token is valid)
    if request.user.is_authenticated:
        # Return validation result with any stored session data
        response_data = {'valid': True}
        
        # Include organization ID if it exists in session
        org_id = request.session.get('organization_id')
        if org_id:
            response_data['organization_id'] = org_id
        
        return Response(response_data)
    else:
        return Response({'valid': False}, status=status.HTTP_401_UNAUTHORIZED)


# Class-based views for all models
class WasteBinListCreateView(APIView):
    def get(self, request):
        # Get the user's organization if available
        org_id = request.session.get('organization_id')
        
        if org_id:
            # For organization users, return only bins belonging to their organization
            bins = WasteBin.objects.filter(organization_id=org_id).select_related('location', 'organization')
        else:
            # For superadmin, return all bins
            bins = WasteBin.objects.all().select_related('location', 'organization')
        
        serializer = WasteBinSerializer(bins, many=True, context={'request': request})
        return Response(serializer.data)
    
    def post(self, request):
    # 1. 'data'ni har doim requestdan nusxalab olamiz (IF dan tashqarida)
        data = request.data.copy()
        
        # 2. Org_id bo'lsa, uni ma'lumotlarga qo'shamiz
        org_id = request.session.get('organization_id')
        if org_id:
            data['organization'] = org_id
            
        # Endi 'data' har qanday holatda ham mavjud
        serializer = WasteBinSerializer(data=data, context={'request': request})
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        # Xatolik bo'lsa nima xatoligini ko'rsatish
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Exempt CSRF for API views that use token authentication
@method_decorator(csrf_exempt, name='dispatch')
class WasteBinDetailView(APIView):
    def get(self, request, pk):
        bin = get_object_or_404(WasteBin, pk=pk)
        
        # Check if user has permission to access this bin
        org_id = request.session.get('organization_id')
        if org_id and str(bin.organization_id) != org_id:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = WasteBinSerializer(bin)
        return Response(serializer.data)
    
    def put(self, request, pk):
        bin = get_object_or_404(WasteBin, pk=pk)
        
        # Check if user has permission to access this bin
        org_id = request.session.get('organization_id')
        if org_id and str(bin.organization_id) != org_id:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = WasteBinSerializer(bin, data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def patch(self, request, pk):
        bin = get_object_or_404(WasteBin, pk=pk)
        
        # Check if user has permission to access this bin
        org_id = request.session.get('organization_id')
        if org_id and str(bin.organization_id) != org_id:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        # Use partial=True to allow partial updates
        serializer = WasteBinSerializer(bin, data=request.data, context={'request': request}, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        bin = get_object_or_404(WasteBin, pk=pk)
        
        # Check if user has permission to access this bin
        org_id = request.session.get('organization_id')
        if org_id and str(bin.organization_id) != org_id:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        bin.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@method_decorator(csrf_exempt, name='dispatch')
class WasteBinImageUpdateView(APIView):
    def patch(self, request, pk):
        """Update only the image_url, is_full, fill_level, image_source, and last_analysis fields for a waste bin"""
        bin = get_object_or_404(WasteBin, pk=pk)
        
        # Check if user has permission to access this bin
        org_id = request.session.get('organization_id')
        if org_id and str(bin.organization_id) != org_id:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        # Only allow updating specific fields
        allowed_fields = ['image_url', 'is_full', 'fill_level', 'image_source', 'last_analysis']
        update_data = {}
        
        for field in allowed_fields:
            if field in request.data:
                update_data[field] = request.data[field]
        
        # Set default image_source if not provided
        if 'image_source' not in update_data:
            update_data['image_source'] = 'BOT'
        
        # Set default last_analysis if not provided
        if 'last_analysis' not in update_data:
            update_data['last_analysis'] = 'Bot orqali yangilandi'
        
        # Update only the allowed fields
        for field, value in update_data.items():
            setattr(bin, field, value)
        
        bin.save()
        
        # Return the updated bin
        serializer = WasteBinSerializer(bin)
        return Response(serializer.data)


class TruckListCreateView(APIView):
    def get(self, request):
        # Get the user's organization if available
        org_id = request.session.get('organization_id')
        
        if org_id:
            # For organization users, return only trucks belonging to their organization
            trucks = Truck.objects.filter(organization_id=org_id)
        else:
            # For superadmin, return all trucks
            trucks = Truck.objects.all()
        
        serializer = TruckSerializer(trucks, many=True, context={'request': request})
        return Response(serializer.data)
    
    def post(self, request):
        # Add organization context based on user session
        data = request.data.copy()  # Always initialize data
        org_id = request.session.get('organization_id')
        if org_id:
            # Add organization to the request data
            data['organization'] = org_id
        
        serializer = TruckSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TruckDetailView(APIView):
    def get(self, request, pk):
        truck = get_object_or_404(Truck, pk=pk)
        
        # Check if user has permission to access this truck
        org_id = request.session.get('organization_id')
        if org_id and str(truck.organization_id) != org_id:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = TruckSerializer(truck)
        return Response(serializer.data)
    
    def put(self, request, pk):
        truck = get_object_or_404(Truck, pk=pk)
        
        # Check if user has permission to access this truck
        org_id = request.session.get('organization_id')
        if org_id and str(truck.organization_id) != org_id:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = TruckSerializer(truck, data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        truck = get_object_or_404(Truck, pk=pk)
        
        # Check if user has permission to access this truck
        org_id = request.session.get('organization_id')
        if org_id and str(truck.organization_id) != org_id:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        truck.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class RegionListCreateView(APIView):
    def get(self, request):
        regions = Region.objects.all()
        serializer = RegionSerializer(regions, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        serializer = RegionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RegionDetailView(APIView):
    def get(self, request, pk):
        region = get_object_or_404(Region, pk=pk)
        serializer = RegionSerializer(region)
        return Response(serializer.data)
    
    def put(self, request, pk):
        region = get_object_or_404(Region, pk=pk)
        serializer = RegionSerializer(region, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        region = get_object_or_404(Region, pk=pk)
        region.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class DistrictListCreateView(APIView):
    def get(self, request):
        districts = District.objects.all()
        serializer = DistrictSerializer(districts, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        serializer = DistrictSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DistrictDetailView(APIView):
    def get(self, request, pk):
        district = get_object_or_404(District, pk=pk)
        serializer = DistrictSerializer(district)
        return Response(serializer.data)
    
    def put(self, request, pk):
        district = get_object_or_404(District, pk=pk)
        serializer = DistrictSerializer(district, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        district = get_object_or_404(District, pk=pk)
        district.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class OrganizationListCreateView(APIView):
    def get(self, request):
        organizations = Organization.objects.all()
        serializer = OrganizationSerializer(organizations, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        serializer = OrganizationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class OrganizationDetailView(APIView):
    def get(self, request, pk):
        # Try to get by ID first, then by login as fallback
        try:
            # Check if pk is a valid UUID
            uuid_obj = uuid.UUID(pk)
            organization = get_object_or_404(Organization, pk=pk)
        except ValueError:
            # If not a UUID, try to get by login
            organization = get_object_or_404(Organization, login=pk)
        
        serializer = OrganizationSerializer(organization)
        return Response(serializer.data)
    
    def put(self, request, pk):
        # Try to get by ID first, then by login as fallback
        try:
            # Check if pk is a valid UUID
            uuid_obj = uuid.UUID(pk)
            organization = get_object_or_404(Organization, pk=pk)
        except ValueError:
            # If not a UUID, try to get by login
            try:
                organization = Organization.objects.get(login=pk)
            except Organization.DoesNotExist:
                # If the organization doesn't exist, create a new one with the given pk as login
                # Process the data to handle region/district references properly
                data = request.data.copy()
                data['login'] = pk  # Use the pk from URL as login
                
                # Handle region and district lookups if they're provided as names
                if 'regionId' in data and data['regionId']:
                    try:
                        # First try to get by UUID
                        region = Region.objects.get(id=data['regionId'])
                        data['region'] = region.pk
                    except Region.DoesNotExist:
                        try:
                            # If UUID lookup fails, try to get by name
                            region = Region.objects.get(name=data['regionId'])
                            data['region'] = region.pk
                        except Region.DoesNotExist:
                            return Response({'error': 'Region not found'}, status=status.HTTP_400_BAD_REQUEST)
                    # Remove the regionId field since we're using region now
                    del data['regionId']
                
                if 'districtId' in data and data['districtId']:
                    try:
                        # First try to get by UUID
                        district = District.objects.get(id=data['districtId'])
                        data['district'] = district.pk
                    except District.DoesNotExist:
                        try:
                            # If UUID lookup fails, try to get by name
                            district = District.objects.get(name=data['districtId'])
                            data['district'] = district.pk
                        except District.DoesNotExist:
                            return Response({'error': 'District not found'}, status=status.HTTP_400_BAD_REQUEST)
                    # Remove the districtId field since we're using district now
                    del data['districtId']
                
                # Create the organization with properly processed data
                serializer = OrganizationSerializer(data=data)
                if serializer.is_valid():
                    organization = serializer.save()
                    return Response(serializer.data, status=status.HTTP_201_CREATED)
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # For updating existing organization
        # Process the data to handle region/district references properly
        data = request.data.copy()
        
        # Handle region and district lookups if they're provided as names
        if 'regionId' in data and data['regionId']:
            try:
                # First try to get by UUID
                region = Region.objects.get(id=data['regionId'])
                data['region'] = region.pk
            except Region.DoesNotExist:
                try:
                    # If UUID lookup fails, try to get by name
                    region = Region.objects.get(name=data['regionId'])
                    data['region'] = region.pk
                except Region.DoesNotExist:
                    return Response({'error': 'Region not found'}, status=status.HTTP_400_BAD_REQUEST)
            # Remove the regionId field since we're using region now
            del data['regionId']
        
        if 'districtId' in data and data['districtId']:
            try:
                # First try to get by UUID
                district = District.objects.get(id=data['districtId'])
                data['district'] = district.pk
            except District.DoesNotExist:
                try:
                    # If UUID lookup fails, try to get by name
                    district = District.objects.get(name=data['districtId'])
                    data['district'] = district.pk
                except District.DoesNotExist:
                    return Response({'error': 'District not found'}, status=status.HTTP_400_BAD_REQUEST)
            # Remove the districtId field since we're using district now
            del data['districtId']
        
        serializer = OrganizationSerializer(organization, data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        # Try to get by ID first, then by login as fallback
        try:
            # Check if pk is a valid UUID
            uuid_obj = uuid.UUID(pk)
            organization = get_object_or_404(Organization, pk=pk)
        except ValueError:
            # If not a UUID, try to get by login
            organization = get_object_or_404(Organization, login=pk)
        
        organization.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MoistureSensorListCreateView(APIView):
    def get(self, request):
        sensors = MoistureSensor.objects.all()
        serializer = MoistureSensorSerializer(sensors, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        serializer = MoistureSensorSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MoistureSensorDetailView(APIView):
    def get(self, request, pk):
        sensor = get_object_or_404(MoistureSensor, pk=pk)
        serializer = MoistureSensorSerializer(sensor)
        return Response(serializer.data)
    
    def put(self, request, pk):
        sensor = get_object_or_404(MoistureSensor, pk=pk)
        serializer = MoistureSensorSerializer(sensor, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        sensor = get_object_or_404(MoistureSensor, pk=pk)
        sensor.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class RoomListCreateView(APIView):
    def get(self, request):
        rooms = Room.objects.all()
        serializer = RoomSerializer(rooms, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        serializer = RoomSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RoomDetailView(APIView):
    def get(self, request, pk):
        room = get_object_or_404(Room, pk=pk)
        serializer = RoomSerializer(room)
        return Response(serializer.data)
    
    def put(self, request, pk):
        room = get_object_or_404(Room, pk=pk)
        serializer = RoomSerializer(room, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        room = get_object_or_404(Room, pk=pk)
        room.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class BoilerListCreateView(APIView):
    def get(self, request):
        boilers = Boiler.objects.all()
        serializer = BoilerSerializer(boilers, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        serializer = BoilerSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BoilerDetailView(APIView):
    def get(self, request, pk):
        boiler = get_object_or_404(Boiler, pk=pk)
        serializer = BoilerSerializer(boiler)
        return Response(serializer.data)
    
    def put(self, request, pk):
        boiler = get_object_or_404(Boiler, pk=pk)
        serializer = BoilerSerializer(boiler, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        boiler = get_object_or_404(Boiler, pk=pk)
        boiler.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class FacilityListCreateView(APIView):
    def get(self, request):
        from django.db.models import Prefetch
        # Prefetch boilers and their connected rooms for efficient querying
        boilers_prefetch = Prefetch('boilers', Boiler.objects.prefetch_related('connected_rooms', 'device_health'))
        facilities = Facility.objects.prefetch_related(boilers_prefetch).all()
        serializer = FacilitySerializer(facilities, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        serializer = FacilitySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class FacilityDetailView(APIView):
    def get(self, request, pk):
        from django.db.models import Prefetch
        # Prefetch boilers and their connected rooms for efficient querying
        boilers_prefetch = Prefetch('boilers', Boiler.objects.prefetch_related('connected_rooms', 'device_health'))
        facility = get_object_or_404(Facility.objects.prefetch_related(boilers_prefetch), pk=pk)
        serializer = FacilitySerializer(facility)
        return Response(serializer.data)
    
    def put(self, request, pk):
        facility = get_object_or_404(Facility, pk=pk)
        serializer = FacilitySerializer(facility, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        facility = get_object_or_404(Facility, pk=pk)
        facility.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AirSensorListCreateView(APIView):
    def get(self, request):
        # Get the user's organization if available
        org_id = request.session.get('organization_id')
        
        if org_id:
            # For organization users, return only sensors belonging to their organization
            sensors = AirSensor.objects.filter(organization_id=org_id)
        else:
            # For superadmin, return all sensors
            sensors = AirSensor.objects.all()
        
        serializer = AirSensorSerializer(sensors, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        # Add organization context based on user session
        data = request.data.copy()  # Always initialize data
        org_id = request.session.get('organization_id')
        if org_id:
            # Add organization to the request data
            data['organization'] = org_id
        
        serializer = AirSensorSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AirSensorDetailView(APIView):
    def get(self, request, pk):
        sensor = get_object_or_404(AirSensor, pk=pk)
        serializer = AirSensorSerializer(sensor)
        return Response(serializer.data)
    
    def put(self, request, pk):
        sensor = get_object_or_404(AirSensor, pk=pk)
        serializer = AirSensorSerializer(sensor, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        sensor = get_object_or_404(AirSensor, pk=pk)
        sensor.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class SOSColumnListCreateView(APIView):
    def get(self, request):
        # Get the user's organization if available
        org_id = request.session.get('organization_id')
        
        if org_id:
            # For organization users, return only columns belonging to their organization
            columns = SOSColumn.objects.filter(organization_id=org_id)
        else:
            # For superadmin, return all columns
            columns = SOSColumn.objects.all()
        
        serializer = SOSColumnSerializer(columns, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        # Add organization context based on user session
        data = request.data.copy()  # Always initialize data
        org_id = request.session.get('organization_id')
        if org_id:
            # Add organization to the request data
            data['organization'] = org_id
        
        serializer = SOSColumnSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SOSColumnDetailView(APIView):
    def get(self, request, pk):
        column = get_object_or_404(SOSColumn, pk=pk)
        serializer = SOSColumnSerializer(column)
        return Response(serializer.data)
    
    def put(self, request, pk):
        column = get_object_or_404(SOSColumn, pk=pk)
        serializer = SOSColumnSerializer(column, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        column = get_object_or_404(SOSColumn, pk=pk)
        column.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class EcoViolationListCreateView(APIView):
    def get(self, request):
        # Get the user's organization if available
        org_id = request.session.get('organization_id')
        
        if org_id:
            # For organization users, return only violations belonging to their organization
            violations = EcoViolation.objects.filter(organization_id=org_id)
        else:
            # For superadmin, return all violations
            violations = EcoViolation.objects.all()
        
        serializer = EcoViolationSerializer(violations, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        # Add organization context based on user session
        data = request.data.copy()  # Always initialize data
        org_id = request.session.get('organization_id')
        if org_id:
            # Add organization to the request data
            data['organization'] = org_id
        
        serializer = EcoViolationSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EcoViolationDetailView(APIView):
    def get(self, request, pk):
        violation = get_object_or_404(EcoViolation, pk=pk)
        serializer = EcoViolationSerializer(violation)
        return Response(serializer.data)
    
    def put(self, request, pk):
        violation = get_object_or_404(EcoViolation, pk=pk)
        serializer = EcoViolationSerializer(violation, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        violation = get_object_or_404(EcoViolation, pk=pk)
        violation.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ConstructionSiteListCreateView(APIView):
    def get(self, request):
        # Get the user's organization if available
        org_id = request.session.get('organization_id')
        
        if org_id:
            # For organization users, return only sites belonging to their organization
            sites = ConstructionSite.objects.filter(organization_id=org_id)
        else:
            # For superadmin, return all sites
            sites = ConstructionSite.objects.all()
        
        serializer = ConstructionSiteSerializer(sites, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        # Add organization context based on user session
        data = request.data.copy()  # Always initialize data
        org_id = request.session.get('organization_id')
        if org_id:
            # Add organization to the request data
            data['organization'] = org_id
        
        serializer = ConstructionSiteSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ConstructionSiteDetailView(APIView):
    def get(self, request, pk):
        site = get_object_or_404(ConstructionSite, pk=pk)
        serializer = ConstructionSiteSerializer(site)
        return Response(serializer.data)
    
    def put(self, request, pk):
        site = get_object_or_404(ConstructionSite, pk=pk)
        serializer = ConstructionSiteSerializer(site, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        site = get_object_or_404(ConstructionSite, pk=pk)
        site.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class LightPoleListCreateView(APIView):
    def get(self, request):
        # Get the user's organization if available
        org_id = request.session.get('organization_id')
        
        if org_id:
            # For organization users, return only poles belonging to their organization
            poles = LightPole.objects.filter(organization_id=org_id)
        else:
            # For superadmin, return all poles
            poles = LightPole.objects.all()
        
        serializer = LightPoleSerializer(poles, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        # Add organization context based on user session
        data = request.data.copy()  # Always initialize data
        org_id = request.session.get('organization_id')
        if org_id:
            # Add organization to the request data
            data['organization'] = org_id
        
        serializer = LightPoleSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LightPoleDetailView(APIView):
    def get(self, request, pk):
        pole = get_object_or_404(LightPole, pk=pk)
        serializer = LightPoleSerializer(pole)
        return Response(serializer.data)
    
    def put(self, request, pk):
        pole = get_object_or_404(LightPole, pk=pk)
        serializer = LightPoleSerializer(pole, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        pole = get_object_or_404(LightPole, pk=pk)
        pole.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class BusListCreateView(APIView):
    def get(self, request):
        # Get the user's organization if available
        org_id = request.session.get('organization_id')
        
        if org_id:
            # For organization users, return only buses belonging to their organization
            buses = Bus.objects.filter(organization_id=org_id)
        else:
            # For superadmin, return all buses
            buses = Bus.objects.all()
        
        serializer = BusSerializer(buses, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        # Add organization context based on user session
        data = request.data.copy()  # Always initialize data
        org_id = request.session.get('organization_id')
        if org_id:
            # Add organization to the request data
            data['organization'] = org_id
        
        serializer = BusSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BusDetailView(APIView):
    def get(self, request, pk):
        bus = get_object_or_404(Bus, pk=pk)
        serializer = BusSerializer(bus)
        return Response(serializer.data)
    
    def put(self, request, pk):
        bus = get_object_or_404(Bus, pk=pk)
        serializer = BusSerializer(bus, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        bus = get_object_or_404(Bus, pk=pk)
        bus.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CallRequestListCreateView(APIView):
    def get(self, request):
        requests = CallRequest.objects.all()
        serializer = CallRequestSerializer(requests, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        serializer = CallRequestSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CallRequestDetailView(APIView):
    def get(self, request, pk):
        request_obj = get_object_or_404(CallRequest, pk=pk)
        serializer = CallRequestSerializer(request_obj)
        return Response(serializer.data)
    
    def put(self, request, pk):
        request_obj = get_object_or_404(CallRequest, pk=pk)
        serializer = CallRequestSerializer(request_obj, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        request_obj = get_object_or_404(CallRequest, pk=pk)
        request_obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# Add other class-based views as needed...

# Additional functional views
@api_view(['GET'])
def get_waste_bins_by_hudud(request, toza_hudud):
    """
    Get waste bins by toza hudud
    """
    bins = WasteBin.objects.filter(toza_hudud=toza_hudud)
    serializer = WasteBinSerializer(bins, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def get_trucks_by_hudud(request, toza_hudud):
    """
    Get trucks by toza hudud
    """
    trucks = Truck.objects.filter(toza_hudud=toza_hudud)
    serializer = TruckSerializer(trucks, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def get_region_districts(request, region_id):
    """
    Get districts for a specific region
    """
    districts = District.objects.filter(region_id=region_id)
    serializer = DistrictSerializer(districts, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def get_facilities_by_type(request, facility_type):
    """
    Get facilities by type
    """
    facilities = Facility.objects.filter(type=facility_type)
    serializer = FacilitySerializer(facilities, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def get_air_sensors_by_status(request, status):
    """
    Get air sensors by status
    """
    sensors = AirSensor.objects.filter(status=status)
    serializer = AirSensorSerializer(sensors, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def get_sos_columns_by_status(request, status):
    """
    Get SOS columns by status
    """
    columns = SOSColumn.objects.filter(status=status)
    serializer = SOSColumnSerializer(columns, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def get_eco_violations_by_date_range(request):
    """
    Get eco violations by date range
    """
    from django.utils.dateparse import parse_date
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    violations = EcoViolation.objects.all()
    if start_date:
        start_date = parse_date(start_date)
        violations = violations.filter(timestamp__gte=start_date)
    if end_date:
        end_date = parse_date(end_date)
        violations = violations.filter(timestamp__lte=end_date)
    
    serializer = EcoViolationSerializer(violations, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def get_construction_sites_by_status(request, status):
    """
    Get construction sites by status
    """
    sites = ConstructionSite.objects.filter(status=status)
    serializer = ConstructionSiteSerializer(sites, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def get_buses_by_status(request, status):
    """
    Get buses by status
    """
    buses = Bus.objects.filter(status=status)
    serializer = BusSerializer(buses, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def get_call_requests_by_status(request, status):
    """
    Get call requests by status
    """
    requests = CallRequest.objects.filter(status=status)
    serializer = CallRequestSerializer(requests, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def get_notifications_unread(request):
    """
    Get unread notifications
    """
    notifications = Notification.objects.filter(read=False)
    serializer = NotificationSerializer(notifications, many=True)
    return Response(serializer.data)


@api_view(['POST'])
def mark_notification_read(request, notification_id):
    """
    Mark notification as read
    """
    notification = get_object_or_404(Notification, pk=notification_id)
    notification.read = True
    notification.save()
    serializer = NotificationSerializer(notification)
    return Response(serializer.data)


@api_view(['GET'])
def get_utility_nodes_by_type(request, utility_type):
    """
    Get utility nodes by type
    """
    nodes = UtilityNode.objects.filter(type=utility_type)
    serializer = UtilityNodeSerializer(nodes, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def get_utility_nodes_by_status(request, status):
    """
    Get utility nodes by status
    """
    nodes = UtilityNode.objects.filter(status=status)
    serializer = UtilityNodeSerializer(nodes, many=True)
    return Response(serializer.data)


# Search functionality
@api_view(['GET'])
def search_entities(request):
    """
    Search across all entities
    """
    query = request.GET.get('q', '')
    entity_type = request.GET.get('type', '')
    
    results = []
    
    if entity_type == 'organization' or not entity_type:
        orgs = Organization.objects.filter(name__icontains=query)
        results.extend(OrganizationSerializer(orgs, many=True).data)
    
    if entity_type == 'waste-bin' or not entity_type:
        bins = WasteBin.objects.filter(address__icontains=query)
        results.extend(WasteBinSerializer(bins, many=True).data)
    
    if entity_type == 'truck' or not entity_type:
        trucks = Truck.objects.filter(driver_name__icontains=query)
        results.extend(TruckSerializer(trucks, many=True).data)
    
    return Response({
        'query': query,
        'type': entity_type,
        'results': results
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trigger_waste_bin_analysis(request):
    """
    API endpoint to trigger automated waste bin analysis
    """
    from smartcity_app.management.commands.analyze_waste_bins import Command
    import io
    from contextlib import redirect_stdout

    # Create a string buffer to capture output
    f = io.StringIO()
    
    # Run the analysis command
    try:
        command = Command()
        command.analyze_bins()
        return Response({
            'success': True,
            'message': 'Waste bin analysis completed successfully'
        })
    except Exception as e:
        return Response({
            'success': False,
            'message': f'Error during analysis: {str(e)}'
        }, status=500)


# Custom views for specific functionality
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_stats(request):
    """
    Get dashboard statistics
    """
    # Get the user's organization if available
    org_id = request.session.get('organization_id')
    
    if org_id:
        # For organization users, count only their entities
        total_bins = WasteBin.objects.filter(organization_id=org_id).count()
        active_bins = WasteBin.objects.filter(organization_id=org_id, is_full=False).count()
        total_trucks = Truck.objects.filter(organization_id=org_id).count()
        busy_trucks = Truck.objects.filter(organization_id=org_id, status='BUSY').count()
    else:
        # For superadmin, count all entities
        total_bins = WasteBin.objects.count()
        active_bins = WasteBin.objects.filter(is_full=False).count()
        total_trucks = Truck.objects.count()
        busy_trucks = Truck.objects.filter(status='BUSY').count()
    
    return Response({
        'total_bins': total_bins,
        'active_bins': active_bins,
        'total_trucks': total_trucks,
        'busy_trucks': busy_trucks,
        'fill_rate': (total_bins - active_bins) / total_bins * 100 if total_bins > 0 else 0
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_organizations(request):
    """
    Get organizations for the logged-in user
    """
    org_id = request.session.get('organization_id')
    
    if org_id:
        # Return only the user's organization
        org = Organization.objects.get(id=org_id)
        serializer = OrganizationSerializer(org)
        return Response([serializer.data])
    else:
        # For superadmin, return all organizations
        organizations = Organization.objects.all()
        serializer = OrganizationSerializer(organizations, many=True)
        return Response(serializer.data)


class ConstructionMissionListCreateView(APIView):
    def get(self, request):
        missions = ConstructionMission.objects.all()
        serializer = ConstructionMissionSerializer(missions, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        serializer = ConstructionMissionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ConstructionMissionDetailView(APIView):
    def get(self, request, pk):
        mission = get_object_or_404(ConstructionMission, pk=pk)
        serializer = ConstructionMissionSerializer(mission)
        return Response(serializer.data)
    
    def put(self, request, pk):
        mission = get_object_or_404(ConstructionMission, pk=pk)
        serializer = ConstructionMissionSerializer(mission, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        mission = get_object_or_404(ConstructionMission, pk=pk)
        mission.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class LightROIListCreateView(APIView):
    def get(self, request):
        rois = LightROI.objects.all()
        serializer = LightROISerializer(rois, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        serializer = LightROISerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LightROIDetailView(APIView):
    def get(self, request, pk):
        roi = get_object_or_404(LightROI, pk=pk)
        serializer = LightROISerializer(roi)
        return Response(serializer.data)
    
    def put(self, request, pk):
        roi = get_object_or_404(LightROI, pk=pk)
        serializer = LightROISerializer(roi, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        roi = get_object_or_404(LightROI, pk=pk)
        roi.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ResponsibleOrgListCreateView(APIView):
    def get(self, request):
        orgs = ResponsibleOrg.objects.all()
        serializer = ResponsibleOrgSerializer(orgs, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        serializer = ResponsibleOrgSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ResponsibleOrgDetailView(APIView):
    def get(self, request, pk):
        org = get_object_or_404(ResponsibleOrg, pk=pk)
        serializer = ResponsibleOrgSerializer(org)
        return Response(serializer.data)
    
    def put(self, request, pk):
        org = get_object_or_404(ResponsibleOrg, pk=pk)
        serializer = ResponsibleOrgSerializer(org, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        org = get_object_or_404(ResponsibleOrg, pk=pk)
        org.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CallRequestTimelineListCreateView(APIView):
    def get(self, request):
        timelines = CallRequestTimeline.objects.all()
        serializer = CallRequestTimelineSerializer(timelines, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        serializer = CallRequestTimelineSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CallRequestTimelineDetailView(APIView):
    def get(self, request, pk):
        timeline = get_object_or_404(CallRequestTimeline, pk=pk)
        serializer = CallRequestTimelineSerializer(timeline)
        return Response(serializer.data)
    
    def put(self, request, pk):
        timeline = get_object_or_404(CallRequestTimeline, pk=pk)
        serializer = CallRequestTimelineSerializer(timeline, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        timeline = get_object_or_404(CallRequestTimeline, pk=pk)
        timeline.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class NotificationListCreateView(APIView):
    def get(self, request):
        notifications = Notification.objects.all()
        serializer = NotificationSerializer(notifications, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        serializer = NotificationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class NotificationDetailView(APIView):
    def get(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk)
        serializer = NotificationSerializer(notification)
        return Response(serializer.data)
    
    def put(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk)
        serializer = NotificationSerializer(notification, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk)
        notification.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ReportEntryListCreateView(APIView):
    def get(self, request):
        entries = ReportEntry.objects.all()
        serializer = ReportEntrySerializer(entries, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        serializer = ReportEntrySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ReportEntryDetailView(APIView):
    def get(self, request, pk):
        entry = get_object_or_404(ReportEntry, pk=pk)
        serializer = ReportEntrySerializer(entry)
        return Response(serializer.data)
    
    def put(self, request, pk):
        entry = get_object_or_404(ReportEntry, pk=pk)
        serializer = ReportEntrySerializer(entry, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        entry = get_object_or_404(ReportEntry, pk=pk)
        entry.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class UtilityNodeListCreateView(APIView):
    def get(self, request):
        # Get the user's organization if available
        org_id = request.session.get('organization_id')
        
        if org_id:
            # For organization users, return only nodes belonging to their organization
            nodes = UtilityNode.objects.filter(organization_id=org_id)
        else:
            # For superadmin, return all nodes
            nodes = UtilityNode.objects.all()
        
        serializer = UtilityNodeSerializer(nodes, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        # Add organization context based on user session
        data = request.data.copy()  # Always initialize data
        org_id = request.session.get('organization_id')
        if org_id:
            # Add organization to the request data
            data['organization'] = org_id
        
        serializer = UtilityNodeSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UtilityNodeDetailView(APIView):
    def get(self, request, pk):
        node = get_object_or_404(UtilityNode, pk=pk)
        serializer = UtilityNodeSerializer(node)
        return Response(serializer.data)
    
    def put(self, request, pk):
        node = get_object_or_404(UtilityNode, pk=pk)
        serializer = UtilityNodeSerializer(node, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        node = get_object_or_404(UtilityNode, pk=pk)
        node.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_bin_with_camera_image(request, pk):
    """
    API endpoint to update waste bin with camera image and AI analysis
    """
    bin = get_object_or_404(WasteBin, pk=pk)
    
    # Check if user has permission to access this bin
    org_id = request.session.get('organization_id')
    if org_id and str(bin.organization_id) != org_id:
        return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
    
    # Get image data from request
    image_data = request.data.get('image_url', None)
    image_source = request.data.get('image_source', 'CCTV')
    last_analysis = request.data.get('last_analysis', f'Kamera tahlili {timezone.now().strftime("%Y-%m-%d %H:%M:%S")}')
    
    if image_data:
        # Update the bin with the new image and information
        bin.image_url = image_data
        bin.image_source = image_source
        bin.last_analysis = last_analysis
        
        # For camera images, we'll update the fill level based on the image if possible
        # In a real system, this would call an AI service to analyze the image
        # For now, we'll keep the existing fill level and is_full status
        # But we can enhance this to use AI analysis
        try:
            # Attempt to download and analyze the image with AI
            import requests as req
            import base64
            from io import BytesIO
            
            # Download image from URL
            response = req.get(image_data)
            if response.status_code == 200:
                # Convert image to base64 for AI analysis
                image_bytes = BytesIO(response.content).read()
                image_base64 = base64.b64encode(image_bytes).decode('utf-8')
                
                # Call backend AI service to analyze the image
                ai_result = analyze_bin_image_backend(image_base64)
                
                # Update bin status based on AI analysis
                bin.fill_level = ai_result['fillLevel']
                bin.is_full = ai_result['isFull']
                
                # Update last analysis with AI results
                bin.last_analysis = f"AI tahlili: {ai_result['notes']}, IsFull: {ai_result['isFull']}, FillLevel: {ai_result['fillLevel']}%, Conf: {ai_result['confidence']}%"
                
        except Exception as e:
            # If AI analysis fails, log the error but continue with existing values
            print(f"AI analysis failed: {e}")
            # Optionally, you could use a default analysis or keep the existing values
            
        bin.save()
    
    serializer = WasteBinSerializer(bin)
    return Response(serializer.data)

def analyze_bin_image_backend(base64_image):
    """
    Backend function to analyze waste bin image using Google AI API
    """
    import os
    import requests
    import json
    
    # Get API key from environment or use default
    api_key = os.getenv('GEMINI_API_KEY', 'YOUR_API_KEY_HERE')
    if api_key == 'YOUR_API_KEY_HERE':
        # If no API key is set, return a basic response
        return {
            'isFull': True,
            'fillLevel': 90,
            'confidence': 70,
            'notes': 'API kaliti ornatilmagan, oddiy tahlil amalga oshirildi'
        }
    
    # Prepare the request to Google AI
    ai_url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-pro-vision:generateContent?key={api_key}'
    
    # Create detailed prompt for AI with enhanced analysis
    prompt = '''Siz tajriboli atrof-muhitni kuzatuv tizimi ekspertisiz. Rasmni tahlil qiling va quyidagilarni aniqlang:
    1. Rasmda chiqindi konteyneri bormi? Javob: HA yoki YO'Q.
    2. Agar HA bo'lsa, konteyner to'la bo'limi? Javob: HA yoki YO'Q.
    3. Agar HA bo'lsa, to'ldirish darajasini % (0-100) ko'rsating.
    4. Rasm sifatini baholang (yaxshi, o'rtacha, yomon).

    Javobni quyidagi JSON formatda bering:
    {
        "isFull": boolean,
        "fillLevel": number (0 dan 100 gacha foiz),
        "confidence": number (O'z qaroringga ishonch darajasi 0-100),
        "notes": string (Qisqa izoh o'zbek tilida: Masalan "Konteyner toshib ketgan" yoki "Yarmi bo'sh")
    }
    '''
    
    ai_headers = {
        'Content-Type': 'application/json',
    }
    
    ai_payload = {
        'contents': [{
            'parts': [
                {'text': prompt},
                {
                    'inlineData': {
                        'mimeType': 'image/jpeg',
                        'data': base64_image
                    }
                }
            ]
        }]
    }
    
    try:
        response = requests.post(ai_url, headers=ai_headers, data=json.dumps(ai_payload))
        
        if response.status_code == 200:
            result = response.json()
            
            # Extract the AI response
            if 'candidates' in result and len(result['candidates']) > 0:
                candidate = result['candidates'][0]
                if 'content' in candidate and 'parts' in candidate['content']:
                    content_parts = candidate['content']['parts']
                    for part in content_parts:
                        if 'text' in part:
                            # Try to parse the JSON response
                            text_content = part['text'].strip()
                            
                            # Remove any markdown code block markers
                            if text_content.startswith('```'):
                                # Find the JSON part in the response
                                import re
                                json_match = re.search(r'\{.*\}', text_content, re.DOTALL)
                                if json_match:
                                    text_content = json_match.group()
                                else:
                                    # If no JSON found, return default values
                                    return {
                                        'isFull': True,
                                        'fillLevel': 80,
                                        'confidence': 60,
                                        'notes': 'Tahlil natijasini tahlil qilishda xatolik yuz berdi'
                                    }
                            
                            try:
                                ai_result = json.loads(text_content)
                                return {
                                    'isFull': ai_result.get('isFull', False),
                                    'fillLevel': ai_result.get('fillLevel', 50),
                                    'confidence': ai_result.get('confidence', 50),
                                    'notes': ai_result.get('notes', 'AI tahlili tugadi')
                                }
                            except json.JSONDecodeError:
                                # If JSON parsing fails, return default values
                                return {
                                    'isFull': True,
                                    'fillLevel': 75,
                                    'confidence': 50,
                                    'notes': 'JSON javobini tahlil qilishda xatolik yuz berdi'
                                }
            
            # If no candidates found, return default values
            return {
                'isFull': True,
                'fillLevel': 70,
                'confidence': 40,
                'notes': 'AI javob topilmadi'
            }
        else:
            # If API call fails, return default values
            print(f"AI API request failed: {response.status_code}, {response.text}")
            return {
                'isFull': True,
                'fillLevel': 60,
                'confidence': 30,
                'notes': f'AI tahlilida xatolik: {response.status_code}'
            }
    except Exception as e:
        # If any error occurs, return default values
        print(f"AI analysis error: {e}")
        return {
            'isFull': True,
            'fillLevel': 50,
            'confidence': 25,
            'notes': f'AI tahlilida xatolik yuz berdi: {str(e)}'
        }


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_iot_sensor_data(request):
    """
    API endpoint to update IoT sensor data (temperature and humidity) from ESP devices
    """
    try:
        device_id = request.data.get('device_id')
        temperature = request.data.get('temperature')
        humidity = request.data.get('humidity')
        sleep_seconds = request.data.get('sleep_seconds', 2000)
        timestamp = request.data.get('timestamp', int(timezone.now().timestamp()))
        
        if not device_id:
            return Response({'error': 'device_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Find the IoT device by device_id
        try:
            iot_device = IoTDevice.objects.get(device_id=device_id)
        except IoTDevice.DoesNotExist:
            return Response({'error': f'Device with ID {device_id} not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Update device's last seen time and sensor readings
        iot_device.last_seen = timezone.now()
        iot_device.current_temperature = temperature
        iot_device.current_humidity = humidity
        iot_device.last_sensor_update = timezone.now()
        iot_device.save()
        
        # Update associated room or boiler if available
        if iot_device.room:
            iot_device.room.temperature = temperature or iot_device.room.temperature
            if humidity is not None:
                iot_device.room.humidity = humidity
            iot_device.room.last_updated = timezone.now()
            iot_device.room.save()
        elif iot_device.boiler:
            iot_device.boiler.temperature = temperature or iot_device.boiler.temperature
            if humidity is not None:
                iot_device.boiler.humidity = humidity
            iot_device.boiler.last_updated = timezone.now()
            iot_device.boiler.save()
        
        return Response({
            'message': 'Sensor data updated successfully',
            'device_id': device_id,
            'temperature': temperature,
            'humidity': humidity,
            'timestamp': timestamp
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
@api_view(['POST', 'OPTIONS'])
@permission_classes([])  # Temporarily allow unauthenticated for diagnostic tests
def link_iot_device_to_boiler(request):
    """
    API endpoint to link an IoT device to a boiler
    """
    try:
        # Diagnostic logging
        import logging
        logger = logging.getLogger(__name__)
        logger.debug('link_iot_device_to_boiler called with method=%s, user=%s', request.method, str(request.user))
        try:
            headers = {k: v for k, v in request.META.items() if k.startswith('HTTP_')}
        except Exception:
            headers = {}
        logger.debug('Request headers (HTTP_*): %s', headers)
        logger.debug('Request data: %s', request.data)

        device_id = request.data.get('device_id')
        boiler_id = request.data.get('boiler_id')
        
        if not device_id or not boiler_id:
            return Response({'error': 'device_id and boiler_id are required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Find the IoT device and boiler
        try:
            iot_device = IoTDevice.objects.get(device_id=device_id)
        except IoTDevice.DoesNotExist:
            return Response({'error': f'Device with ID {device_id} not found'}, status=status.HTTP_404_NOT_FOUND)
        
        try:
            boiler = Boiler.objects.get(id=boiler_id)
        except Boiler.DoesNotExist:
            return Response({'error': f'Boiler with ID {boiler_id} not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Link the IoT device to the boiler
        iot_device.boiler = boiler
        iot_device.room = None  # Clear room if previously linked
        iot_device.save()
        
        # Update boiler with current device readings if available
        if iot_device.current_temperature is not None:
            boiler.temperature = iot_device.current_temperature
        if iot_device.current_humidity is not None:
            boiler.humidity = iot_device.current_humidity
        boiler.last_updated = timezone.now()
        boiler.save()

        logger.debug('IoT device %s linked to boiler %s successfully', device_id, boiler_id)
        return Response({
            'message': 'IoT device linked to boiler successfully',
            'device_id': device_id,
            'boiler_id': boiler_id
        })
        
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception('Error in link_iot_device_to_boiler')
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Debug endpoint to verify POST requests reach the server
@csrf_exempt
@api_view(['POST', 'OPTIONS'])
@permission_classes([])
def iot_link_test(request):
    """Simple debug endpoint: echoes back received JSON and headers."""
    import logging
    logger = logging.getLogger(__name__)
    logger.debug('iot_link_test method=%s headers=%s data=%s', request.method, {k:v for k,v in request.META.items() if k.startswith('HTTP_')}, request.data)
    return Response({'ok': True, 'method': request.method, 'data': request.data})


from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
@api_view(['POST', 'OPTIONS'])
@permission_classes([])  # Temporarily allow unauthenticated for diagnostic tests
def link_iot_device_to_room(request):
    """
    API endpoint to link an IoT device to a room
    """
    try:
        # Diagnostic logging
        import logging
        logger = logging.getLogger(__name__)
        logger.debug('link_iot_device_to_room called with method=%s, user=%s', request.method, str(request.user))
        try:
            # Only log a subset of headers to avoid sensitive info
            headers = {k: v for k, v in request.META.items() if k.startswith('HTTP_')}
        except Exception:
            headers = {}
        logger.debug('Request headers (HTTP_*): %s', headers)
        logger.debug('Request data: %s', request.data)

        device_id = request.data.get('device_id')
        room_id = request.data.get('room_id')
        
        if not device_id or not room_id:
            return Response({'error': 'device_id and room_id are required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Find the IoT device and room
        try:
            iot_device = IoTDevice.objects.get(device_id=device_id)
        except IoTDevice.DoesNotExist:
            return Response({'error': f'Device with ID {device_id} not found'}, status=status.HTTP_404_NOT_FOUND)
        
        try:
            room = Room.objects.get(id=room_id)
        except Room.DoesNotExist:
            return Response({'error': f'Room with ID {room_id} not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Link the IoT device to the room
        iot_device.room = room
        iot_device.boiler = None  # Clear boiler if previously linked
        iot_device.save()
        
        # Update room with current device readings if available
        if iot_device.current_temperature is not None:
            room.temperature = iot_device.current_temperature
        if iot_device.current_humidity is not None:
            room.humidity = iot_device.current_humidity
        room.last_updated = timezone.now()
        room.save()
        
        logger.debug('IoT device %s linked to room %s successfully', device_id, room_id)
        return Response({
            'message': 'IoT device linked to room successfully',
            'device_id': device_id,
            'room_id': room_id
        })
        
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception('Error in link_iot_device_to_room')
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# IoT Device Views
@method_decorator(csrf_exempt, name='dispatch')
class IoTDeviceListCreateView(APIView):
    def get(self, request):
        # Get the user's organization if available
        org_id = request.session.get('organization_id')
        
        if org_id:
            # For organization users, return only devices belonging to their organization
            # Since IoT devices are linked to rooms or boilers which are linked to facilities
            # we'll return all IoT devices but with optimized queries
            devices = IoTDevice.objects.select_related('location', 'room', 'boiler').all()
        else:
            # For superadmin, return all devices
            devices = IoTDevice.objects.select_related('location', 'room', 'boiler').all()
        
        serializer = IoTDeviceSerializer(devices, many=True, context={'request': request})
        return Response(serializer.data)
    
    def post(self, request):
        # Add organization context based on user session if needed
        # For IoT devices, we don't directly associate with organizations
        # but rather through rooms/boilers
        data = request.data.copy()  # Always initialize data
        
        serializer = IoTDeviceSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class IoTDeviceDetailView(APIView):
    def get(self, request, pk):
        device = get_object_or_404(IoTDevice.objects.select_related('location', 'room', 'boiler'), pk=pk)
        serializer = IoTDeviceSerializer(device, context={'request': request})
        return Response(serializer.data)
    
    def put(self, request, pk):
        device = get_object_or_404(IoTDevice, pk=pk)
        serializer = IoTDeviceSerializer(device, data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def patch(self, request, pk):
        device = get_object_or_404(IoTDevice, pk=pk)
        serializer = IoTDeviceSerializer(device, data=request.data, context={'request': request}, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        device = get_object_or_404(IoTDevice, pk=pk)
        device.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


