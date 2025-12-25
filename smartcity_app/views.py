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
    DeviceHealth
)
from .serializers import (
    OrganizationSerializer, WasteBinSerializer, TruckSerializer, 
    MoistureSensorSerializer, FacilitySerializer, AirSensorSerializer, 
    SOSColumnSerializer, EcoViolationSerializer, ConstructionSiteSerializer, 
    LightPoleSerializer, BusSerializer, CallRequestSerializer, 
    RegionSerializer, DistrictSerializer, RoomSerializer, BoilerSerializer,
    ConstructionMissionSerializer, LightROISerializer, ResponsibleOrgSerializer,
    CallRequestTimelineSerializer, NotificationSerializer, ReportEntrySerializer,
    UtilityNodeSerializer, DeviceHealthSerializer
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
                        'enabled_modules': org.enabled_modules
                    },
                    'organization': OrganizationSerializer(org).data
                })
        except Organization.DoesNotExist:
            pass
        
        # Try to find as a truck/driver user
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
                    'enabled_modules': ['DASHBOARD', 'WASTE', 'CLIMATE', 'MOISTURE', 'SECURITY', 
                                      'ECO_CONTROL', 'CONSTRUCTION', 'LIGHT_INSPECTOR', 'AIR', 
                                      'TRANSPORT', 'CALL_CENTER', 'ANALYTICS']
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
                    'enabled_modules': ['DASHBOARD', 'WASTE', 'CLIMATE', 'MOISTURE', 'SECURITY', 
                                      'ECO_CONTROL', 'CONSTRUCTION', 'LIGHT_INSPECTOR', 'AIR', 
                                      'TRANSPORT', 'CALL_CENTER', 'ANALYTICS']
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
            bins = WasteBin.objects.filter(organization_id=org_id)
        else:
            # For superadmin, return all bins
            bins = WasteBin.objects.all()
        
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
    
    def delete(self, request, pk):
        bin = get_object_or_404(WasteBin, pk=pk)
        
        # Check if user has permission to access this bin
        org_id = request.session.get('organization_id')
        if org_id and str(bin.organization_id) != org_id:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        bin.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


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
        facilities = Facility.objects.all()
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
        facility = get_object_or_404(Facility, pk=pk)
        serializer = FacilitySerializer(facility)
        return Response(serializer.data)
    
    def put(self, request, pk):
        facility = get_object_or_404(Facility, pk=pk)
        serializer = FacilitySerializer(facility, data=request.data)
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

