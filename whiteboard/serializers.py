from rest_framework import serializers
from .models import Room, RoomParticipant, DrawingElement, Snapshot, Permission
from django.contrib.auth.models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']


class RoomSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)
    active_users_count = serializers.ReadOnlyField()
    
    class Meta:
        model = Room
        fields = [
            'id', 'name', 'description', 'created_by', 'created_at', 
            'updated_at', 'is_public', 'max_users', 'background_color', 
            'grid_enabled', 'active_users_count'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        # Don't include password in serializer for security
        return super().create(validated_data)


class RoomParticipantSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = RoomParticipant
        fields = [
            'user', 'joined_at', 'last_activity', 'is_active',
            'cursor_x', 'cursor_y', 'cursor_color'
        ]


class DrawingElementSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)
    
    class Meta:
        model = DrawingElement
        fields = [
            'id', 'room', 'created_by', 'element_type', 'x', 'y', 
            'width', 'height', 'color', 'stroke_width', 'opacity',
            'path_data', 'text_content', 'font_size', 'font_family',
            'image', 'created_at', 'updated_at', 'z_index'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class SnapshotSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)
    
    class Meta:
        model = Snapshot
        fields = [
            'id', 'room', 'name', 'description', 'created_by',
            'created_at', 'thumbnail'
        ]
        read_only_fields = ['id', 'created_at', 'elements_data']


class PermissionSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    granted_by = UserSerializer(read_only=True)
    
    class Meta:
        model = Permission
        fields = [
            'room', 'user', 'permission_type', 'granted_by', 'granted_at'
        ]
        read_only_fields = ['granted_at']

