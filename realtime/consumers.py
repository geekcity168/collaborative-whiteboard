import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from whiteboard.models import Room, RoomParticipant, DrawingElement, Permission
from django.utils import timezone
from django.core.serializers.json import DjangoJSONEncoder


class WhiteboardConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'whiteboard_{self.room_id}'
        self.user = self.scope["user"]
        
        if not self.user.is_authenticated:
            await self.close()
            return
        
        # Check if user has permission to join the room
        room_exists = await self.check_room_exists()
        if not room_exists:
            await self.close()
            return
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Add user as participant
        await self.add_participant()
        
        # Send current whiteboard state to the new user
        await self.send_current_state()
        
        # Notify other users that someone joined
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_joined',
                'user': self.user.username,
                'message': f'{self.user.username} joined the room'
            }
        )
    
    async def disconnect(self, close_code):
        # Remove user from participants
        await self.remove_participant()
        
        # Notify other users that someone left
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_left',
                'user': self.user.username,
                'message': f'{self.user.username} left the room'
            }
        )
        
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'draw':
                await self.handle_draw(data)
            elif message_type == 'erase':
                await self.handle_erase(data)
            elif message_type == 'clear':
                await self.handle_clear()
            elif message_type == 'cursor_move':
                await self.handle_cursor_move(data)
            elif message_type == 'add_element':
                await self.handle_add_element(data)
            elif message_type == 'update_element':
                await self.handle_update_element(data)
            elif message_type == 'delete_element':
                await self.handle_delete_element(data)
                
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON format'
            }))
    
    async def handle_draw(self, data):
        # Save drawing data and broadcast to other users
        element_data = {
            'type': 'draw_update',
            'element_id': data.get('element_id'),
            'path_data': data.get('path_data'),
            'color': data.get('color', '#000000'),
            'stroke_width': data.get('stroke_width', 2),
            'user': self.user.username
        }
        
        # Save to database
        await self.save_drawing_element(data)
        
        # Broadcast to room group (excluding sender)
        await self.channel_layer.group_send(
            self.room_group_name,
            element_data
        )
    
    async def handle_add_element(self, data):
        # Add new element (text, shape, etc.)
        element_id = await self.create_element(data)
        
        element_data = {
            'type': 'element_added',
            'element_id': str(element_id),
            'element_type': data.get('element_type'),
            'x': data.get('x'),
            'y': data.get('y'),
            'width': data.get('width', 0),
            'height': data.get('height', 0),
            'color': data.get('color', '#000000'),
            'text_content': data.get('text_content', ''),
            'user': self.user.username
        }
        
        await self.channel_layer.group_send(
            self.room_group_name,
            element_data
        )
    
    async def handle_cursor_move(self, data):
        # Update cursor position
        await self.update_cursor_position(data.get('x', 0), data.get('y', 0))
        
        # Broadcast cursor position to other users
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'cursor_update',
                'user': self.user.username,
                'x': data.get('x', 0),
                'y': data.get('y', 0)
            }
        )
    
    async def handle_clear(self):
        # Clear the whiteboard
        await self.clear_whiteboard()
        
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'whiteboard_cleared',
                'user': self.user.username
            }
        )
    
    async def handle_erase(self, data):
        # Handle eraser tool
        await self.save_drawing_element({
            **data,
            'element_type': 'eraser'
        })
        
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'erase_update',
                'x': data.get('x'),
                'y': data.get('y'),
                'size': data.get('size', 10),
                'user': self.user.username
            }
        )
    
    async def handle_update_element(self, data):
        # Update existing element
        element_id = data.get('element_id')
        if element_id:
            await self.update_element(element_id, data)
            
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'element_updated',
                    'element_id': element_id,
                    'data': data,
                    'user': self.user.username
                }
            )
    
    async def handle_delete_element(self, data):
        # Delete element
        element_id = data.get('element_id')
        if element_id:
            await self.delete_element(element_id)
            
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'element_deleted',
                    'element_id': element_id,
                    'user': self.user.username
                }
            )
    
    # WebSocket message handlers
    async def draw_update(self, event):
        await self.send(text_data=json.dumps(event))
    
    async def element_added(self, event):
        await self.send(text_data=json.dumps(event))
    
    async def cursor_update(self, event):
        # Don't send cursor updates back to the sender
        if event['user'] != self.user.username:
            await self.send(text_data=json.dumps(event))
    
    async def user_joined(self, event):
        await self.send(text_data=json.dumps(event))
    
    async def user_left(self, event):
        await self.send(text_data=json.dumps(event))
    
    async def whiteboard_cleared(self, event):
        await self.send(text_data=json.dumps(event))
    
    # Database operations
    @database_sync_to_async
    def check_room_exists(self):
        try:
            room = Room.objects.get(id=self.room_id)
            return True
        except Room.DoesNotExist:
            return False
    
    @database_sync_to_async
    def add_participant(self):
        room = Room.objects.get(id=self.room_id)
        participant, created = RoomParticipant.objects.get_or_create(
            room=room,
            user=self.user,
            defaults={'is_active': True, 'last_activity': timezone.now()}
        )
        if not created:
            participant.is_active = True
            participant.last_activity = timezone.now()
            participant.save()
    
    @database_sync_to_async
    def remove_participant(self):
        try:
            participant = RoomParticipant.objects.get(
                room_id=self.room_id,
                user=self.user
            )
            participant.is_active = False
            participant.save()
        except RoomParticipant.DoesNotExist:
            pass
    
    @database_sync_to_async
    def save_drawing_element(self, data):
        room = Room.objects.get(id=self.room_id)
        element_id = data.get('element_id')
        
        if element_id:
            # Update existing element
            try:
                element = DrawingElement.objects.get(id=element_id)
                element.path_data = data.get('path_data', element.path_data)
                element.updated_at = timezone.now()
                element.save()
            except DrawingElement.DoesNotExist:
                pass
        else:
            # Create new element
            DrawingElement.objects.create(
                room=room,
                created_by=self.user,
                element_type='pen',
                x=data.get('x', 0),
                y=data.get('y', 0),
                color=data.get('color', '#000000'),
                stroke_width=data.get('stroke_width', 2),
                path_data=data.get('path_data', '')
            )
    
    @database_sync_to_async
    def create_element(self, data):
        room = Room.objects.get(id=self.room_id)
        element = DrawingElement.objects.create(
            room=room,
            created_by=self.user,
            element_type=data.get('element_type', 'pen'),
            x=data.get('x', 0),
            y=data.get('y', 0),
            width=data.get('width', 0),
            height=data.get('height', 0),
            color=data.get('color', '#000000'),
            stroke_width=data.get('stroke_width', 2),
            text_content=data.get('text_content', ''),
            font_size=data.get('font_size', 16)
        )
        return element.id
    
    @database_sync_to_async
    def update_cursor_position(self, x, y):
        try:
            participant = RoomParticipant.objects.get(
                room_id=self.room_id,
                user=self.user
            )
            participant.cursor_x = x
            participant.cursor_y = y
            participant.last_activity = timezone.now()
            participant.save()
        except RoomParticipant.DoesNotExist:
            pass
    
    @database_sync_to_async
    def clear_whiteboard(self):
        DrawingElement.objects.filter(room_id=self.room_id).update(is_deleted=True)
    
    @database_sync_to_async
    def get_room_elements(self):
        elements = DrawingElement.objects.filter(
            room_id=self.room_id,
            is_deleted=False
        ).order_by('z_index', 'created_at')
        
        return [
            {
                'id': str(element.id),
                'type': element.element_type,
                'x': element.x,
                'y': element.y,
                'width': element.width,
                'height': element.height,
                'color': element.color,
                'stroke_width': element.stroke_width,
                'path_data': element.path_data,
                'text_content': element.text_content,
                'font_size': element.font_size,
                'created_by': element.created_by.username
            }
            for element in elements
        ]
    
    async def send_current_state(self):
        """Send current whiteboard state to newly connected user"""
        elements = await self.get_room_elements()
        
        await self.send(text_data=json.dumps({
            'type': 'initial_state',
            'elements': elements
        }))

