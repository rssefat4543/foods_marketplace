
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from .models import Product, Order, CartItem,Notification
from django.core.paginator import Paginator
from django.urls import reverse
from django.contrib import messages
from decimal import Decimal
import json
from django.http import JsonResponse


from django.contrib.auth import get_user_model
from accounts.models import Profile



User = get_user_model()


@never_cache
@login_required
def dashboard(request):
    query = request.GET.get("q")

    products = Product.objects.select_related('owner').all().order_by("-id")

    if query:
        products = products.filter(title__icontains=query)


    paginator = Paginator(products, 12)
    page = request.GET.get("page")
    products = paginator.get_page(page)

    return render(request, "listings/index.html", {
        "products": products
    })



@login_required
def add_product(request):
    if request.method == "POST":

        image = request.FILES.get("image")

        print("FILES:", request.FILES)   # 🔍 DEBUG (temporary)

        product = Product(
            owner=request.user,
            title=request.POST.get("title"),
            description=request.POST.get("description"),
            category=request.POST.get("category"),
            price=request.POST.get("price") or 0,
            stock=request.POST.get("stock") or 0,
        )

        if image:
            product.image = image

        product.save()

        return redirect("listings:dashboard")

    return render(request, "listings/add_product.html")
@login_required
def delete_product(request, pk):
    product = get_object_or_404(Product, pk=pk)

    if product.owner != request.user:
        return redirect("listings:dashboard")

    product.delete()
    return redirect("listings:dashboard")


@login_required
def add_to_cart(request, pk):
    product = get_object_or_404(Product, pk=pk)

    if product.owner == request.user:
        messages.error(request, "You can't add your own product")
        return redirect("listings:dashboard")

    item, created = CartItem.objects.get_or_create(
        user=request.user,
        product=product
    )

    if created:
        messages.success(request, "Added to cart")
    else:
        messages.info(request, "Already in cart")

 
    if request.GET.get("buy_now") == "1":
        return redirect("listings:cart")

    return redirect("listings:dashboard")
@login_required
def update_cart(request, pk, action):
    item = get_object_or_404(CartItem, pk=pk, user=request.user)

    if action == "inc":
        item.quantity += 1
        item.save()

    elif action == "dec":
        if item.quantity > 1:
            item.quantity -= 1
            item.save()
        else:
            item.delete()

    cart_items = CartItem.objects.filter(user=request.user)

    total = sum(i.product.price * i.quantity for i in cart_items if i.product.price)

    return JsonResponse({
        "deleted": item.quantity == 0,
        "quantity": item.quantity if item.pk else 0,
        "item_id": pk,
        "total": float(total)
    })
@login_required
def remove_from_cart(request, pk):
    cart_item = CartItem.objects.filter(
        id=pk,
        user=request.user
    ).first()

    if cart_item:
        cart_item.delete()

    return redirect('listings:cart')

@login_required
def cart_view(request):
    cart_items = CartItem.objects.filter(user=request.user).select_related("product")

    total = Decimal("0.00")

    for item in cart_items:
        if item.product.price:
            total += item.product.price * item.quantity

    return render(request, "listings/cart.html", {
        "cart_items": cart_items,
        "total": total
    })


@login_required
def buy_product(request, pk):
    product = get_object_or_404(Product, pk=pk)

    if product.owner == request.user:
        return redirect("listings:dashboard")

    return render(request, "listings/checkout.html", {
        "product": product
    })

@login_required
def checkout(request):
    cart_items = CartItem.objects.filter(user=request.user).select_related("product")

    if not cart_items.exists():
        return redirect("listings:cart")

    total = sum(i.product.price * i.quantity for i in cart_items)

    return render(request, "listings/checkout.html", {
        "cart_items": cart_items,
        "total": total
    })


