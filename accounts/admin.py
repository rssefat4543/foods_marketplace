
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.db.models import Sum
from django.utils import timezone
from django.utils.html import format_html
from django.urls import reverse

from .models import User, Profile
from listings.models import Product, Order


class ProfileInline(admin.StackedInline):
    model = Profile
    extra = 0
    max_num = 1
    can_delete = False


class ProductInline(admin.TabularInline):
    model = Product
    fk_name = "owner"
    extra = 0

    fields = (
        "title",
        "category",
        "price",
        "stock",
        "product_details",
        "created_at",
        "updated_at",
    )

    readonly_fields = (
        "product_details",
        "created_at",
        "updated_at",
    )

    @admin.display(description="Product Details")
    def product_details(self, obj):
        if not obj or not obj.id:
            return ""

        url = reverse(
            "listings:product_detail",
            args=[obj.id]
        )

        return format_html(
            '<a class="button" href="{}">Product Details</a>',
            url
        )


@admin.register(User)
class UserAdmin(BaseUserAdmin):

    list_display = (
        "username",
        "account_age",
        "products_and_stock",
        "daily_sales",
        "monthly_sales",
        "total_sales",
        "profile_view",
        "is_active",
    )

    list_filter = (
        "is_email_verified",
        "is_active",
        "is_staff",
        "date_joined",
    )

    search_fields = (
        "email",
        "username",
    )

    ordering = ("-date_joined",)

    readonly_fields = (
        "date_joined",
        "last_login",
    )

    inlines = [
        ProfileInline,
        ProductInline,
    ]

    @admin.display(description="Account Age")
    def account_age(self, obj):
        delta = timezone.now() - obj.date_joined

        days = delta.days
        hours = delta.seconds // 3600

        if days > 0:
            return f"{days} days {hours} hours"

        return f"{hours} hours"

    @admin.display(description="Products & Stock")
    def products_and_stock(self, obj):
        url = reverse(
            "admin:accounts_user_change",
            args=[obj.id]
        )

        return format_html(
            '<a href="{}">{}</a>',
            url,
            obj.products.count()
        )

    def seller_orders(self, obj):
        return Order.objects.filter(
            product__owner=obj
        )

    def completed_sales(self, obj):
        return self.seller_orders(obj).filter(
            status="delivered"
        )

    @admin.display(description="Daily Sales")
    def daily_sales(self, obj):
        today = timezone.localdate()

        total = self.completed_sales(obj).filter(
            created_at__date=today
        ).aggregate(
            total=Sum("quantity")
        )["total"]

        return total or 0

    @admin.display(description="Monthly Sales")
    def monthly_sales(self, obj):
        today = timezone.localdate()

        total = self.completed_sales(obj).filter(
            created_at__year=today.year,
            created_at__month=today.month,
        ).aggregate(
            total=Sum("quantity")
        )["total"]

        return total or 0

    @admin.display(description="Total Sales")
    def total_sales(self, obj):
        total = self.completed_sales(obj).aggregate(
            total=Sum("quantity")
        )["total"]

        return total or 0

    @admin.display(description="Profile View")
    def profile_view(self, obj):
        url = reverse(
            "listings:user_profile",
            args=[obj.id]
        )

        return format_html(
            '<a class="button" href="{}">Profile View</a>',
            url
        )

