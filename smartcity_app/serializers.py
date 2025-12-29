from rest_framework import serializers
from django.utils import timezone
from .models import (
    User, Coordinate, Region, District, Organization, WasteBin, Truck, 
    MoistureSensor, Room, Boiler, Facility, AirSensor, SOSColumn, 
    EcoViolation, ConstructionMission, ConstructionSite, LightROI, 
    LightPole, Bus, ResponsibleOrg, CallRequest, CallRequestTimeline, 
    Notification, ReportEntry, UtilityNode, DeviceHealth, IoTDevice
)


class CoordinateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coordinate
        fields = '__all__'


class RegionSerializer(serializers.ModelSerializer):
    center = CoordinateSerializer(read_only=True)

    class Meta:
        model = Region
        fields = '__all__'


class DistrictSerializer(serializers.ModelSerializer):
    center = CoordinateSerializer(read_only=True)
    region = RegionSerializer(read_only=True)

    class Meta:
        model = District
        fields = '__all__'


class OrganizationSerializer(serializers.ModelSerializer):
    regionId = serializers.CharField(write_only=True, required=False)
    districtId = serializers.CharField(write_only=True, required=False)
    center = CoordinateSerializer(required=False)

    class Meta:
        model = Organization
        fields = '__all__'
        extra_fields = ['regionId', 'districtId']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Add the IDs as separate fields to match frontend expectations
        data['regionId'] = str(instance.region.id) if instance.region else None
        data['districtId'] = str(instance.district.id) if instance.district else None
        return data
    
    def to_internal_value(self, data):
        # Convert regionId and districtId to actual region and district objects
        if 'regionId' in data and data['regionId']:
            try:
                # First try to get by UUID
                region = Region.objects.get(id=data['regionId'])
                data = data.copy()  # Make a copy to avoid modifying the original
                data['region'] = region.pk  # Use the primary key
            except Region.DoesNotExist:
                try:
                    # If UUID lookup fails, try to get by name
                    region = Region.objects.get(name=data['regionId'])
                    data = data.copy()  # Make a copy to avoid modifying the original
                    data['region'] = region.pk  # Use the primary key
                except Region.DoesNotExist:
                    raise serializers.ValidationError({'regionId': 'Region does not exist'})
        
        if 'districtId' in data and data['districtId']:
            try:
                # First try to get by UUID
                district = District.objects.get(id=data['districtId'])
                data = data.copy()  # Make a copy to avoid modifying the original
                data['district'] = district.pk  # Use the primary key
            except District.DoesNotExist:
                try:
                    # If UUID lookup fails, try to get by name
                    district = District.objects.get(name=data['districtId'])
                    data = data.copy()  # Make a copy to avoid modifying the original
                    data['district'] = district.pk  # Use the primary key
                except District.DoesNotExist:
                    raise serializers.ValidationError({'districtId': 'District does not exist'})
        
        return super().to_internal_value(data)
    
    def create(self, validated_data):
        # Handle center coordinate if provided
        center_data = validated_data.pop('center', None)
        if center_data:
            center = Coordinate.objects.create(
                lat=center_data['lat'],
                lng=center_data['lng']
            )
            validated_data['center'] = center
        
        organization = Organization.objects.create(**validated_data)
        return organization
    
    def update(self, instance, validated_data):
        # Handle center coordinate if provided
        center_data = validated_data.pop('center', None)
        if center_data:
            center = getattr(instance, 'center', None)
            if center:
                center.lat = center_data['lat']
                center.lng = center_data['lng']
                center.save()
            else:
                center = Coordinate.objects.create(
                    lat=center_data['lat'],
                    lng=center_data['lng']
                )
                instance.center = center
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class WasteBinSerializer(serializers.ModelSerializer):
    location = CoordinateSerializer(required=False)
    organization_id = serializers.CharField(write_only=True)
    organization = OrganizationSerializer(read_only=True)

    class Meta:
        model = WasteBin
        fields = [
            'id', 'organization', 'organization_id', 'address', 'location', 
            'toza_hudud', 'camera_url', 'google_maps_url', 'fill_level', 
            'fill_rate', 'last_analysis', 'image_url', 'image_source', 
            'is_full', 'device_health', 'qr_code_url'
        ]
        read_only_fields = ['organization']

    def create(self, validated_data):
        # Extract location data and organization ID
        location_data = validated_data.pop('location')
        organization_id = validated_data.pop('organization_id')
        
        # Get the organization instance
        try:
            organization = Organization.objects.get(id=organization_id)
        except Organization.DoesNotExist:
            raise serializers.ValidationError({"organization_id": "Organization not found."})
        
        # Create Coordinate and WasteBin instances
        location = Coordinate.objects.create(**location_data)
        waste_bin = WasteBin.objects.create(
            location=location, 
            organization=organization, 
            **validated_data
        )
        return waste_bin

    def update(self, instance, validated_data):
        # Handle location update if provided
        location_data = validated_data.pop('location', None)
        if location_data:
            # Update the existing location coordinates
            location = instance.location
            for attr, value in location_data.items():
                setattr(location, attr, value)
            location.save()
        
        # Handle organization update if provided
        organization = validated_data.pop('organization', None)
        if organization:
            instance.organization = organization
        
        # Update other fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        return instance