@login_required
def place_order_cart(request):

    if request.method != "POST":
        return JsonResponse({
            "success": False,
            "message": "POST required"
        })

    try:
        data = json.loads(request.body.decode("utf-8") or "{}")
    except Exception:
        data = {}

    address = data.get("address", "")
    payment = data.get("payment_method", "cod")
    single_product_id = data.get("product_id")

    cart_items = CartItem.objects.filter(user=request.user)
    last_order_id = None


    if single_product_id:
        product = get_object_or_404(Product, id=single_product_id)

        order = Order.objects.create(
            buyer=request.user,
            product=product,
            quantity=1,
            address=address or "Not provided",
            payment_method=payment,
            status="pending"
        )

        if product.owner and product.owner != request.user:
            Notification.objects.create(
                user=product.owner,
                order=order,
                message=f"New order received for {product.title}"
            )

        last_order_id = order.id

    else:
        if not cart_items.exists():
            return JsonResponse({
                "success": False,
                "message": "Cart empty"
            })

        for item in cart_items:
            order = Order.objects.create(
                buyer=request.user,
                product=item.product,
                quantity=item.quantity,
                address=address or "Not provided",
                payment_method=payment,
                status="pending"
            )

            owner = item.product.owner

         
            if owner and owner != request.user:
                Notification.objects.create(
                    user=owner,
                    order=order,
                    message=f"New order received for {item.product.title}"
                )

            last_order_id = order.id

        cart_items.delete()

    return JsonResponse({
        "success": True,
        "order_id": last_order_id
    })
@login_required
def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)

    return render(request, "listings/product_detail.html", {
        "product": product
    })
def order_detail(request, pk):

    o = Order.objects.get(id=pk, buyer=request.user)

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":

        return JsonResponse({
            "id": o.id,
            "product": o.product.title,
            "status": o.status,
            "quantity": o.quantity,
            "address": o.address,
            "price": o.product.price
        })

    return render(request, "listings/order_detail.html", {"order": o})

def order_history(request):

    orders = Order.objects.filter(buyer=request.user)


    if request.headers.get("X-Requested-With") == "XMLHttpRequest":

        data = list(orders.values("id", "status", "product__title"))
        return JsonResponse(data, safe=False)

    return render(request, "listings/orders.html", {"orders": orders})

@login_required
def my_orders(request):
    orders = Order.objects.filter(
        buyer=request.user
    ).exclude(status="cancelled").select_related("product").order_by("-created_at")

    return render(request, "listings/my_orders.html", {
        "orders": orders
    })

@login_required
def cancel_order(request, pk):

    try:
        order = Order.objects.get(id=pk, buyer=request.user)

        if order.status == "cancelled":
            return JsonResponse({
                "success": False,
                "message": "Already cancelled"
            })

     
        order.status = "cancelled"
        order.save()

        return JsonResponse({
            "success": True,
            "id": pk
        })

    except Order.DoesNotExist:
        return JsonResponse({
            "success": False,
            "message": "Order not found"
        })
@login_required
def notifications_view(request):
    notifications = Notification.objects.filter(
        user=request.user
    ).order_by("-created_at")

    return render(request, "listings/Notificationpage.html", {
        "notifications": notifications
    })

@login_required
def open_notification(request, pk):
    notification = get_object_or_404(
        Notification,
        id=pk,
        user=request.user
    )

    if not notification.is_read:
        notification.is_read = True
        notification.save()

    return render(request, "listings/notification_detail.html", {
        "notification": notification,
        "order": notification.order
    })
@login_required
def mark_notification_read(request, pk):
    n = get_object_or_404(Notification, id=pk, user=request.user)
    n.is_read = True
    n.save()
    return redirect("listings:notifications")

@login_required
def userProfileView(request, id):
    user_obj = get_object_or_404(User, id=id)

    profile = Profile.objects.filter(user=user_obj).first()

    return render(request, 'listings/userProfile.html', {
        "user_obj": user_obj,
        "profile": profile
    })



@login_required
def userMessage(request,id):

    return render(request, 'listings/messages.html',{"id":id})
@login_required
def confirm_order(request, pk):
    order = get_object_or_404(Order, id=pk)

    if order.product.owner != request.user:
        return redirect("listings:dashboard")

    order.status = "processing"
    order.save()

    if order.buyer:
        Notification.objects.create(
            user=order.buyer,
            order=order,
            message=f"Your order for '{order.product.title}' has been confirmed. Delivery in 3–5 days."
        )

    messages.success(request, "Order confirmed")

    return redirect("listings:notifications")
@login_required
def seller_orders(request):
    orders = Order.objects.filter(
        product__owner=request.user,
        status="pending"
    ).select_related("product", "buyer")

    return render(request, "listings/seller_orders.html", {
        "orders": orders
    })

