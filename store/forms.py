from django import forms
from .models import Order

class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['customer_name', 'customer_phone', 'customer_address']
        
        # Thoda style dete hain input boxes ko
        widgets = {
            'customer_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apna Naam likhein'}),
            'customer_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Mobile Number'}),
            'customer_address': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Pura pata (Gali no, Landmark etc.)', 'rows': 3}),
        }