class TruckSerializer(serializers.ModelSerializer):
    location = CoordinateSerializer()

    class Meta:
        model = Truck
        fields = '__all__'

    def create(self, validated_data):
        # Extract location data
        location_data = validated_data.pop('location')
        location = Coordinate.objects.create(**location_data)
        
        # The organization should be passed from the view context
        request = self.context.get('request')
        if request and hasattr(request, 'user') and hasattr(request.user, 'organization'):
            # If the user has an organization, assign it to the truck
            validated_data['organization'] = request.user.organization
            
        # Create the truck with the location
        truck = Truck.objects.create(location=location, **validated_data)
        return truck


class DeviceHealthSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceHealth
        fields = '__all__'


class MoistureSensorSerializer(serializers.ModelSerializer):
    location = CoordinateSerializer()

    class Meta:
        model = MoistureSensor
        fields = '__all__'

    def create(self, validated_data):
        # Extract location data
        location_data = validated_data.pop('location')
        location = Coordinate.objects.create(**location_data)
        
        # Create the moisture sensor with the location
        sensor = MoistureSensor.objects.create(location=location, **validated_data)
        return sensor


class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = '__all__'


class BoilerSerializer(serializers.ModelSerializer):
    device_health = DeviceHealthSerializer(required=False, allow_null=True)
    connected_rooms = RoomSerializer(many=True, required=False)
    target_humidity = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = Boiler
        fields = '__all__'

    def create(self, validated_data):
        device_health_data = validated_data.pop('device_health', None)
        connected_rooms_data = validated_data.pop('connected_rooms', [])
        
        # Set default target_humidity if not provided
        if 'target_humidity' not in validated_data or validated_data.get('target_humidity') is None:
            validated_data['target_humidity'] = 50
        
        # Create default device health if not provided
        if device_health_data:
            device_health = DeviceHealth.objects.create(**device_health_data)
        else:
            device_health = DeviceHealth.objects.create(
                battery_level=100.0,
                signal_strength=100.0,
                last_ping=timezone.now(),
                firmware_version='1.0.0',
                is_online=True
            )
        
        boiler = Boiler.objects.create(device_health=device_health, **validated_data)
        
        for room_data in connected_rooms_data:
            # Set default target_humidity for room if not provided
            if 'target_humidity' not in room_data or room_data.get('target_humidity') is None:
                room_data['target_humidity'] = 50
            room = Room.objects.create(**room_data)
            boiler.connected_rooms.add(room)
        
        return boiler

    def update(self, instance, validated_data):
        device_health_data = validated_data.pop('device_health', None)
        connected_rooms_data = validated_data.pop('connected_rooms', None)

        if device_health_data:
            device_health = instance.device_health
            for attr, value in device_health_data.items():
                setattr(device_health, attr, value)
            device_health.save()

        if connected_rooms_data is not None:
            instance.connected_rooms.clear()
            for room_data in connected_rooms_data:
                # Set default target_humidity for room if not provided
                if 'target_humidity' not in room_data or room_data.get('target_humidity') is None:
                    room_data['target_humidity'] = 50
                
                # Handle room creation with all required fields
                room_id = room_data.get('id')
                if room_id:
                    # If room has an ID, try to get or create it
                    room, created = Room.objects.get_or_create(
                        id=room_id,
                        defaults=room_data
                    )
                    if not created:
                        # Update existing room
                        for attr, value in room_data.items():
                            if attr != 'id':
                                setattr(room, attr, value)
                        room.save()
                else:
                    # Create new room
                    room = Room.objects.create(**room_data)
                instance.connected_rooms.add(room)

        # Set default target_humidity if not provided in update
        if 'target_humidity' not in validated_data or validated_data.get('target_humidity') is None:
            if not hasattr(instance, 'target_humidity') or instance.target_humidity is None:
                validated_data['target_humidity'] = 50

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class FacilitySerializer(serializers.ModelSerializer):
    boilers = BoilerSerializer(many=True, read_only=False)

    class Meta:
        model = Facility
        fields = '__all__'

    def create(self, validated_data):
        boilers_data = validated_data.pop('boilers', [])
        facility = Facility.objects.create(**validated_data)
        
        for boiler_data in boilers_data:
            # Extract connected_rooms from boiler_data
            connected_rooms_data = boiler_data.pop('connected_rooms', [])
            
            # Create boiler without connected_rooms first
            boiler_serializer = BoilerSerializer(data=boiler_data)
            boiler_serializer.is_valid(raise_exception=True)
            boiler = boiler_serializer.save()
            
            # Now add connected_rooms to the boiler
            for room_data in connected_rooms_data:
                # Set default target_humidity for room if not provided
                if 'target_humidity' not in room_data or room_data.get('target_humidity') is None:
                    room_data['target_humidity'] = 50
                
                # Handle room creation with all required fields
                room_id = room_data.get('id')
                if room_id:
                    # If room has an ID, try to get or create it
                    room, created = Room.objects.get_or_create(
                        id=room_id,
                        defaults=room_data
                    )
                    if not created:
                        # Update existing room
                        for attr, value in room_data.items():
                            if attr != 'id':
                                setattr(room, attr, value)
                        room.save()
                else:
                    # Create new room
                    room = Room.objects.create(**room_data)
                boiler.connected_rooms.add(room)
            
            facility.boilers.add(boiler)
        
        return facility

    def update(self, instance, validated_data):
        boilers_data = validated_data.pop('boilers', None)

        if boilers_data is not None:
            # Get existing boiler IDs
            existing_boiler_ids = set(instance.boilers.values_list('id', flat=True))
            incoming_boiler_ids = set()
            
            for boiler_data in boilers_data:
                boiler_id = boiler_data.get('id')
                
                # Extract connected_rooms from boiler_data
                connected_rooms_data = boiler_data.pop('connected_rooms', [])
                
                if boiler_id and boiler_id in existing_boiler_ids:
                    # Update existing boiler
                    boiler = instance.boilers.get(id=boiler_id)
                    boiler_serializer = BoilerSerializer(boiler, data=boiler_data, partial=True)
                    boiler_serializer.is_valid(raise_exception=True)
                    boiler = boiler_serializer.save()
                    
                    # Update connected rooms for this boiler
                    boiler.connected_rooms.clear()
                    for room_data in connected_rooms_data:
                        # Set default target_humidity for room if not provided
                        if 'target_humidity' not in room_data or room_data.get('target_humidity') is None:
                            room_data['target_humidity'] = 50
                        
                        # Handle room creation with all required fields
                        room_id = room_data.get('id')
                        if room_id:
                            # If room has an ID, try to get or create it
                            room, created = Room.objects.get_or_create(
                                id=room_id,
                                defaults=room_data
                            )
                            if not created:
                                # Update existing room
                                for attr, value in room_data.items():
                                    if attr != 'id':
                                        setattr(room, attr, value)
                                room.save()
                        else:
                            # Create new room
                            room = Room.objects.create(**room_data)
                        boiler.connected_rooms.add(room)
                    
                    incoming_boiler_ids.add(boiler_id)
                else:
                    # Create new boiler
                    # Create boiler without connected_rooms first
                    boiler_serializer = BoilerSerializer(data=boiler_data)
                    boiler_serializer.is_valid(raise_exception=True)
                    boiler = boiler_serializer.save()
                    
                    # Now add connected_rooms to the new boiler
                    for room_data in connected_rooms_data:
                        # Set default target_humidity for room if not provided
                        if 'target_humidity' not in room_data or room_data.get('target_humidity') is None:
                            room_data['target_humidity'] = 50
                        
                        # Handle room creation with all required fields
                        room_id = room_data.get('id')
                        if room_id:
                            # If room has an ID, try to get or create it
                            room, created = Room.objects.get_or_create(
                                id=room_id,
                                defaults=room_data
                            )
                            if not created:
                                # Update existing room
                                for attr, value in room_data.items():
                                    if attr != 'id':
                                        setattr(room, attr, value)
                                room.save()
                        else:
                            # Create new room
                            room = Room.objects.create(**room_data)
                        boiler.connected_rooms.add(room)
                    
                    instance.boilers.add(boiler)
                    if boiler_id:
                        incoming_boiler_ids.add(boiler_id)
            
            # Remove boilers that are no longer in the incoming data
            boilers_to_remove = existing_boiler_ids - incoming_boiler_ids
            for boiler_id in boilers_to_remove:
                instance.boilers.remove(boiler_id)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class AirSensorSerializer(serializers.ModelSerializer):
    location = CoordinateSerializer()

    class Meta:
        model = AirSensor
        fields = '__all__'

    def create(self, validated_data):
        # Extract location data
        location_data = validated_data.pop('location')
        location = Coordinate.objects.create(**location_data)
        
        # Create the air sensor with the location
        sensor = AirSensor.objects.create(location=location, **validated_data)
        return sensor


