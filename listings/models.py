from django.db import models
from accounts.models import User
from django.conf import settings
from cloudinary.models import CloudinaryField

CATEGORY_CHOICES = [
    ('veg', 'Vegetarian'),
    ('nonveg', 'Non-Vegetarian'),
    ('dessert', 'Dessert'),
    ('beverage', 'Beverage'),
]

class Product(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="products"
    )

    title = models.CharField(max_length=200)
    description = models.TextField()

    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)

    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)

    image = CloudinaryField(
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

class CartItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="cart_items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "product")

    def __str__(self):
        return f"{self.user} -> {self.product}"

class Order(models.Model):

    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("shipped", "Shipped"),
        ("delivered", "Delivered"),
    )

    buyer = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    address = models.TextField(default="Not provided")
    payment_method = models.CharField(max_length=20, default="cod")

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending"
    )

    created_at = models.DateTimeField(auto_now_add=True)

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.message