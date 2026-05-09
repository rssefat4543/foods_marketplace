
import random
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta
from django.core.cache import cache
from .models import OTP, Profile
from listings.models import Order
from django.core.mail import send_mail


User = get_user_model()


# OTP GENERATOR 
def generate_otp(email, purpose="verify"):
    OTP.objects.filter(email=email, purpose=purpose).delete()

    code = str(random.randint(100000, 999999))

    otp = OTP.objects.create(
        email=email,
        code=code,
        purpose=purpose
    )

    send_mail(
        subject="Your OTP Code",
        message=f"Your OTP code is {code}",
        from_email="noreply@market.com",
        recipient_list=[email]
    )

    print("NEW OTP:", code,flush=True)
    return otp



#  RESEND OTP 
def resend_otp(request, user_id):
    user = User.objects.get(id=user_id)

    last_otp = OTP.objects.filter(email=user.email).order_by('-created_at').first()

    if last_otp and (timezone.now() - last_otp.created_at).seconds < 60:
        messages.error(request, "Wait 60 seconds before resending OTP")
        return redirect(request.META.get('HTTP_REFERER'))

    OTP.objects.filter(email=user.email, is_used=False).update(is_used=True)

    generate_otp(user.email, "verify")

    messages.success(request, "OTP resent successfully")
    return redirect(f"/accounts/verify/{user.id}/")


#  REGISTER 


def register(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")

       
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already exists")
            return redirect("register")
        
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists")
            return redirect("register")

        user = User.objects.create_user(
           username=username,
           email=email,
           password=password
      )

        user.is_active = False
        user.is_email_verified = False
        user.save()

        generate_otp(user.email, "verify")

        return redirect(f"/accounts/verify/{user.id}/")

    return render(request, "accounts/register.html")

# VERIFY OTP FOR REGISTRATION
def verify_otp(request, user_id):
    user = get_object_or_404(User, id=user_id)

    if request.method == "POST":
        code = request.POST.get("otp", "").strip()

        print("ENTERED OTP:", code)

        otp = OTP.objects.filter(
            email=user.email,
            code=code,
            purpose="verify",
            is_used=False
        ).order_by("-created_at").first()

        print(
            "DB OTPs:",
            list(
                OTP.objects.filter(email=user.email)
                .values("email", "code", "is_used", "created_at")
            )
        )

        if otp and otp.is_valid():
            user.is_active = True
            user.is_email_verified = True
            user.save()

            otp.is_used = True
            otp.save()

            login(request, user, backend='django.contrib.auth.backends.ModelBackend')

            OTP.objects.filter(email=user.email, purpose="verify").delete()

            print("OTP VERIFIED SUCCESSFULLY")

            return redirect("/listings/dashboard/")

        else:
            print("INVALID OTP ENTERED")
            messages.error(request, "Invalid OTP. Please try again.")

    return render(request, "accounts/verify.html", {"user": user})

# LOGIN 


def login_view(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        user = authenticate(
            request,
            email=email,
            password=password
        )

        if user is None:
            messages.error(request, "Invalid email or password")
            return redirect("login")

        if not user.is_active:
            messages.error(request, "Account not verified")
            return redirect("login")

        login(request, user)
        return redirect("/listings/dashboard/")

    return render(request, "accounts/login.html")
# FORGOT PASSWORD
def forgot_password(request):
    if request.method == "POST":
        email = request.POST.get("email")

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            messages.error(request, "User not found")
            return redirect("forgot_password")

        generate_otp(user.email, "reset")

        return redirect(f"/accounts/reset-otp/{user.id}/")

    return render(request, "accounts/forgot_password.html")

# RESET OTP 
def reset_otp(request, user_id):
    user = get_object_or_404(User, id=user_id)

    if request.method == "POST":
        code = request.POST.get("otp", "").strip()

        otp = OTP.objects.filter(
            email=user.email,
            code=code,
            purpose="reset",
            is_used=False
        ).order_by("-created_at").first()

        if otp and otp.is_valid():
            otp.is_used = True
            otp.save()

            request.session["reset_user_id"] = user.id

            return redirect("set_new_password")

        messages.error(request, "Invalid OTP")

    return render(request, "accounts/reset_otp.html")
def set_new_password(request):
    user_id = request.session.get("reset_user_id")

    if not user_id:
        return redirect("login")

    user = get_object_or_404(User, id=user_id)

    if request.method == "POST":
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        if password != confirm_password:
            messages.error(request, "Passwords do not match")
            return redirect("set_new_password")

       
        user.set_password(password)
        user.save()

        
        request.session.pop("reset_user_id", None)

      
        logout(request)

        messages.success(request, "Password reset successful")

        return redirect("login")

    return render(request, "accounts/set_new_password.html")


#  LOGOUT 
def logout_view(request):
    logout(request)
    return redirect("/accounts/login/")


# PROFILE


@login_required
def profile(request, username=None):


    if username:
        user_obj = get_object_or_404(User, username=username)
    else:
        user_obj = request.user

    profile, _ = Profile.objects.get_or_create(user=user_obj)

    is_owner = request.user == user_obj
    orders = Order.objects.filter(buyer=user_obj).select_related("product").order_by("-created_at")

    return render(request, "accounts/profile.html", {
        "profile": profile,
        "user_obj": user_obj,
        "is_owner": is_owner,
        "orders": orders
    })

@login_required
def profile_view(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        request.user.username = request.POST.get("username")
        request.user.save()

        profile.bio = request.POST.get("bio")

        if request.FILES.get("image"):
            profile.image = request.FILES["image"]

        profile.save()
        return redirect("profile")

    return render(request, "accounts/profile.html", {
        "profile": profile,
        "is_owner": True
    })

# DASHBOARD
@login_required
def dashboard(request):
    return render(request, "listings/dashboard.html")