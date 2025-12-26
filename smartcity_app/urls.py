from django.urls import path
from . import views

urlpatterns = [
    # Authentication URLs
    path('auth/login/', views.login_view, name='login'),
    path('auth/validate/', views.validate_token, name='validate_token'),
    
    # Waste Bin URLs
    path('waste-bins/', views.WasteBinListCreateView.as_view(), name='waste-bin-list-create'),
    path('waste-bins/<str:pk>/', views.WasteBinDetailView.as_view(), name='waste-bin-detail'),
    path('waste-bins/<str:pk>/update-image/', views.WasteBinImageUpdateView.as_view(), name='waste-bin-image-update'),
    path('waste-bins/hudud/<str:toza_hudud>/', views.get_waste_bins_by_hudud, name='waste-bins-by-hudud'),
    
    # Truck URLs
    path('trucks/', views.TruckListCreateView.as_view(), name='truck-list-create'),
    path('trucks/<str:pk>/', views.TruckDetailView.as_view(), name='truck-detail'),
    path('trucks/hudud/<str:toza_hudud>/', views.get_trucks_by_hudud, name='trucks-by-hudud'),
    
    # District URLs
    path('districts/', views.DistrictListCreateView.as_view(), name='district-list-create'),
    path('districts/<str:pk>/', views.DistrictDetailView.as_view(), name='district-detail'),
    
    # Region URLs
    path('regions/', views.RegionListCreateView.as_view(), name='region-list-create'),
    path('regions/<str:pk>/', views.RegionDetailView.as_view(), name='region-detail'),
    path('regions/<str:region_id>/districts/', views.get_region_districts, name='region-districts'),
    
    # Moisture Sensor URLs
    path('moisture-sensors/', views.MoistureSensorListCreateView.as_view(), name='moisture-sensor-list-create'),
    path('moisture-sensors/<str:pk>/', views.MoistureSensorDetailView.as_view(), name='moisture-sensor-detail'),
    
    # Room URLs
    path('rooms/', views.RoomListCreateView.as_view(), name='room-list-create'),
    path('rooms/<str:pk>/', views.RoomDetailView.as_view(), name='room-detail'),
    
    # Boiler URLs
    path('boilers/', views.BoilerListCreateView.as_view(), name='boiler-list-create'),
    path('boilers/<str:pk>/', views.BoilerDetailView.as_view(), name='boiler-detail'),
    
    # Facility URLs
    path('facilities/', views.FacilityListCreateView.as_view(), name='facility-list-create'),
    path('facilities/<str:pk>/', views.FacilityDetailView.as_view(), name='facility-detail'),
    path('facilities/type/<str:facility_type>/', views.get_facilities_by_type, name='facilities-by-type'),
    
    # Air Sensor URLs
    path('air-sensors/', views.AirSensorListCreateView.as_view(), name='air-sensor-list-create'),
    path('air-sensors/<str:pk>/', views.AirSensorDetailView.as_view(), name='air-sensor-detail'),
    path('air-sensors/status/<str:status>/', views.get_air_sensors_by_status, name='air-sensors-by-status'),
    
    # SOS Column URLs
    path('sos-columns/', views.SOSColumnListCreateView.as_view(), name='sos-column-list-create'),
    path('sos-columns/<str:pk>/', views.SOSColumnDetailView.as_view(), name='sos-column-detail'),
    path('sos-columns/status/<str:status>/', views.get_sos_columns_by_status, name='sos-columns-by-status'),
    
    # Eco Violation URLs
    path('eco-violations/', views.EcoViolationListCreateView.as_view(), name='eco-violation-list-create'),
    path('eco-violations/<str:pk>/', views.EcoViolationDetailView.as_view(), name='eco-violation-detail'),
    path('eco-violations/date-range/', views.get_eco_violations_by_date_range, name='eco-violations-by-date-range'),
    
    # Construction Mission URLs
    path('construction-missions/', views.ConstructionMissionListCreateView.as_view(), name='construction-mission-list-create'),
    path('construction-missions/<str:pk>/', views.ConstructionMissionDetailView.as_view(), name='construction-mission-detail'),
    
    # Construction Site URLs
    path('construction-sites/', views.ConstructionSiteListCreateView.as_view(), name='construction-site-list-create'),
    path('construction-sites/<str:pk>/', views.ConstructionSiteDetailView.as_view(), name='construction-site-detail'),
    path('construction-sites/status/<str:status>/', views.get_construction_sites_by_status, name='construction-sites-by-status'),
    
    # Light ROI URLs
    path('light-rois/', views.LightROIListCreateView.as_view(), name='light-roi-list-create'),
    path('light-rois/<str:pk>/', views.LightROIDetailView.as_view(), name='light-roi-detail'),
    
    # Light Pole URLs
    path('light-poles/', views.LightPoleListCreateView.as_view(), name='light-pole-list-create'),
    path('light-poles/<str:pk>/', views.LightPoleDetailView.as_view(), name='light-pole-detail'),
    
    # Bus URLs
    path('buses/', views.BusListCreateView.as_view(), name='bus-list-create'),
    path('buses/<str:pk>/', views.BusDetailView.as_view(), name='bus-detail'),
    path('buses/status/<str:status>/', views.get_buses_by_status, name='buses-by-status'),
    
    # Responsible Org URLs
    path('responsible-orgs/', views.ResponsibleOrgListCreateView.as_view(), name='responsible-org-list-create'),
    path('responsible-orgs/<str:pk>/', views.ResponsibleOrgDetailView.as_view(), name='responsible-org-detail'),
    
    # Organization URLs
    path('organizations/', views.OrganizationListCreateView.as_view(), name='organization-list-create'),
    path('organizations/<str:pk>/', views.OrganizationDetailView.as_view(), name='organization-detail'),
    
    # Call Request URLs
    path('call-requests/', views.CallRequestListCreateView.as_view(), name='call-request-list-create'),
    path('call-requests/<str:pk>/', views.CallRequestDetailView.as_view(), name='call-request-detail'),
    path('call-requests/status/<str:status>/', views.get_call_requests_by_status, name='call-requests-by-status'),
    
    # Call Request Timeline URLs
    path('call-request-timelines/', views.CallRequestTimelineListCreateView.as_view(), name='call-request-timeline-list-create'),
    path('call-request-timelines/<str:pk>/', views.CallRequestTimelineDetailView.as_view(), name='call-request-timeline-detail'),
    
    # Notification URLs
    path('notifications/', views.NotificationListCreateView.as_view(), name='notification-list-create'),
    path('notifications/<str:pk>/', views.NotificationDetailView.as_view(), name='notification-detail'),
    path('notifications/unread/', views.get_notifications_unread, name='notifications-unread'),
    path('notifications/<str:notification_id>/read/', views.mark_notification_read, name='mark-notification-read'),
    
    # Report Entry URLs
    path('report-entries/', views.ReportEntryListCreateView.as_view(), name='report-entry-list-create'),
    path('report-entries/<str:pk>/', views.ReportEntryDetailView.as_view(), name='report-entry-detail'),
    
    # Utility Node URLs
    path('utility-nodes/', views.UtilityNodeListCreateView.as_view(), name='utility-node-list-create'),
    path('utility-nodes/<str:pk>/', views.UtilityNodeDetailView.as_view(), name='utility-node-detail'),
    path('utility-nodes/type/<str:utility_type>/', views.get_utility_nodes_by_type, name='utility-nodes-by-type'),
    path('utility-nodes/status/<str:status>/', views.get_utility_nodes_by_status, name='utility-nodes-by-status'),
    
    # Dashboard URLs
    path('dashboard/stats/', views.dashboard_stats, name='dashboard-stats'),
    path('user/organizations/', views.get_user_organizations, name='user-organizations'),
    
    # Search URLs
    path('search/', views.search_entities, name='search-entities'),
    
    # Waste bin analysis
    path('waste-bins/analyze/', views.trigger_waste_bin_analysis, name='trigger-waste-bin-analysis'),
]