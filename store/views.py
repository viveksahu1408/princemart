from django.shortcuts import render
from django.db.models import Sum
from django.contrib.admin.views.decorators import staff_member_required
from .models import Product, Order, OrderItem,Category, Banner
import datetime
from django.shortcuts import redirect, get_object_or_404
from .models import Product
from django.contrib import messages
from .forms import OrderForm
from django.db.models import Q # Search ke liye
#pdf ke liye
from .utils import render_to_pdf 
import csv # Excel export ke liye
from django.http import HttpResponse
from django.db.models import Sum,Count # Ye import jaruri hai
from django.db.models.functions import TruncMonth
from .models import Notification,Cart, CartItem # notification ke liye h 
from django.core.exceptions import ObjectDoesNotExist # Ye error handle karne ke liye
from django.http import JsonResponse # Sabse upar ye import kar
from django.contrib.auth.models import User


@staff_member_required # Sirf admin hi dekh payega
def admin_dashboard(request):
    # 1. Basic Stats cards ke liye
    total_products = Product.objects.count()
    total_orders = Order.objects.count()
    total_stock = Product.objects.aggregate(Sum('stock_quantity'))['stock_quantity__sum'] or 0
    
    #total_orders = orders.count()
    # 1. Date Filter Logic
    orders = Order.objects.all().order_by('-id')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

   # 1. Search Logic (Name or Mobile)
    search_query = request.GET.get('search_query')
    if search_query:
        orders = orders.filter(
            Q(customer_name__icontains=search_query) | 
            Q(customer_phone__icontains=search_query)
        )

    if start_date and end_date:
        # Agar date select ki hai to filter karo
        orders = orders.filter(date__range=[start_date, end_date])

    #total_orders = Order.objects.count()
    pending_orders = Order.objects.filter(status=False).count()
    completed_orders = Order.objects.filter(status=True).count()

    # Sirf delivered orders ka total paisa
    revenue = Order.objects.filter(status=True).aggregate(Sum('total_amount'))['total_amount__sum'] or 0

    # Total Kamai (Sum)
    total_sales = Order.objects.filter(status=True).aggregate(Sum('total_amount'))['total_amount__sum'] or 0

    # Recent 5 Orders
    recent_orders = Order.objects.all().order_by('-id')[:5]

    # 2. Graph ke liye Data (Last 6 Months ki Sales)
    # Ye thoda advanced logic hai, dhyan se dekhna
    today = datetime.date.today()
    months = []
    sales = []

    #notification ke liye h ye 
    admin_notifs = Notification.objects.filter(for_admin=True).order_by('-date')[:5] # Latest 5 dikhayenge

    for i in range(5, -1, -1):
        # Pichle 6 mahine calculate karo
        date_limit = today - datetime.timedelta(days=i*30)
        month_name = date_limit.strftime('%B') # e.g. January
        months.append(month_name)
        
        # Us mahine ki sales
        monthly_sales = Order.objects.filter(
            date__year=date_limit.year, 
            date__month=date_limit.month, 
            status=True
        ).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        sales.append(int(monthly_sales))


    context = {
        'total_products': total_products,
        'orders': orders, # Ye filtered list hai
        'total_orders': total_orders,
        'total_stock': total_stock,
        'revenue': revenue,
        'months': months, # Graph X-Axis
        'sales': sales,  # Graph Y-Axis
        'pending_orders': pending_orders,
        'completed_orders': completed_orders,
        'total_sales': total_sales,
        'recent_orders': recent_orders,
        'admin_notifs': admin_notifs, 
    }
    return render(request, 'admin_dashboard.html', context)


#home page 
def home(request):
    products = Product.objects.all()
    categories = Category.objects.all()
    products = Product.objects.all()

    # 1. Category Filter Logic
    category_id = request.GET.get('category') # URL se category id nikalo
    if category_id:
        products = products.filter(category_id=category_id)

    # 2. Search Logic
    search_query = request.GET.get('search') # URL se search text nikalo
    if search_query:
        # Naam me ya Description me dhundho
        products = products.filter(Q(name__icontains=search_query) | Q(description__icontains=search_query))

    # Sirf active banners nikalo
    banners = Banner.objects.filter(is_active=True)

    context = {
        'products': products,
        'categories': categories,
        'banners': banners, # Template me bheja
    }
    return render(request, 'index.html', context)
