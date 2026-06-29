from rest_framework import serializers
from .models import Product, ProductVariant, Category
from .models import CartItem
from .models import Order, OrderItem

# 1. Category Serializer
class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'image'] # Jo-jo fields Flutter ko bhejne hain

# 2. Product Variant Serializer (Kyunki ek product ke kayi variants ho sakte hain)
class ProductVariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductVariant
        fields = ['id', 'weight_or_size', 'color', 'market_price', 'selling_price', 'stock_quantity', 'is_active']

# 3. Main Product Serializer
class ProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True) 
    
    market_price = serializers.SerializerMethodField()
    selling_price = serializers.SerializerMethodField()
    stock_quantity = serializers.SerializerMethodField()
    discount_percentage = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'image', 'description', 
            'unit', 'market_price', 'selling_price', 
            'stock_quantity', 'category', 'variants', 'discount_percentage'
        ]

    # 🔥 1. Product ID ke base par seedhe ProductVariant table se filter karo
    def get_market_price(self, obj):
        # Seedhe ProductVariant model se query karo bina kisi _set jhanjhat ke
        active_variants = ProductVariant.objects.filter(product=obj, is_active=True)
        lowest_variant = active_variants.order_by('selling_price').first()
        return float(lowest_variant.market_price) if lowest_variant else 0.0

    # 🔥 2. Sabse saste variant ka Selling Price
    def get_selling_price(self, obj):
        active_variants = ProductVariant.objects.filter(product=obj, is_active=True)
        lowest_variant = active_variants.order_by('selling_price').first()
        return float(lowest_variant.selling_price) if lowest_variant else 0.0

    # 🔥 3. Saare active variants ka total stock
    def get_stock_quantity(self, obj):
        active_variants = ProductVariant.objects.filter(product=obj, is_active=True)
        return sum(variant.stock_quantity for variant in active_variants)

    # 🔥 4. Saste variant ke hisaab se discount percentage
    def get_discount_percentage(self, obj):
        m_price = self.get_market_price(obj)
        s_price = self.get_selling_price(obj)
        if m_price > s_price and m_price > 0:
            return int(((m_price - s_price) / m_price) * 100)
        return 0
        
class CartItemSerializer(serializers.ModelSerializer):
    # Nested serializer taaki item ke sath product aur variant ki poori detail chali jaye
    product = ProductSerializer(read_only=True)
    variant = ProductVariantSerializer(read_only=True)
    sub_total = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ['id', 'product', 'variant', 'quantity', 'sub_total']

    # Har item ka total price (price * quantity) nikalne ke liye
    def get_sub_total(self, obj):
        return obj.variant.selling_price * obj.quantity        
    
# 1. Order ke andar ke items ke liye
class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    # 🎯 NEW FIELDS: Variant ka size aur product ki main unit nikalne ke liye
    variant_size = serializers.CharField(source='variant.weight_or_size', read_only=True)
    product_unit = serializers.CharField(source='product.unit', read_only=True) 
    
    class Meta:
        model = OrderItem
        fields = ['id', 'product_name', 'variant_size', 'product_unit', 'quantity', 'price']


# 2. Main Order History Ke Liye
# 2. Main Order History Ke Liye (Updated with total_amount)
class OrderHistorySerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(source='orderitem_set', many=True, read_only=True)
    invoice_url = serializers.SerializerMethodField()
    date_formatted = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 
            'date_formatted', 
            'total_amount',  # 👈 Tumhare template ke hisab se exact name
            'status', 
            'items', 
            'invoice_url'
        ]

    def get_date_formatted(self, obj):
        try:
            return obj.date.strftime('%d %b %Y, %I:%M %p')
        except:
            try:
                return obj.created_at.strftime('%d %b %Y, %I:%M %p')
            except:
                return str(obj.id)

    def get_invoice_url(self, obj):
        request = self.context.get('request')
        if request:
            from django.urls import reverse
            try:
                return request.build_absolute_uri(reverse('order_invoice', args=[obj.id]))
            except:
                return ""
        return ""