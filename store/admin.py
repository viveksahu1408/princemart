from django.contrib import admin
from .models import Category, Product, Order, OrderItem
from .models import Banner 
from .models import Notification 
from django.utils.html import format_html
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin

# Category
admin.site.register(Category)

# Product
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'selling_price', 'stock_quantity', 'unit','stock_status')
    search_fields = ('name','category__name',)

    # Filter: Client side me dekh sakega ki "Low Stock" wale dikhao
    list_filter = ('category',)
    
    # POWERFUL FEATURE: List ke bahar se hi Stock edit karne ki suvidha
    list_editable = ('stock_quantity', 'selling_price')

    # Default Sorting: Jiska stock sabse kam hai, wo sabse upar dikhega
    ordering = ['stock_quantity']

    # Ye function rangeen status banayega
    def stock_status(self, obj):
        if obj.stock_quantity == 0:
            return format_html('<span style="color:red; font-weight:bold;">❌ Out of Stock</span>')
        elif obj.stock_quantity <= 10:  # Agar 10 se kam bacha hai
            return format_html('<span style="color:orange; font-weight:bold;">⚠️ Low Stock ({})</span>', obj.stock_quantity)
        else:
            return format_html('<span style="color:green; font-weight:bold;">✅ In Stock</span>')

    stock_status.short_description = "Stock Alert"

admin.site.register(Product, ProductAdmin)

# Order
# Bulk action (Select all -> Mark Delivered)
def mark_as_delivered(modeladmin, request, queryset):
    updated_count = queryset.update(status=True)
    modeladmin.message_user(request, f"{updated_count} Orders ko 'Delivered' mark kar diya gaya hai. ✅")

mark_as_delivered.short_description = "Mark selected orders as Delivered"

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    
class OrderAdmin(admin.ModelAdmin):
    # 'order_actions' list me hona jaruri hai tabhi button dikhenge
    list_display = ('id', 'customer_name', 'total_amount', 'status','is_paid', 'order_actions') 
    list_editable = ('status', 'is_paid') 
    
    # --- YAHAN CHANGE KIYA HAI ---
    def order_actions(self, obj):
        return format_html(
            # Button 1: Original Invoice (A4)
            '<a class="button" href="{}">📄 Bill</a>&nbsp;'
            
            # Button 2: Packing List (Dark Button)
            '<a class="button" href="{}" style="background-color:#333; color:white;">📦 Pack List</a>&nbsp;'
            
            # Button 3: NEW Thermal Receipt (Yellow Button)
            '<a class="button" href="{}" target="_blank" style="background-color:#f1c40f; color:black; font-weight:bold;">🖨️ Receipt</a>',
            
            reverse('order_invoice', args=[obj.id]),      # Link 1
            reverse('packing_list', args=[obj.id]),       # Link 2
            reverse('order_receipt_pdf', args=[obj.id]),  # Link 3 (Naya wala)
        )
    
    order_actions.short_description = 'Actions'
    order_actions.allow_tags = True
    # -----------------------------

    list_filter = ('status', 'date')
    search_fields = ('customer_name', 'customer_phone')
    actions = [mark_as_delivered]

admin.site.register(Order, OrderAdmin)

# Order Item
admin.site.register(OrderItem)
# Banner
admin.site.register(Banner)
# Notification 
admin.site.register(Notification)

# --- 👇 CUSTOMER HISTORY FEATURE (End me paste kar) 👇 ---

# 1. Pehle purane User Admin ko hatao
try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass

# 2. Orders ki list banayenge jo User ke andar dikhegi
# ... Upar ka code same rahega ...

# 2. Orders ki list banayenge
class OrderInline(admin.TabularInline):
    model = Order
    fields = ('id', 'total_amount', 'status', 'date', 'is_paid')
    readonly_fields = ('id', 'total_amount', 'status', 'date', 'is_paid')
    extra = 0  
    can_delete = False 
    ordering = ('-date',)
    
    # 👇 YE LINE JADU KAREGI (Isse error hat jayega)
    fk_name = 'user' 

# 3. Naya User Admin banao
class CustomUserAdmin(UserAdmin):
    inlines = [OrderInline]
    
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'total_orders_count')
    search_fields = ('username', 'first_name', 'last_name', 'email')

    def total_orders_count(self, obj):
        # Dhyan rakhna: Agar Order model me field ka naam 'customer' hai to yahan bhi change karna padega
        count = Order.objects.filter(user=obj).count() 
        return f"{count} Orders"
    
    total_orders_count.short_description = "Total Orders"

# 4. Register
admin.site.register(User, CustomUserAdmin)