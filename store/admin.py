from django.contrib import admin
from .models import Category, Product, ProductVariant, Order, OrderItem, Banner, Notification
from django.utils.html import format_html
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin

# =========================================================================
# 1. CATEGORY REGISTRATION
# =========================================================================
admin.site.register(Category)


# =========================================================================
# 2. PRODUCT & PRODUCT VARIANT (VARIANT SYSTEM INTEGRATION)
# =========================================================================
class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1  # Ek khali row hamesha dikhegi naya variant (weight/color) jodne ke liye
    fields = ['image','weight_or_size', 'color', 'market_price', 'selling_price', 'cost_price', 'stock_quantity', 'total_sold', 'is_active']


class ProductAdmin(admin.ModelAdmin):
    # list_display me ab hum variant_type dikhayenge aur list_editable se stock hata diya hai kyuki wo variant me dikhega
    list_display = ('name', 'category', 'variant_type', 'unit', 'stock_status', 'total_sold',)
    search_fields = ('name', 'category__name',)
    list_filter = ('category', 'variant_type',)
    
    # Default Sorting: Jiska total_sold sabse zyada hai ya naye requirements ke hisab se set karein
    ordering = ['name']
    
    # Is line se Product ke page par hi variants jodne ka option niche table me dikhega
    inlines = [ProductVariantInline]

    # Ye function rangeen status banayega variants ki overall management dekhne ke liye
    def stock_status(self, obj):
        # Saare variants ka total stock nikal kar check karte hain
        total_variants_stock = sum(variant.stock_quantity for variant in obj.variants.all())
        
        if total_variants_stock == 0:
            return format_html('<span style="color:red; font-weight:bold;">❌ Out of Stock</span>')
        elif total_variants_stock <= 10:
            return format_html('<span style="color:orange; font-weight:bold;">⚠️ Low Stock ({})</span>', total_variants_stock)
        else:
            return format_html('<span style="color:green; font-weight:bold;">✅ In Stock</span>')

    stock_status.short_description = "Stock Alert"

admin.site.register(Product, ProductAdmin)
admin.site.register(ProductVariant)  # Isse alag se bhi database check karne me aasani hogi


# =========================================================================
# 3. ORDER & ORDER ITEMS (BILLING & BUTTONS SYSTEM)
# =========================================================================
def mark_as_delivered(modeladmin, request, queryset):
    updated_count = queryset.update(status=True)
    modeladmin.message_user(request, f"{updated_count} Orders ko 'Delivered' mark kar diya gaya hai. ✅")

mark_as_delivered.short_description = "Mark selected orders as Delivered"


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


class OrderAdmin(admin.ModelAdmin):
    # Address aur area ko automatic jod kar dikhane wala function
    def formatted_address(self, obj):
        if obj.address_details and obj.area:
            return f"{obj.address_details}, {obj.get_area_display()}"
        elif obj.address_details:
            return obj.address_details
        else:
            return "Address Not Provided"
        
    formatted_address.short_description = 'Customer Address'

    list_display = ('id', 'customer_name', 'formatted_address', 'total_amount', 'status', 'is_paid', 'order_actions') 
    list_editable = ('status', 'is_paid') 
    list_filter = ('status', 'date')
    search_fields = ('customer_name', 'customer_phone')
    actions = [mark_as_delivered]
    inlines = [OrderItemInline]

    # Bill, Pack List aur Thermal Receipt Buttons System
    def order_actions(self, obj):
        return format_html(
            '<a class="button" href="{}">📄 Bill</a>&nbsp;'
            '<a class="button" href="{}" style="background-color:#333; color:white;">📦 Pack List</a>&nbsp;'
            '<a class="button" href="{}" target="_blank" style="background-color:#f1c40f; color:black; font-weight:bold;">🖨️ Receipt</a>',
            reverse('order_invoice', args=[obj.id]),      # Link 1
            reverse('packing_list', args=[obj.id]),       # Link 2
            reverse('order_receipt_pdf', args=[obj.id]),  # Link 3
        )
    
    order_actions.short_description = 'Actions'

admin.site.register(Order, OrderAdmin)
admin.site.register(OrderItem)


# =========================================================================
# 4. MISCELLANEOUS MODELS
# =========================================================================
admin.site.register(Banner)
admin.site.register(Notification)


# =========================================================================
# 5. CUSTOMER HISTORY FEATURE (USER INLINE)
# =========================================================================
try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass


class OrderInline(admin.TabularInline):
    model = Order
    fields = ('id', 'total_amount', 'status', 'date', 'is_paid')
    readonly_fields = ('id', 'total_amount', 'status', 'date', 'is_paid')
    extra = 0  
    can_delete = False 
    ordering = ('-date',)
    fk_name = 'user' 


class CustomUserAdmin(UserAdmin):
    inlines = [OrderInline]
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'total_orders_count')
    search_fields = ('username', 'first_name', 'last_name', 'email')

    def total_orders_count(self, obj):
        count = Order.objects.filter(user=obj).count() 
        return f"{count} Orders"
    
    total_orders_count.short_description = "Total Orders"

admin.site.register(User, CustomUserAdmin)