from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from store import views

urlpatterns = [
    # --- Admin Dashboard & Actions ---
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    
    # 👇 YE LINE MISSING THI, ISLIYE ERROR AA RAHA THA
    path('admin/toggle-status/<int:order_id>/', views.admin_toggle_status, name='admin_toggle_status'),
    
    # Main Admin Panel
    path('admin/', admin.site.urls),

    # --- Home & Search ---
    path('', views.home, name='home'),

    # --- Cart System ---
    path('cart/', views.cart_details, name='cart'),
    path('add-to-cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('update-cart/<int:product_id>/<str:action>/', views.update_cart, name='update_cart'),
    path('checkout/', views.checkout, name='checkout'),

    # --- Profile & Orders ---
    path('my-orders/', views.my_orders, name='my_orders'),
    path('order-received/<int:order_id>/', views.mark_order_received, name='mark_order_received'),
    
    # --- Notifications ---
    path('notifications/', views.notifications, name='notifications'),

    # --- Reports (PDF/Excel) ---
    path('invoice/<int:order_id>/', views.order_invoice, name='order_invoice'),
    path('packing-list/<int:order_id>/', views.packing_list, name='packing_list'),
    path('export-orders/', views.export_orders_xls, name='export_orders'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)