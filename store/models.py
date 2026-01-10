from django.db import models
from django.contrib.auth.models import User
import datetime

# --- KATNI AREA LIST (Dropdown ke liye) ---
KATNI_AREAS = (
    ('mansarovar', 'Man Sarovar'),
    ('post_office_camp', 'Post Office Camp'),
    ('shubh_city', 'Shubh City'),
    ('chawala_chowk', 'Chawala Chowk'),
    ('shani_mandir_camp', 'Shani Mandir Camp'),
    ('hospital_line', 'Hospital Line'),
    ('adm_line', 'ADM Line'),
    ('gram_panchayat', 'Gram Panchayat'),
    ('bangla_line', 'Bangla Line'),
    ('audinance_factory', 'Audinance Factory'),
    ('keren_line', 'Keren Line'),
    ('samdariya_colony', 'Samdariya Colony'),
    ('mes', 'MES'),
    ('sabji_mandi_camp', 'Sabji Mandi Camp'),
    ('shanti_nagar', 'Shanti Nagar'),
    # Aur jo areas client bole yahan add kar dena
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
    
    # MRP Field
    market_price = models.DecimalField(default=0, max_digits=10, decimal_places=2, help_text="MRP (Kata hua rate)")

    # Total Sold Record
    total_sold = models.IntegerField(default=0, help_text="Ab tak kitne bike")
    
    # Paisa aur Munafa
    cost_price = models.DecimalField(default=0, max_digits=10, decimal_places=2, help_text="Khareed Rate")
    selling_price = models.DecimalField(default=0, max_digits=10, decimal_places=2, help_text="Bechne ka Rate")
    
    # Stock
    stock_quantity = models.IntegerField(default=0, help_text="Stock me kitna hai")
    is_active = models.BooleanField(default=True)
    
    image = models.ImageField(upload_to='uploads/product/')
    
    # Unit
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

# --- (Cart System) ---
class Cart(models.Model):
    cart_id = models.CharField(max_length=250, blank=True)
    date_added = models.DateField(auto_now_add=True)

    def __str__(self):
        return self.cart_id

class CartItem(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.product.name
    
    @property
    def total(self):
        return self.product.selling_price * self.quantity

# --- 3. Order Model (UPDATED) ---
class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    customer_name = models.CharField(max_length=50)
    customer_phone = models.CharField(max_length=15)
    
    # --- YAHAN CHANGE KIYA HAI (Address Section) ---
    
    # 1. Dropdown (Area Select karo)
    area = models.CharField(max_length=100, choices=KATNI_AREAS, default='mansarovar', help_text="Area Select Karein")
    
    # 2. Text Box (Ghar ka number, Gali number likho)
    address_details = models.TextField(blank=True, help_text="House No, Gali No, Landmark") 
    
    # -----------------------------------------------

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
    
    
# 4. OrderItem (Order details)
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
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
    
    # Kiske liye hai?
    for_admin = models.BooleanField(default=False) 
    for_user_phone = models.CharField(max_length=15, null=True, blank=True) 
    
    # Link
    link = models.CharField(max_length=200, blank=True, null=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return self.title