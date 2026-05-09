from django.contrib import admin
from django.urls import path, include
from accounts import views as accounts_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', accounts_views.register, name='home'),
    path('accounts/', include('accounts.urls')),
    path('listings/', include('listings.urls')),
    path('chat/', include(('chat.urls', 'chat'), namespace='chat')),
]

