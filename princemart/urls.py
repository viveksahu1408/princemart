from django.contrib import admin
from django.urls import path,include
from django.conf import settings
from django.conf.urls.static import static
from store import views

urlpatterns = [
    # --- Admin Dashboard & Actions ---
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/toggle-status/<int:order_id>/', views.admin_toggle_status, name='admin_toggle_status'),
    path('admin-dashboard/customers/', views.customer_insights, name='customer_insights'),
    
    # Main Django Admin Panel
    path('admin/', admin.site.urls),
    path('', include('store.urls')), # 👈 Ye line ensure karti hai ki store ki saari urls kaam karein

    # --- Home & Search ---
    path('', views.home, name='home'),
    
    # --- Product Detail Page (Naya Route) ---
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),

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

    # --- Reports (PDF/Excel/Thermal) ---
    path('invoice/<int:order_id>/', views.order_invoice, name='order_invoice'),
    path('packing-list/<int:order_id>/', views.packing_list, name='packing_list'),
    path('export-orders/', views.export_orders_xls, name='export_orders'),
    path('order-receipt/<int:order_id>/', views.order_receipt_pdf, name='order_receipt_pdf'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)