from django.contrib import admin
from .models import Room, RoomParticipant, DrawingElement, Snapshot, Permission


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_by', 'is_public', 'max_users', 'active_users_count', 'created_at']
    list_filter = ['is_public', 'created_at', 'grid_enabled']
    search_fields = ['name', 'description', 'created_by__username']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    def active_users_count(self, obj):
        return obj.active_users_count
    active_users_count.short_description = 'Active Users'


@admin.register(RoomParticipant)
class RoomParticipantAdmin(admin.ModelAdmin):
    list_display = ['user', 'room', 'is_active', 'joined_at', 'last_activity']
    list_filter = ['is_active', 'joined_at', 'last_activity']
    search_fields = ['user__username', 'room__name']
    readonly_fields = ['joined_at']


@admin.register(DrawingElement)
class DrawingElementAdmin(admin.ModelAdmin):
    list_display = ['id', 'element_type', 'room', 'created_by', 'color', 'created_at', 'is_deleted']
    list_filter = ['element_type', 'created_at', 'is_deleted']
    search_fields = ['room__name', 'created_by__username', 'text_content']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(Snapshot)
class SnapshotAdmin(admin.ModelAdmin):
    list_display = ['name', 'room', 'created_by', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name', 'description', 'room__name', 'created_by__username']
    readonly_fields = ['id', 'created_at']


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ['user', 'room', 'permission_type', 'granted_by', 'granted_at']
    list_filter = ['permission_type', 'granted_at']
    search_fields = ['user__username', 'room__name', 'granted_by__username']
    readonly_fields = ['granted_at']
