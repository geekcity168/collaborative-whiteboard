from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# API Router
router = DefaultRouter()
router.register(r'rooms', views.RoomViewSet, basename='room')
router.register(r'elements', views.DrawingElementViewSet, basename='element')
router.register(r'snapshots', views.SnapshotViewSet, basename='snapshot')

app_name = 'whiteboard'

urlpatterns = [
    # Web views
    path('', views.room_list, name='room_list'),
    path('room/<uuid:room_id>/', views.whiteboard_room, name='room'),
    
    # API endpoints - only for the API namespace
] + router.urls

