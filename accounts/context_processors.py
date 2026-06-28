from listings.models import Notification
from chat.models import Message
from .models import Profile


def notifications(request):
    unread_count = 0
    unread_message_count = 0

    if request.user.is_authenticated:
        unread_count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).count()
        unread_message_count = Message.objects.filter(
            receiver=request.user,
            is_read=False
        ).count()

    return {
        "unread_count": unread_count,
        "unread_message_count": unread_message_count
    }


def user_profile(request):
    if request.user.is_authenticated:
        profile, _ = Profile.objects.get_or_create(user=request.user)
        return {
            "nav_profile": profile
        }

    return {
        "nav_profile": None
    }