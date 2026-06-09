from listings.models import Notification
from .models import Profile


def notifications(request):
    unread_count = 0

    if request.user.is_authenticated:
        unread_count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).count()

    return {
        "unread_count": unread_count
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