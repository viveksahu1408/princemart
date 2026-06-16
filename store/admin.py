from django.contrib import admin
from .models import Category, Product, ProductVariant, Order, OrderItem, Banner, Notification
from django.utils.html import format_html
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from django.apps import AppConfig
from django.db.models import Sum
from django.db.models import Min

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
    list_display = ('name', 'category', 'variant_type', 'unit', 'stock_status', 'total_sold',)
    search_fields = ('name', 'category__name',)
    list_filter = ('category', 'variant_type',)
    
    inlines = [ProductVariantInline]

    # 🔥 Database sorting: Jo variant sabse kam stock wala hai, uske hisab se product upar aayega
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(
            annotated_stock=Min('variants__stock_quantity')
        )
        return queryset.order_by('annotated_stock')

    # 🔥 DYNAMIC FIX: Exact Number aur Variant ke Naam ke sath upar lana
    def stock_status(self, obj):
        active_variants = obj.variants.filter(is_active=True)
        if not active_variants.exists():
            return format_html('<b style="color: #e74c3c;">No Variant Found</b>')
            
        # Sabse kam stock wala variant dhoondte hain
        lowest_variant = min(active_variants, key=lambda v: v.stock_quantity)
        qty = lowest_variant.stock_quantity
        name = lowest_variant.weight_or_size  # Jaise '1 Kg', '250 Gm', '1 Pcs'
        
        if qty == 0:
            return format_html('<b style="color: #e74c3c;">{} - 0 Bacha (Khatam)</b>', name)
        elif qty <= 5:
            # 5 ya usse kam bacha hone par Orange alert exact number ke sath
            return format_html('<b style="color: #e67e22;">{} - {} Bacha</b>', name, qty)
        else:
            # Safe zone ke liye simple green count
            return format_html('<span style="color: #2ecc71; font-weight: bold;">✅ {} - {} Bacha</span>', name, qty)

    stock_status.short_description = "Lowest Variant Stock"
    stock_status.admin_order_field = 'annotated_stock'

admin.site.register(Product, ProductAdmin)

# ⚠️ NOTE: Purani duplicate 'admin.site.register(ProductVariant)' line yahan se hata di gayi hai!


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


# =========================================================================
# 6. PRODUCT VARIANT ADVANCED STOCK SORTING SYSTEM
# =========================================================================
@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    # Admin screen par ye columns dikhenge
    list_display = ('product', 'weight_or_size', 'exact_stock_count', 'selling_price')
    
    # 🔥 MAGIC: Sabse kam stock wale variants line se sabse upar milenge (0, then 1, then 2...)
    ordering = ['stock_quantity']
    
    search_fields = ('product__name', 'weight_or_size')

    # Direct Number Display System
    def exact_stock_count(self, obj):
        if obj.stock_quantity == 0:
            return format_html('<b style="color: #e74c3c;">0 Bacha Hai (Khatam)</b>')
        elif obj.stock_quantity <= 5:
            # 5 ya usse kam bacha hone par number alag se highlight hoga
            return format_html('<b style="color: #e67e22;">{} Bacha Hai</b>', obj.stock_quantity)
        else:
            # Normal stock ke liye simple number dikhega
            return format_html('<span style="color: #2ecc71;">{} Bacha Hai</span>', obj.stock_quantity)
            
    exact_stock_count.short_description = 'Available Stock' 