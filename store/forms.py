from django import forms
from .models import Order

class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['customer_name', 'customer_phone', 'area', 'address_details', 'delivery_mode']

        widgets = {
            'customer_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apna Naam Likhein'}),
            'customer_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Mobile Number'}),
            
            # --- YAHAN GALTI THI (Ab Sahi Hai) ---
            # Sirf ye ek line rakhni hai RadioSelect wali
            'delivery_mode': forms.RadioSelect(attrs={'class': 'form-check-input'}),
            
            'area': forms.Select(attrs={'class': 'form-control'}),
            'address_details': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Ghar No, Gali No, Landmark...'}),
        }