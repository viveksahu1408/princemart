# store/urls.py

from django.urls import path
from . import views

# Agar yahan 'app_name' likha hai to use hata dena, simple rakho
# app_name = 'store'  <-- Ye line NAHI honi chahiye abhi ke liye

urlpatterns = [
    # --- Purane Pages ---
    path('', views.home, name='home'),
    path('cart/', views.cart_details, name='cart'),
    path('add-to-cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('update-cart/<int:product_id>/<str:action>/', views.update_cart, name='update_cart'),
    path('checkout/', views.checkout, name='checkout'),
    
    # --- Profile & Order Status ---
    path('my-orders/', views.my_orders, name='my_orders'),
    path('order-received/<int:order_id>/', views.mark_order_received, name='mark_order_received'),

    # --- YE HAI WO MISSING LINES (Jo Error de rahi hain) ---
    path('invoice/<int:order_id>/', views.order_invoice, name='order_invoice'),
    path('packing-list/<int:order_id>/', views.packing_list, name='packing_list'),
    path('export-orders/', views.export_orders_xls, name='export_orders'),
]