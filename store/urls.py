from django.urls import path
from . import views

urlpatterns = [
    # --- Home & Search ---
    path('', views.home, name='home'),
    
    # --- Product Detail (Naya Route) ---
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),
    
    # --- Cart System ---
    path('cart/', views.cart_details, name='cart'),
    path('add-to-cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('update-cart/<int:product_id>/<str:action>/', views.update_cart, name='update_cart'),
    path('checkout/', views.checkout, name='checkout'),
    
    # --- Profile & Order Status ---
    path('my-orders/', views.my_orders, name='my_orders'),
    path('order-received/<int:order_id>/', views.mark_order_received, name='mark_order_received'),

    # --- Reports (PDF/Excel) & Administration Links ---
    path('invoice/<int:order_id>/', views.order_invoice, name='order_invoice'),
    path('packing-list/<int:order_id>/', views.packing_list, name='packing_list'),
    path('export-orders/', views.export_orders_xls, name='export_orders'),


   # 🎯 API ENDPOINTS
    path('api/categories/', views.api_category_list, name='api_category_list'),
    path('api/products/', views.api_product_list, name='api_product_list'),
    path('api/cart/add/', views.api_add_to_cart, name='api_add_to_cart'),
    path('api/products/<int:product_id>/', views.api_product_detail, name='api_product_detail'), # <-- Ye line ensure karo
    path('api/cart/', views.api_cart_view, name='api_cart_view'),
    path('api/cart/remove/', views.api_remove_from_cart, name='api_remove_from_cart'),
    path('api/order/place/', views.api_place_order, name='api_place_order'),
    path('api/my-orders/', views.api_my_orders, name='api_my_orders'),

]