'''
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

            #ye notifications ke liye 
            Notification.objects.create(
                title="🎉 New Order Received!",
                message=f"{order.customer_name} ne order kiya hai (₹{order.total_amount}). Jaldi pack karo!",
                for_admin=True,
                link=f"/admin/store/order/{order.id}/change/" # Click karke seedha order page khulega
            )

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
'''

# --- HELPER FUNCTION (Cart ID nikalne ke liye) ---
def _cart_id(request):
    cart = request.session.session_key
    if not cart:
        cart = request.session.create()
    return cart
# Views.py me add_to_cart function

# def add_to_cart(request, product_id):
#     current_product = Product.objects.get(id=product_id)
    
#     # 1. Cart ka pata lagao
#     try:
#         cart = Cart.objects.get(cart_id=_cart_id(request))
#     except Cart.DoesNotExist:
#         cart = Cart.objects.create(cart_id=_cart_id(request))
#     cart.save()

#     # 2. Cart Item logic
#     try:
#         cart_item = CartItem.objects.get(product=current_product, cart=cart)
#         if request.method == 'POST':
#             quantity = int(request.POST.get('quantity', 1))
#             cart_item.quantity += quantity
#         else:
#             cart_item.quantity += 1
#         cart_item.save()
#     except CartItem.DoesNotExist:
#         quantity = int(request.POST.get('quantity', 1))
#         cart_item.create(
#             product=current_product,
#             quantity=quantity,
#             cart=cart
#         )
#         cart_item.save()
    
#     # --- 👇 YAHAN MISSING THA (Ye line add kar) 👇 ---
#     cart_count = CartItem.objects.filter(cart=cart).count()
#     # ------------------------------------------------

#     return JsonResponse({
#         'status': 'success', 
#         'message': 'Product added successfully', 
#         'cart_count': cart_count  # Ab ye chalega kyunki upar humne count nikaal liya
#     })


def add_to_cart(request, product_id):
    # 1. Product nikalo (get_object_or_404 best hai)
    product = get_object_or_404(Product, id=product_id)

    # 2. Quantity nikalo (Jo humne JS se bheji hai '?quantity=3')
    # Agar URL me quantity nahi mili, to default 1 manenge
    try:
        quantity = int(request.GET.get('quantity', 1))
    except ValueError:
        quantity = 1

    # 3. Cart ka pata lagao
    try:
        cart = Cart.objects.get(cart_id=_cart_id(request))
    except Cart.DoesNotExist:
        cart = Cart.objects.create(cart_id=_cart_id(request))
    cart.save()

    # 4. Cart Item Logic (Jodna hai ya naya banana hai)
    try:
        cart_item = CartItem.objects.get(product=product, cart=cart)
        
        # STOCK CHECK: Jitna stock hai usse jyada add na ho
        if (cart_item.quantity + quantity) <= product.stock_quantity:
            cart_item.quantity += quantity
            cart_item.save()
        else:
            # Agar stock se jyada maang raha hai
            return JsonResponse({'status': 'error', 'message': 'Stock khatam hone wala hai!'})
            
    except CartItem.DoesNotExist:
        # Naya item tabhi banao agar stock available ho
        if quantity <= product.stock_quantity:
            cart_item = CartItem.objects.create(
                product=product,
                quantity=quantity,
                cart=cart
            )
            cart_item.save()
        else:
            return JsonResponse({'status': 'error', 'message': 'Out of Stock!'})
    
    # 5. Cart Count update karo
    cart_count = CartItem.objects.filter(cart=cart).count()

    # 6. JSON Return karo
    return JsonResponse({
        'status': 'success', 
        'message': 'Product added successfully', 
        'cart_count': cart_count
    })


# --- 2. CART DETAILS (Database Wala) ---
# store/views.py

def cart_details(request):
    total_price = 0
    total_items = 0
    cart_items = []

    try:
        cart = Cart.objects.get(cart_id=_cart_id(request))
        cart_items = CartItem.objects.filter(cart=cart, is_active=True)
        
        for cart_item in cart_items:
            # Hum seedha model ki property use karenge calculation ke liye
            total_price += cart_item.total 
            total_items += cart_item.quantity
            
            # ❌ Ye line humne HATA DI (Jo error de rahi thi):
            # cart_item.total = temp_total 

    except ObjectDoesNotExist:
        pass 

    context = {
        'cart_items': cart_items,
        'total_price': total_price,
        'total_items': total_items,
    }
    return render(request, 'cart.html', context)


