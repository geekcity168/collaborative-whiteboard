from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid


class Room(models.Model):
    """Whiteboard room where users can collaborate"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_rooms')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    is_public = models.BooleanField(default=False)
    password = models.CharField(max_length=100, blank=True, null=True)
    max_users = models.IntegerField(default=50)
    background_color = models.CharField(max_length=7, default='#ffffff')
    grid_enabled = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    @property
    def active_users_count(self):
        return self.participants.filter(is_active=True).count()


class RoomParticipant(models.Model):
    """Users participating in a whiteboard room"""
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='participants')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    joined_at = models.DateTimeField(default=timezone.now)
    last_activity = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)
    cursor_x = models.FloatField(default=0)
    cursor_y = models.FloatField(default=0)
    cursor_color = models.CharField(max_length=7, default='#000000')
    
    class Meta:
        unique_together = ['room', 'user']
    
    def __str__(self):
        return f'{self.user.username} in {self.room.name}'


class DrawingElement(models.Model):
    """Individual drawing elements on the whiteboard"""
    ELEMENT_TYPES = [
        ('pen', 'Pen'),
        ('line', 'Line'),
        ('rectangle', 'Rectangle'),
        ('circle', 'Circle'),
        ('text', 'Text'),
        ('image', 'Image'),
        ('eraser', 'Eraser'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='elements')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    element_type = models.CharField(max_length=20, choices=ELEMENT_TYPES)
    
    # Position and dimensions
    x = models.FloatField()
    y = models.FloatField()
    width = models.FloatField(default=0)
    height = models.FloatField(default=0)
    
    # Style properties
    color = models.CharField(max_length=7, default='#000000')
    stroke_width = models.FloatField(default=2)
    opacity = models.FloatField(default=1.0)
    
    # Path data for pen/brush strokes
    path_data = models.TextField(blank=True)  # JSON string of path points
    
    # Text content
    text_content = models.TextField(blank=True)
    font_size = models.IntegerField(default=16)
    font_family = models.CharField(max_length=50, default='Arial')
    
    # Image data
    image = models.ImageField(upload_to='whiteboard_images/', blank=True, null=True)
    
    # Metadata
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    z_index = models.IntegerField(default=0)  # Layer order
    is_deleted = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['z_index', 'created_at']
    
    def __str__(self):
        return f'{self.element_type} by {self.created_by.username} in {self.room.name}'


class Snapshot(models.Model):
    """Saved snapshots of the whiteboard state"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='snapshots')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=timezone.now)
    
    # Snapshot data
    elements_data = models.TextField()  # JSON string of all elements
    thumbnail = models.ImageField(upload_to='snapshots/', blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f'Snapshot: {self.name} - {self.room.name}'


class Permission(models.Model):
    """Room permissions for users"""
    PERMISSION_TYPES = [
        ('view', 'View Only'),
        ('draw', 'Draw'),
        ('edit', 'Edit'),
        ('admin', 'Admin'),
    ]
    
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='permissions')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    permission_type = models.CharField(max_length=10, choices=PERMISSION_TYPES, default='draw')
    granted_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='granted_permissions')
    granted_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        unique_together = ['room', 'user']
    
    def __str__(self):
        return f'{self.user.username} - {self.permission_type} in {self.room.name}'
