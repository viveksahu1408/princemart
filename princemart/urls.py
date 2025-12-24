from django.contrib import admin
from django.urls import path
from django.conf import settings               # <--- Image ke liye
from django.conf.urls.static import static     # <--- Image ke liye
from store.views import admin_dashboard,home,add_to_cart,cart_details,update_cart,checkout  # <--- 'home' ko import karna mat bhulna
from store.views import my_orders, mark_order_received # Imports add kar



urlpatterns = [
    path('admin/dashboard/', admin_dashboard, name='admin_dashboard'), # Naya Link
    path('admin/', admin.site.urls),
    path('', home, name='home'),
    #cart ke liye url
    path('add-to-cart/<int:product_id>/', add_to_cart, name='add_to_cart'),
    #cart me session set 
    path('cart/', cart_details, name='cart'), # <--- Ye naya link
    #cart update krne ke liye 
    path('update-cart/<int:product_id>/<str:action>/', update_cart, name='update_cart'),
    #checkout ke liye
    path('checkout/', checkout, name='checkout'),
    #profile section or order confirmation ke liye
    path('my-orders/', my_orders, name='my_orders'),
    path('order-received/<int:order_id>/', mark_order_received, name='mark_order_received'),



]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