class SOSColumnSerializer(serializers.ModelSerializer):
    location = CoordinateSerializer()
    device_health = DeviceHealthSerializer()

    class Meta:
        model = SOSColumn
        fields = '__all__'

    def create(self, validated_data):
        location_data = validated_data.pop('location')
        device_health_data = validated_data.pop('device_health')
        
        location = Coordinate.objects.create(**location_data)
        device_health = DeviceHealth.objects.create(**device_health_data)
        
        sos_column = SOSColumn.objects.create(
            location=location,
            device_health=device_health,
            **validated_data
        )
        return sos_column

    def update(self, instance, validated_data):
        location_data = validated_data.pop('location', None)
        device_health_data = validated_data.pop('device_health', None)

        if location_data:
            location = instance.location
            for attr, value in location_data.items():
                setattr(location, attr, value)
            location.save()

        if device_health_data:
            device_health = instance.device_health
            for attr, value in device_health_data.items():
                setattr(device_health, attr, value)
            device_health.save()

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class EcoViolationSerializer(serializers.ModelSerializer):
    class Meta:
        model = EcoViolation
        fields = '__all__'


class ConstructionMissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConstructionMission
        fields = '__all__'


class ConstructionSiteSerializer(serializers.ModelSerializer):
    missions = ConstructionMissionSerializer(many=True)

    class Meta:
        model = ConstructionSite
        fields = '__all__'

    def create(self, validated_data):
        missions_data = validated_data.pop('missions', [])
        construction_site = ConstructionSite.objects.create(**validated_data)
        
        for mission_data in missions_data:
            mission_serializer = ConstructionMissionSerializer(data=mission_data)
            mission_serializer.is_valid(raise_exception=True)
            mission = mission_serializer.save()
            construction_site.missions.add(mission)
        
        return construction_site

    def update(self, instance, validated_data):
        missions_data = validated_data.pop('missions', None)

        if missions_data is not None:
            instance.missions.clear()
            for mission_data in missions_data:
                mission_serializer = ConstructionMissionSerializer(data=mission_data)
                mission_serializer.is_valid(raise_exception=True)
                mission = mission_serializer.save()
                instance.missions.add(mission)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class LightROISerializer(serializers.ModelSerializer):
    class Meta:
        model = LightROI
        fields = '__all__'