# --- 3. UPDATE CART (Database Wala) ---
def update_cart(request, product_id, action):
    # Product aur Cart dhundho
    product = get_object_or_404(Product, id=product_id)
    cart = Cart.objects.get(cart_id=_cart_id(request))
    cart_item = get_object_or_404(CartItem, product=product, cart=cart)

    if action == 'plus':
        if cart_item.quantity < product.stock_quantity:
            cart_item.quantity += 1
            cart_item.save()
        else:
            messages.warning(request, f"Sorry, sirf {product.stock_quantity} pieces hi stock me hain.")
    
    elif action == 'minus':
        if cart_item.quantity > 1:
            cart_item.quantity -= 1
            cart_item.save()
        else:
            cart_item.delete() # 1 se kam hua to uda do
    
    elif action == 'remove':
        cart_item.delete()

    return redirect('cart')


# --- 4. CHECKOUT LOGIC (Database Wala) ---
def checkout(request):
    try:
        cart = Cart.objects.get(cart_id=_cart_id(request))
        cart_items = CartItem.objects.filter(cart=cart, is_active=True)
        
        # Agar cart khali hai (database me entry hai par items nahi)
        if not cart_items.exists():
             messages.warning(request, "Cart khali hai bhai!")
             return redirect('home')

    except ObjectDoesNotExist:
        # Cart hi nahi hai
        messages.warning(request, "Cart khali hai bhai!")
        return redirect('home')

    # Total Calculation
    total_price = 0
    for item in cart_items:
        total_price += (item.product.selling_price * item.quantity)

    # Form Submit Logic
    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            # 1. Order Create
            order = form.save(commit=False)
            if request.user.is_authenticated:
                order.user = request.user
            order.total_amount = total_price
            order.save()
            request.session['customer_phone'] = order.customer_phone

            # Notification Logic (Tera purana code)
            Notification.objects.create(
                title="🎉 New Order Received!",
                message=f"{order.customer_name} ne order kiya hai (₹{order.total_amount}). Jaldi pack karo!",
                for_admin=True,
                link=f"/admin/store/order/{order.id}/change/"
            )

            # 2. Cart Items ko Order Items me shift karo
            for item in cart_items:
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    price=item.product.selling_price,
                    quantity=item.quantity
                )
                
                # Stock Minus Logic
                product = item.product
                product.stock_quantity -= item.quantity
                # 👇 YE NAYI LINE JOD DE (Sold Badhane ke liye)
                product.total_sold += item.quantity
                product.save()

            # 3. Cart Khali Karo (Database se item uda do)
            cart_items.delete() 
            # Note: Hum Cart object delete nahi kar rahe, sirf items uda rahe hain
            
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
    customer_info = {}
    orders = []

    # CASE 1: Agar User Login hai (To ID se saare order nikalo)
    if request.user.is_authenticated:
        orders = Order.objects.filter(user=request.user).order_by('-id')
        customer_info = {
            'name': request.user.first_name + ' ' + request.user.last_name,
            'phone': request.user.username, # Agar username hi mobile no. hai
            'address': 'Saved Address'
        }
    
    # CASE 2: Agar Guest User hai (To Session Phone se nikalo)
    else:
        phone = request.session.get('customer_phone')
        if not phone:
            messages.warning(request, "Pehle ek order to place karo bhai!")
            return redirect('home')
        
        orders = Order.objects.filter(customer_phone=phone).order_by('-id')
        
        if orders.exists():
            latest_order = orders.first()
            customer_info = {
                'name': latest_order.customer_name,
                'phone': latest_order.customer_phone,
                'address': f"{latest_order.address_details}, {latest_order.get_area_display()}"                
            }

    context = {
        'orders': orders,
        'customer': customer_info
    }
    return render(request, 'my_orders.html', context)

