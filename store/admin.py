from django.contrib import admin
from .models import Category, Product, Order, OrderItem

# Category
admin.site.register(Category)

# Product
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'selling_price', 'stock_quantity', 'unit')
    search_fields = ('name',)

admin.site.register(Product, ProductAdmin)

# Order
# Ye function bulk action ke liye hai (Select all -> Mark Delivered)
def mark_as_delivered(modeladmin, request, queryset):
    updated_count = queryset.update(status=True) # Sabka status True kar dega
    modeladmin.message_user(request, f"{updated_count} Orders ko 'Delivered' mark kar diya gaya hai. ✅")

mark_as_delivered.short_description = "Mark selected orders as Delivered"

class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer_name', 'customer_phone', 'total_amount', 'status', 'is_paid', 'date')
    
    # Ye line magic karegi: Admin bina andar gaye bahar se hi status change kar payega
    list_editable = ('status', 'is_paid') 
    
    list_filter = ('status', 'date')
    search_fields = ('customer_name', 'customer_phone')
    
    # Dropdown action add kiya
    actions = [mark_as_delivered]

admin.site.register(Order, OrderAdmin)

# Order Item
admin.site.register(OrderItem)