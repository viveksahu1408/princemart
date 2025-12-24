from django.db import models
from django.contrib.auth.models import User
import datetime

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

    def __str__(self):
        return self.name

# 3. Order (Bina Area restriction ke)
class Order(models.Model):
    customer_name = models.CharField(max_length=50)
    customer_phone = models.CharField(max_length=15)
    customer_address = models.TextField() # Ab user kuch bhi address dal sakta hai
    
    date = models.DateField(default=datetime.datetime.today)
    total_amount = models.DecimalField(default=0, max_digits=10, decimal_places=2)
    
    status = models.BooleanField(default=False, help_text="Delivery Status")
    is_paid = models.BooleanField(default=False, help_text="Payment Status")

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