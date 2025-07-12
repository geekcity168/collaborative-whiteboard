from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Room, RoomParticipant, DrawingElement, Snapshot, Permission
from .serializers import RoomSerializer, DrawingElementSerializer, SnapshotSerializer
import json
from django.db.models import Q


class RoomViewSet(viewsets.ModelViewSet):
    serializer_class = RoomSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        # Return rooms that are public or user has access to
        return Room.objects.filter(
            Q(is_public=True) | 
            Q(created_by=user) |
            Q(participants__user=user)
        ).distinct()
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        room = self.get_object()
        password = request.data.get('password')
        
        # Check password if room is password protected
        if room.password and room.password != password:
            return Response(
                {'error': 'Invalid password'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check room capacity
        if room.active_users_count >= room.max_users:
            return Response(
                {'error': 'Room is full'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Add user to room participants
        participant, created = RoomParticipant.objects.get_or_create(
            room=room,
            user=request.user,
            defaults={'is_active': True}
        )
        
        if not created:
            participant.is_active = True
            participant.save()
        
        return Response({'message': 'Successfully joined room'})
    
    @action(detail=True, methods=['post'])
    def leave(self, request, pk=None):
        room = self.get_object()
        try:
            participant = RoomParticipant.objects.get(
                room=room,
                user=request.user
            )
            participant.is_active = False
            participant.save()
            return Response({'message': 'Successfully left room'})
        except RoomParticipant.DoesNotExist:
            return Response(
                {'error': 'You are not in this room'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['get'])
    def participants(self, request, pk=None):
        room = self.get_object()
        participants = RoomParticipant.objects.filter(
            room=room, 
            is_active=True
        ).select_related('user')
        
        participants_data = [
            {
                'username': p.user.username,
                'cursor_x': p.cursor_x,
                'cursor_y': p.cursor_y,
                'cursor_color': p.cursor_color,
                'joined_at': p.joined_at
            }
            for p in participants
        ]
        
        return Response(participants_data)
    
    @action(detail=True, methods=['get'])
    def elements(self, request, pk=None):
        room = self.get_object()
        elements = DrawingElement.objects.filter(
            room=room,
            is_deleted=False
        ).order_by('z_index', 'created_at')
        
        serializer = DrawingElementSerializer(elements, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def clear(self, request, pk=None):
        room = self.get_object()
        # Check if user has permission to clear
        if room.created_by != request.user:
            return Response(
                {'error': 'Only room creator can clear the whiteboard'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        DrawingElement.objects.filter(room=room).update(is_deleted=True)
        return Response({'message': 'Whiteboard cleared successfully'})
    
    @action(detail=True, methods=['post'])
    def save_snapshot(self, request, pk=None):
        room = self.get_object()
        name = request.data.get('name', f'Snapshot {room.snapshots.count() + 1}')
        
        # Get all current elements
        elements = DrawingElement.objects.filter(
            room=room,
            is_deleted=False
        ).order_by('z_index', 'created_at')
        
        elements_data = DrawingElementSerializer(elements, many=True).data
        
        snapshot = Snapshot.objects.create(
            room=room,
            name=name,
            description=request.data.get('description', ''),
            created_by=request.user,
            elements_data=json.dumps(elements_data)
        )
        
        return Response({
            'id': snapshot.id,
            'name': snapshot.name,
            'created_at': snapshot.created_at
        })


class DrawingElementViewSet(viewsets.ModelViewSet):
    serializer_class = DrawingElementSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return DrawingElement.objects.filter(
            room__participants__user=self.request.user,
            is_deleted=False
        )
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class SnapshotViewSet(viewsets.ModelViewSet):
    serializer_class = SnapshotSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Snapshot.objects.filter(
            room__participants__user=self.request.user
        )
    
    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        snapshot = self.get_object()
        room = snapshot.room
        
        # Check if user has permission to restore
        if room.created_by != request.user:
            return Response(
                {'error': 'Only room creator can restore snapshots'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Clear current elements
        DrawingElement.objects.filter(room=room).update(is_deleted=True)
        
        # Restore elements from snapshot
        elements_data = json.loads(snapshot.elements_data)
        for element_data in elements_data:
            element_data.pop('id', None)  # Remove ID to create new objects
            DrawingElement.objects.create(
                room=room,
                created_by=request.user,
                **element_data
            )
        
        return Response({'message': 'Snapshot restored successfully'})


@login_required
def whiteboard_room(request, room_id):
    """Main whiteboard interface view"""
    room = get_object_or_404(Room, id=room_id)
    
    # Check if user has access to the room
    if not room.is_public and room.created_by != request.user:
        if not RoomParticipant.objects.filter(room=room, user=request.user).exists():
            return render(request, 'whiteboard/access_denied.html', {'room': room})
    
    context = {
        'room': room,
        'room_id': str(room.id),
        'user': request.user,
        'websocket_url': f'ws://localhost:8000/ws/whiteboard/{room.id}/'
    }
    
    return render(request, 'whiteboard/room.html', context)


def room_list(request):
    """List of available rooms"""
    if request.user.is_authenticated:
        rooms = Room.objects.filter(
            Q(is_public=True) | 
            Q(created_by=request.user) |
            Q(participants__user=request.user)
        ).distinct().order_by('-created_at')
    else:
        rooms = Room.objects.filter(is_public=True).order_by('-created_at')
    
    context = {'rooms': rooms}
    return render(request, 'whiteboard/room_list.html', context)
