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
    # Relational fields ko handle karne ke liye:
    category = CategorySerializer(read_only=True)
    
    # 🎯 SUPER TRICK: Ek product ke saare active variants nested JSON bankar jayenge
    # Dhyaan dena: agar tumhare ProductVariant model me product field par related_name='variants' nahi hai, 
    # toh productvariant_set use karna padega.
    variants = ProductVariantSerializer(many=True, read_only=True) 
    
    discount_percentage = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name','image', 'description', 
            'unit', 'market_price', 'selling_price', 
            'stock_quantity', 'category', 'variants', 'discount_percentage'
        ]

    # Agar mobile app me bhi direct discount percentage dikhana ho
    def get_discount_percentage(self, obj):
        try:
            return obj.get_discount_percentage() # Tumhara model wala method call ho jayega
        except:
            if obj.market_price > obj.selling_price:
                return int(((obj.market_price - obj.selling_price) / obj.market_price) * 100)
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
    
    class Meta:
        model = OrderItem
        fields = ['id', 'product_name', 'quantity', 'price']

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