class LightPoleSerializer(serializers.ModelSerializer):
    location = CoordinateSerializer()
    rois = LightROISerializer(many=True)

    class Meta:
        model = LightPole
        fields = '__all__'

    def create(self, validated_data):
        location_data = validated_data.pop('location')
        rois_data = validated_data.pop('rois', [])
        
        location = Coordinate.objects.create(**location_data)
        light_pole = LightPole.objects.create(location=location, **validated_data)
        
        for roi_data in rois_data:
            roi = LightROI.objects.create(**roi_data)
            light_pole.rois.add(roi)
        
        return light_pole

    def update(self, instance, validated_data):
        location_data = validated_data.pop('location', None)
        rois_data = validated_data.pop('rois', None)

        if location_data:
            location = instance.location
            for attr, value in location_data.items():
                setattr(location, attr, value)
            location.save()

        if rois_data is not None:
            instance.rois.clear()
            for roi_data in rois_data:
                roi, created = LightROI.objects.get_or_create(**roi_data)
                instance.rois.add(roi)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class BusSerializer(serializers.ModelSerializer):
    location = CoordinateSerializer()

    class Meta:
        model = Bus
        fields = '__all__'

    def create(self, validated_data):
        location_data = validated_data.pop('location')
        location = Coordinate.objects.create(**location_data)
        
        bus = Bus.objects.create(location=location, **validated_data)
        return bus

    def update(self, instance, validated_data):
        location_data = validated_data.pop('location', None)
        if location_data:
            location = instance.location
            for attr, value in location_data.items():
                setattr(location, attr, value)
            location.save()

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class ResponsibleOrgSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResponsibleOrg
        fields = '__all__'


