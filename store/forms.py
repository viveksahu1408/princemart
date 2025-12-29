from django import forms
from .models import Order

class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        # delivery_mode ko fields me jod diya 👇
        fields = ['customer_name', 'customer_phone', 'customer_address', 'delivery_mode']
        
        widgets = {
            'customer_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apna Naam likhein'}),
            'customer_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Mobile Number'}),
            'customer_address': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Address (Agar Delivery chahiye)', 'rows': 3}),
            
            # Radio Buttons (Gola wale button) Delivery vs Pickup ke liye
            'delivery_mode': forms.RadioSelect(attrs={'class': 'form-check-input'}), 
        }