# 2. Customer dwara Order Receive karna
def mark_order_received(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    
    # Status True kar do (Matlab Complete)
    order.status = True
    order.save()
    
    messages.success(request, "Shukriya! Order Complete ho gaya. ✅")
    return redirect('my_orders')    

#pdf genrate karne ke liye 
# --- 1. Customer Bill (Invoice) ---
def order_invoice(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    items = OrderItem.objects.filter(order=order)
    
    # Tax Calculation (Maan lo 18% GST hai - Client se confirm kar lena)
    # Total Amount me already tax juda hai ya alag se lagana hai?
    # Abhi hum maan rahe hain ki Total me sab include hai, bas dikhana hai breakdown.
    amount_without_tax = round(float(order.total_amount) / 1.18, 2)
    tax_amount = round(float(order.total_amount) - amount_without_tax, 2)

    context = {
        'order': order,
        'items': items,
        'amount_without_tax': amount_without_tax,
        'tax_amount': tax_amount,
        'today': datetime.date.today(),
    }
    return render_to_pdf('invoice.html', context)

# --- 2. Packing List (Delivery Boy ke liye) ---
def packing_list(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    items = OrderItem.objects.filter(order=order)
    
    context = {
        'order': order,
        'items': items,
    }
    return render_to_pdf('packing_list.html', context)

# --- 3. CA ke liye Excel Export (Admin Only) ---
def export_orders_xls(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="orders_report.csv"'

    writer = csv.writer(response)
    # Header Row
    writer.writerow(['Order ID', 'Customer Name', 'Phone', 'Date', 'Total Amount', 'Status'])

    # Data Rows
    orders = Order.objects.all().values_list('id', 'customer_name', 'customer_phone', 'date', 'total_amount', 'status')
    for order in orders:
        status = "Delivered" if order[5] else "Pending"
        writer.writerow([order[0], order[1], order[2], order[3], order[4], status])

    return response    

#notification functions 
def notifications(request):
    phone = request.session.get('customer_phone')
    
    # Logic: Wo notifications dikhao jo (Sabke liye hain) YA (Sirf is user ke liye hain)
    # Aur wo Admin ke liye NAHI honi chahiye
    notifs = Notification.objects.filter(
        (Q(for_user_phone__isnull=True) | Q(for_user_phone=phone)) & Q(for_admin=False)
    ).order_by('-date')

    return render(request, 'notifications.html', {'notifs': notifs})    

#ye delivery options ke liye
@staff_member_required
def admin_toggle_status(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    
    # Agar pending hai to complete kar do, agar complete hai to pending (Toggle)
    order.status = not order.status
    order.save()
    
    status_msg = "Completed" if order.status else "Pending"
    messages.success(request, f"Order #{order.id} is now {status_msg}")
    
    return redirect('admin_dashboard') # Wapas dashboard par bhej diya


# --- 2. Thermal Receipt (Choti Machine ke liye) ---
def order_receipt_pdf(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    # Note: Maine yahan 'items' ka naam badal ke 'order_items' kar diya hai
    # taaki jo HTML maine pehle diya tha usse match kare.
    order_items = OrderItem.objects.filter(order=order) 
    
    # Tax Calculation (Same logic jo tune likha hai)
    try:
        amount_without_tax = round(float(order.total_amount) / 1.18, 2)
        tax_amount = round(float(order.total_amount) - amount_without_tax, 2)
    except:
        amount_without_tax = 0
        tax_amount = 0

    context = {
        'order': order,
        'order_items': order_items, # Dhyan dena: HTML me humne 'order_items' use kiya hai
        'amount_without_tax': amount_without_tax,
        'tax_amount': tax_amount,
        'today': datetime.date.today(),
    }
    
    # YAHAN CHANGE HUA HAI: 
    # Humne 'invoice.html' ki jagah naya 'receipt_pdf.html' lagaya hai
    return render_to_pdf('receipt_pdf.html', context)


# --- Customer Search & Insights View ---
@staff_member_required
def customer_insights(request):
    query = request.GET.get('q')
    users_data = []
    
    if query:
        # Naam, Email ya Username (Mobile) se dhoondho
        users = User.objects.filter(
            username__icontains=query
        ) | User.objects.filter(
            first_name__icontains=query
        ) | User.objects.filter(
            email__icontains=query
        )
        
        # Har dhoondhe huye user ka hisaab nikalo
        for user in users:
            # Total Orders gino
            total_orders = Order.objects.filter(user=user).count()
            
            # Total Kharcha (Amount) jodo
            total_spent = Order.objects.filter(user=user).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
            
            users_data.append({
                'id': user.id,
                'username': user.username, # Mobile No.
                'name': f"{user.first_name} {user.last_name}",
                'email': user.email,
                'total_orders': total_orders,
                'total_spent': total_spent,
                'is_staff': user.is_staff
            })

    context = {
        'users_data': users_data,
        'query': query,
    }
    return render(request, 'customer_insights.html', context)