class CallRequestTimelineSerializer(serializers.ModelSerializer):
    class Meta:
        model = CallRequestTimeline
        fields = '__all__'


class CallRequestSerializer(serializers.ModelSerializer):
    timeline = CallRequestTimelineSerializer(many=True, read_only=True)

    class Meta:
        model = CallRequest
        fields = '__all__'


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__'


class ReportEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportEntry
        fields = '__all__'


class IoTDeviceSerializer(serializers.ModelSerializer):
    location = CoordinateSerializer()
    
    class Meta:
        model = IoTDevice
        fields = '__all__'
    
    def create(self, validated_data):
        # Extract location data
        location_data = validated_data.pop('location')
        location = Coordinate.objects.create(**location_data)
        
        # Create the IoT device with the location
        iot_device = IoTDevice.objects.create(location=location, **validated_data)
        return iot_device
    
    def update(self, instance, validated_data):
        location_data = validated_data.pop('location', None)
        if location_data:
            location = instance.location
            for attr, value in location_data.items():
                setattr(location, attr, value)
            location.save()
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class UtilityNodeSerializer(serializers.ModelSerializer):
    location = CoordinateSerializer()

    class Meta:
        model = UtilityNode
        fields = '__all__'

    def create(self, validated_data):
        location_data = validated_data.pop('location')
        location = Coordinate.objects.create(**location_data)
        
        utility_node = UtilityNode.objects.create(location=location, **validated_data)
        return utility_node

    def update(self, instance, validated_data):
        location_data = validated_data.pop('location', None)
        if location_data:
            location = instance.location
            for attr, value in location_data.items():
                setattr(location, attr, value)
            location.save()

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance