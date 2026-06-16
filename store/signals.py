from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Product, ProductVariant

@receiver(post_save, sender=Product)
def create_default_product_variant(sender, instance, created, **kwargs):
    """
    Jab bhi koi naya product save hoga, ye automatic uski unit ke hisab se
    ek active default variant (Stock: 20) bana dega.
    """
    if created:
        # Product ki unit ke hisab se naam decode karenge
        product_unit = str(instance.unit).strip().lower() if instance.unit else 'pieces'
        
        if 'packet' in product_unit:
            variant_name = '1 Packet'
        elif 'kilogram' in product_unit or 'kg' in product_unit:
            variant_name = '1 Kg'
        elif 'liter' in product_unit or 'ltr' in product_unit:
            variant_name = '1 Ltr'
        else:
            variant_name = '1 Pcs'

        # Background me automatic entry insert hogi
        ProductVariant.objects.create(
            product=instance,
            weight_or_size=variant_name,
            market_price=instance.market_price,
            selling_price=instance.selling_price,
            stock_quantity=20,  # Default stock strictly 20 pieces
            is_active=True
        )