from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from .models import Message
from django.db.models import Q




@login_required
def get_chats_preview(request):
    chats = Message.objects.filter(
        Q(sender=request.user) | Q(receiver=request.user)
    ).order_by("-timestamp")

    seen_users = set()
    unique_chats = []

    for msg in chats:
        other_user = msg.receiver if msg.sender == request.user else msg.sender
      

        if other_user.id not in seen_users:
            seen_users.add(other_user.id)
            msg.receiver = other_user
            unique_chats.append(msg)

    return render(
        request,"listings/chat_room.html", {"chats": unique_chats}
    )

