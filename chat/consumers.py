import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.db.models import Q
from django.utils.timezone import localtime


class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()

        self.receiver_id = self.scope["url_route"]["kwargs"]["receiver_id"]
        self.user = self.scope["user"]

        if not self.user.is_authenticated:
            await self.close()
            return

        self.other_user = await get_user_by_id(self.receiver_id)

        self.room_group_name = f"chat_{min(self.user.id, self.other_user.id)}_{max(self.user.id, self.other_user.id)}"

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        history = await get_message_list(self.user.id, self.other_user.id)

        await self.send(text_data=json.dumps({
            "message_history": history
        }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data["message"]

        sender = self.user.username
        receiver = self.other_user.username

        saved_message = await save_to_message_data(self.user, self.other_user, message)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "sender": sender,
                "sender_id": self.user.id,
                "receiver": receiver,
                "message": message,
                "timestamp": localtime(saved_message.timestamp).strftime("%I:%M %p"),
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event))


@database_sync_to_async
def get_user_by_id(user_id):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    return User.objects.get(id=user_id)


@database_sync_to_async
def save_to_message_data(sender, receiver, message):
    from .models import Message 

    return Message.objects.create(
        sender=sender,
        receiver=receiver,
        message=message
    )


@database_sync_to_async
def get_message_list(user_id, other_id):
    from .models import Message 

    messages = Message.objects.filter(
        Q(sender_id=user_id, receiver_id=other_id) |
        Q(sender_id=other_id, receiver_id=user_id)
    ).order_by("timestamp")

    return [
        {
            "sender_id": msg.sender.id,
            "sender": msg.sender.username,
            "receiver": msg.receiver.username,
            "message": msg.message,
            "timestamp": msg.timestamp.strftime("%I:%M %p")
        }
        for msg in messages
    ]