from .models import Cart, CartItem

# Ye private function cart_id nikalne ke liye
def _cart_id(request):
    cart = request.session.session_key
    if not cart:
        cart = request.session.create()
    return cart

def cart_count(request):
    item_count = 0
    try:
        cart = Cart.objects.filter(cart_id=_cart_id(request))
        # Agar cart exist karta hai to items gino
        if cart.exists():
            cart_items = CartItem.objects.filter(cart=cart[0])
            for item in cart_items:
                item_count += item.quantity
    except Exception as e:
        item_count = 0
    
    return {'cart_count': item_count}