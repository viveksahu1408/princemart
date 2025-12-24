from django.shortcuts import render
from django.db.models import Sum
from django.contrib.admin.views.decorators import staff_member_required
from .models import Product, Order, OrderItem,Category
import datetime
from django.shortcuts import redirect, get_object_or_404
from .models import Product
from django.contrib import messages
from .forms import OrderForm
from .models import Order, OrderItem
from django.db.models import Q # Search ke liye

@staff_member_required # Sirf admin hi dekh payega
def admin_dashboard(request):
    # 1. Basic Stats cards ke liye
    total_products = Product.objects.count()
    total_orders = Order.objects.count()
    total_stock = Product.objects.aggregate(Sum('stock_quantity'))['stock_quantity__sum'] or 0
    
    # Sirf delivered orders ka total paisa
    revenue = Order.objects.filter(status=True).aggregate(Sum('total_amount'))['total_amount__sum'] or 0

    # 2. Graph ke liye Data (Last 6 Months ki Sales)
    # Ye thoda advanced logic hai, dhyan se dekhna
    today = datetime.date.today()
    months = []
    sales = []

    for i in range(5, -1, -1): # Pichle 6 mahine ka loop
        date = today - datetime.timedelta(days=i*30)
        month_name = date.strftime("%B") # January, February...
        
        # Us mahine ki sales nikalo
        monthly_sale = Order.objects.filter(
            date__month=date.month, 
            status=True
        ).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        
        months.append(month_name)
        sales.append(float(monthly_sale)) # Decimal ko float me badla chart ke liye

    context = {
        'total_products': total_products,
        'total_orders': total_orders,
        'total_stock': total_stock,
        'revenue': revenue,
        'months': months, # Graph X-Axis
        'sales': sales,   # Graph Y-Axis
    }
    return render(request, 'admin_dashboard.html', context)


#home page 
def home(request):
    products = Product.objects.all()
    categories = Category.objects.all()
    
    # 1. Category Filter Logic
    category_id = request.GET.get('category') # URL se category id nikalo
    if category_id:
        products = products.filter(category_id=category_id)

    # 2. Search Logic
    search_query = request.GET.get('search') # URL se search text nikalo
    if search_query:
        # Naam me ya Description me dhundho
        products = products.filter(Q(name__icontains=search_query) | Q(description__icontains=search_query))

    context = {
        'products': products,
        'categories': categories,
    }
    return render(request, 'index.html', context)

# Cart Logic
# Cart Logic (Updated)
def add_to_cart(request, product_id):
    if request.method == 'POST':
        cart = request.session.get('cart', {})
        product_id = str(product_id)
        
        # HTML form se quantity nikalo (Agar kuch nahi mila to 1 maan lo)
        quantity = int(request.POST.get('quantity', 1))
        
        if product_id in cart:
            cart[product_id] += quantity # Purani quantity me nayi jod do
        else:
            cart[product_id] = quantity # Naya item
        
        request.session['cart'] = cart
        
        # Ye hai wo popup message
        messages.success(request, "Item cart me add ho gaya! 🛒")
        
        return redirect('home')
    else:
        return redirect('home')


# caart details ke liye function

def cart_details(request):
    # 1. Session se cart nikalo
    cart = request.session.get('cart', {})
    
    products = []
    total_price = 0
    total_items = 0

    # 2. Database se products dhundho
    for product_id, quantity in cart.items():
        try:
            product = Product.objects.get(id=product_id)
            total = product.selling_price * quantity
            
            # List me dalo taaki template me dikha sakein
            products.append({
                'product': product,
                'quantity': quantity,
                'total': total
            })
            
            total_price += total
            total_items += quantity
        except Product.DoesNotExist:
            pass # Agar product delete ho gaya ho to ignore karo

    context = {
        'cart_products': products,
        'total_price': total_price,
        'total_items': total_items
    }
    return render(request, 'cart.html', context)    

#cart update karne ke liye 
def update_cart(request, product_id, action):
    cart = request.session.get('cart', {})
    product_id = str(product_id)
    
    if product_id in cart:
        # Stock check karne ke liye product layenge
        product = get_object_or_404(Product, id=product_id)
        current_qty = cart[product_id]

        if action == 'plus':
            # Check karo stock hai ya nahi
            if current_qty < product.stock_quantity:
                cart[product_id] += 1
            else:
                messages.warning(request, f"Sorry, sirf {product.stock_quantity} pieces hi stock me hain.")
        
        elif action == 'minus':
            if current_qty > 1:
                cart[product_id] -= 1
            else:
                # Agar 1 se kam kiya to delete kar do
                del cart[product_id]
        
        elif action == 'remove':
            del cart[product_id]

    request.session['cart'] = cart
    return redirect('cart')    

#checkout ka logic isme 
# Checkout Logic
def checkout(request):
    cart = request.session.get('cart', {})
    
    # Agar cart khali hai to checkout pe mat aane do
    if not cart:
        messages.warning(request, "Cart khali hai bhai!")
        return redirect('home')

    # Total nikalne ka logic
    cart_items = []
    total_price = 0
    for product_id, quantity in cart.items():
        product = Product.objects.get(id=product_id)
        total = product.selling_price * quantity
        total_price += total
        cart_items.append({'product': product, 'quantity': quantity, 'total': total})

    # Form Submit hone par
    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            # 1. Order create karo
            order = form.save(commit=False)
            order.total_amount = total_price
            order.save()
            request.session['customer_phone'] = order.customer_phone
            # 2. Cart items ko OrderItem me dalo aur Stock kam karo
            for item in cart_items:
                OrderItem.objects.create(
                    order=order,
                    product=item['product'],
                    price=item['product'].selling_price,
                    quantity=item['quantity']
                )
                
                # Stock Minus Logic
                product = item['product']
                product.stock_quantity -= item['quantity']
                product.save()

            # 3. Cart khali kar do
            request.session['cart'] = {}
            
            messages.success(request, "Order Place ho gaya! Jald hi delivery hogi. 🎉")
            return redirect('home')
            
    else:
        form = OrderForm()

    context = {
        'form': form,
        'cart_items': cart_items,
        'total_price': total_price
    }
    return render(request, 'checkout.html', context)    

# 1. Profile / My Orders Page
def my_orders(request):
    # Session se number nikalo
    phone = request.session.get('customer_phone')
    
    if not phone:
        messages.warning(request, "Pehle ek order to place karo bhai!")
        return redirect('home')
    
    # Us number ke saare orders dhundho (Latest pehle)
    orders = Order.objects.filter(customer_phone=phone).order_by('-id')
    
    context = {'orders': orders}
    return render(request, 'my_orders.html', context)

# 2. Customer dwara Order Receive karna
def mark_order_received(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    
    # Status True kar do (Matlab Complete)
    order.status = True
    order.save()
    
    messages.success(request, "Shukriya! Order Complete ho gaya. ✅")
    return redirect('my_orders')    