from django.contrib import admin
from .models import (
    User, Coordinate, Region, District, Organization, WasteBin, Truck,
    MoistureSensor, Room, Boiler, Facility, AirSensor, SOSColumn,
    EcoViolation, ConstructionMission, ConstructionSite, LightROI,
    LightPole, Bus, ResponsibleOrg, CallRequest, CallRequestTimeline,
    Notification, ReportEntry, UtilityNode, DeviceHealth
)

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['id', 'username', 'email', 'first_name', 'last_name', 'is_staff', 'date_joined']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    list_filter = ['is_staff', 'is_superuser', 'date_joined']


@admin.register(Coordinate)
class CoordinateAdmin(admin.ModelAdmin):
    list_display = ['id', 'lat', 'lng']
    list_filter = ['lat', 'lng']
    search_fields = ['id']


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'center']
    list_filter = ['name']
    search_fields = ['name', 'id']


@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'region', 'center']
    list_filter = ['region', 'name']
    search_fields = ['name', 'id']


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'type', 'login', 'region', 'district']
    list_filter = ['type', 'region', 'district']
    search_fields = ['name', 'login', 'type']
    readonly_fields = ['id']


@admin.register(WasteBin)
class WasteBinAdmin(admin.ModelAdmin):
    list_display = ['id', 'organization', 'address', 'fill_level', 'is_full']
    list_filter = ['organization', 'is_full', 'fill_level']
    search_fields = ['address', 'id']


@admin.register(Truck)
class TruckAdmin(admin.ModelAdmin):
    list_display = ['id', 'organization', 'driver_name', 'plate_number', 'status']
    list_filter = ['organization', 'status']
    search_fields = ['driver_name', 'plate_number', 'id']


@admin.register(MoistureSensor)
class MoistureSensorAdmin(admin.ModelAdmin):
    list_display = ['id', 'mfy', 'status', 'moisture_level']
    list_filter = ['status', 'mfy']
    search_fields = ['mfy', 'id']


@admin.register(Facility)
class FacilityAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'type', 'overall_status']
    list_filter = ['type', 'overall_status']
    search_fields = ['name', 'id']


@admin.register(AirSensor)
class AirSensorAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'mfy', 'aqi', 'status']
    list_filter = ['status', 'mfy']
    search_fields = ['name', 'mfy', 'id']


@admin.register(SOSColumn)
class SOSColumnAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'mfy', 'status']
    list_filter = ['status', 'mfy']
    search_fields = ['name', 'mfy', 'id']


@admin.register(EcoViolation)
class EcoViolationAdmin(admin.ModelAdmin):
    list_display = ['id', 'location_name', 'mfy', 'timestamp', 'confidence']
    list_filter = ['mfy', 'timestamp']
    search_fields = ['location_name', 'mfy', 'id']


@admin.register(ConstructionSite)
class ConstructionSiteAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'status', 'overall_progress']
    list_filter = ['status']
    search_fields = ['name', 'id']


@admin.register(LightPole)
class LightPoleAdmin(admin.ModelAdmin):
    list_display = ['id', 'address', 'status', 'luminance']
    list_filter = ['status']
    search_fields = ['address', 'id']


@admin.register(Bus)
class BusAdmin(admin.ModelAdmin):
    list_display = ['id', 'route_number', 'plate_number', 'driver_name', 'status']
    list_filter = ['status', 'route_number']
    search_fields = ['route_number', 'plate_number', 'driver_name', 'id']


@admin.register(CallRequest)
class CallRequestAdmin(admin.ModelAdmin):
    list_display = ['id', 'citizen_name', 'category', 'status', 'timestamp']
    list_filter = ['status', 'category', 'timestamp']
    search_fields = ['citizen_name', 'category', 'id']


@admin.register(DeviceHealth)
class DeviceHealthAdmin(admin.ModelAdmin):
    list_display = ['id', 'battery_level', 'signal_strength', 'is_online']
    list_filter = ['is_online']
    search_fields = ['id']