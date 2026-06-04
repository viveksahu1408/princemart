from django.db import models
from django.contrib.auth.models import User
import datetime

# --- KATNI AREA LIST (Dropdown ke liye) ---
KATNI_AREAS = (
    ('madhavnagar', 'Madhav Nagar'),
    # ('post_office_camp', 'Post Office Camp'),
    # ('shubh_city', 'Shubh City'),
    # ('chawala_chowk', 'Chawala Chowk'),
    # ('shani_mandir_camp', 'Shani Mandir Camp'),
    # ('hospital_line', 'Hospital Line'),
    # ('adm_line', 'ADM Line'),
    # ('gram_panchayat', 'Gram Panchayat'),
    # ('bangla_line', 'Bangla Line'),
    # ('audinance_factory', 'Audinance Factory'),
    # ('keren_line', 'Keren Line'),
    # ('samdariya_colony', 'Samdariya Colony'),
    # ('mes', 'MES'),
    # ('sabji_mandi_camp', 'Sabji Mandi Camp'),
    # ('shanti_nagar', 'Shanti Nagar'),
)

# 1. Category (Samaan ki list)
class Category(models.Model):
    name = models.CharField(max_length=50)
    image = models.ImageField(upload_to='uploads/category/', blank=True, null=True)

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = "Categories"


# 2. Product (Asli Maal)
class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, default=1)
    name = models.CharField(max_length=100)
    description = models.TextField(default='', blank=True, null=True)
    
    # --- YAHAN JODA HAI: Flexible Variant Type Dropdown ---
    VARIANT_TYPES = (
        ('weight', 'Weight / Size (Grocery ke liye)'),
        ('color', 'Color / Rang (Crockery/Jug ke liye)'),
    )
    variant_type = models.CharField(
        max_length=20, 
        choices=VARIANT_TYPES, 
        default='weight', 
        help_text="Customer ko kya dikhana hai: Gram/Ltr ya Color?"
    )
    # -----------------------------------------------------

    # Purana data safe rakhne ke liye existing fields ko chheda nahi hai
    market_price = models.DecimalField(default=0, max_digits=10, decimal_places=2, help_text="MRP (Kata hua rate)")
    total_sold = models.IntegerField(default=0, help_text="Ab tak kitne bike")
    cost_price = models.DecimalField(default=0, max_digits=10, decimal_places=2, help_text="Khareed Rate")
    selling_price = models.DecimalField(default=0, max_digits=10, decimal_places=2, help_text="Bechne ka Rate")
    stock_quantity = models.IntegerField(default=0, help_text="Stock me kitna hai")
    is_active = models.BooleanField(default=True)
    image = models.ImageField(upload_to='uploads/product/')
    
    UNIT_CHOICES = (
        ('kg', 'Kilogram'),
        ('ltr', 'Liter'),
        ('pcs', 'Pieces'),
        ('pkt', 'Packet'),
    )
    unit = models.CharField(max_length=10, choices=UNIT_CHOICES, default='pcs')
    
    def get_discount_percentage(self):
        if self.market_price > self.selling_price:
            discount = ((self.market_price - self.selling_price) / self.market_price) * 100
            return round(discount)
        return 0

    def __str__(self):
        return self.name


# 3. Product Variant (Dynamic Attributes System)
class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    
    # Dono optional hain taaki variant_type ke hisasb se admin use kare
    weight_or_size = models.CharField(max_length=50, blank=True, null=True, help_text="e.g. 100g, 200g, 1Ltr (Grocery ke liye)")
    color = models.CharField(max_length=50, blank=True, null=True, help_text="e.g. Red, Black, Green (Crockery ke liye)")
    
    market_price = models.DecimalField(default=0, max_digits=10, decimal_places=2, help_text="MRP")
    selling_price = models.DecimalField(default=0, max_digits=10, decimal_places=2, help_text="Bechne ka Rate")
    cost_price = models.DecimalField(default=0, max_digits=10, decimal_places=2, help_text="Khareed Rate")
    
    stock_quantity = models.IntegerField(default=0, help_text="Stock me kitna hai")
    total_sold = models.IntegerField(default=0, help_text="Kitne bike")
    is_active = models.BooleanField(default=True)
    image = models.ImageField(upload_to='uploads/variants/', blank=True, null=True) # 👈 Naya Field
    def get_discount_percentage(self):
        if self.market_price > self.selling_price:
            discount = ((self.market_price - self.selling_price) / self.market_price) * 100
            return round(discount)
        return 0

    def __str__(self):
        attribute = self.color if self.color else self.weight_or_size
        return f"{self.product.name} - {attribute} (₹{self.selling_price})"


# --- (Cart System) ---
class Cart(models.Model):
    cart_id = models.CharField(max_length=250, blank=True)
    date_added = models.DateField(auto_now_add=True)

    def __str__(self):
        return self.cart_id

class CartItem(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    # 👇 YAHAN JODA: Variant mapping (null=True rakha hai taaki purane bina variant wale items kharab na hon)
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, null=True, blank=True, related_name='cart_items')
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        if self.variant:
            attribute = self.variant.color if self.variant.color else self.variant.weight_or_size
            return f"{self.product.name} ({attribute})"
        return self.product.name
    
    @property
    def total(self):
        # 👇 DYNAMIC PRICE CHECK: Agar variant juda hai toh uska rate, nahi toh main product ka rate
        if self.variant:
            return self.variant.selling_price * self.quantity
        return self.product.selling_price * self.quantity


# --- Order System ---
class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    customer_name = models.CharField(max_length=50)
    customer_phone = models.CharField(max_length=15)
    area = models.CharField(max_length=100, choices=KATNI_AREAS, default='madhavnagar', help_text="Area Select Karein")
    address_details = models.TextField(blank=True, help_text="House No, Gali No, Landmark") 
    date = models.DateField(default=datetime.datetime.today)
    total_amount = models.DecimalField(default=0, max_digits=10, decimal_places=2)
    status = models.BooleanField(default=False, help_text="Delivery Status")
    is_paid = models.BooleanField(default=False, help_text="Payment Status")

    DELIVERY_CHOICES = [
        ('Delivery', 'Home Delivery'),
        ('Pickup', 'Self Pickup (Dukaan se lenge)'),
    ]
    delivery_mode = models.CharField(max_length=20, choices=DELIVERY_CHOICES, default='Delivery')

    def __str__(self):
        return f"Order: {self.id} - {self.customer_name}"
    

# --- Order System ---
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    # 👇 YAHAN BHI JODA: Taaki invoice/admin panel me dikhe ki kaun sa variant order hua tha
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True, related_name='order_items')
    quantity = models.IntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2) # Yeh checkout ke time variant ka rate hi save karega

    def __str__(self):
        if self.variant:
            attribute = self.variant.color if self.variant.color else self.variant.weight_or_size
            return f"{self.quantity} x {self.product.name} ({attribute})"
        return f"{self.quantity} x {self.product.name}"

    def get_cost(self):
        return self.price * self.quantity
    
    

# 5. Banner (Offer Slider)
class Banner(models.Model):
    title = models.CharField(max_length=100, blank=True)
    image = models.ImageField(upload_to='uploads/banners/')
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.title        


# 6. Notification System
class Notification(models.Model):
    title = models.CharField(max_length=100)
    message = models.TextField()
    date = models.DateTimeField(auto_now_add=True)
    for_admin = models.BooleanField(default=False) 
    for_user_phone = models.CharField(max_length=15, null=True, blank=True) 
    link = models.CharField(max_length=200, blank=True, null=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return self.title