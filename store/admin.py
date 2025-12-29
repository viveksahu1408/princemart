from django.contrib import admin
from .models import Category, Product, Order, OrderItem
from .models import Banner # Banner import kar
from .models import Notification #ye notifications ke liye

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
    list_display = ('id', 'customer_name', 'total_amount', 'status','is_paid', 'order_actions') # order_actions add kiya    
    # Ye line magic karegi: Admin bina andar gaye bahar se hi status change kar payega
    list_editable = ('status', 'is_paid') 
    
    # Ye naya function buttons banayega
    def order_actions(self, obj):
        from django.utils.html import format_html
        from django.urls import reverse
        return format_html(
            '<a class="button" href="{}">📄 Bill</a>&nbsp;'
            '<a class="button" href="{}" style="background-color:#333; color:fff;">📦 Pack List</a>',
            reverse('order_invoice', args=[obj.id]),  # <--- Yahan spelling check kar
            reverse('packing_list', args=[obj.id]),   # <--- Yahan bhi
        )
    order_actions.short_description = 'Actions'
    order_actions.allow_tags = True


    list_filter = ('status', 'date')
    search_fields = ('customer_name', 'customer_phone')
    
    # Dropdown action add kiya
    actions = [mark_as_delivered]

admin.site.register(Order, OrderAdmin)

# Order Item
admin.site.register(OrderItem)
#banner ke liye 
admin.site.register(Banner)
#notifications ke liye 
admin.site.register(Notification)