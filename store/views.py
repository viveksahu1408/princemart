# api code start from line number 630 here 
from django.contrib.admin.views.decorators import staff_member_required
from .models import Product, Order, OrderItem,Category, Banner
import datetime
from django.shortcuts import redirect, get_object_or_404,render
from django.contrib import messages
from .forms import OrderForm
from django.db.models import Q,Sum,Count
from .utils import render_to_pdf 
import csv # Excel export ke liye
from django.http import HttpResponse
from django.db.models.functions import TruncMonth
from .models import Notification,Cart, CartItem # notification ke liye h 
from django.core.exceptions import ObjectDoesNotExist # Ye error handle karne ke liye
from django.http import JsonResponse # Sabse upar ye import kar
from django.contrib.auth.models import User
# api vale 
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .serializers import ProductSerializer, CategorySerializer,CartItemSerializer,OrderHistorySerializer
from .models import Product, ProductVariant, Cart, CartItem, Category



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


# --- HELPER FUNCTION (Cart ID nikalne ke liye) ---
def _cart_id(request):
    cart = request.session.session_key
    if not cart:
        cart = request.session.create()
    return cart


# =========================================================================
# 1. ADD TO CART (Variant Supported)
# =========================================================================
def add_to_cart(request, product_id):
    # Safe internal import agar upar na chal raha ho
    from .models import Product, Cart, CartItem, ProductVariant

    product = get_object_or_404(Product, id=product_id)

    # Detail page ke select dropdown se variant_id aayegi
    variant_id = request.GET.get('variant_id')
    
    if not variant_id:
        # Ab ye bina kisi NameError ke chalega 🎯
        first_variant = ProductVariant.objects.filter(product=product, is_active=True).first()
        if first_variant:
            variant_id = first_variant.id
        else:
            return JsonResponse({'status': 'error', 'message': 'Is product ka koi variant available nahi hai!'})

    # Variant object nikalenge
    variant = get_object_or_404(ProductVariant, id=variant_id, product=product)

    # Quantity filter check
    try:
        quantity = int(request.GET.get('quantity', 1))
    except ValueError:
        quantity = 1

    # Cart session handle
    try:
        cart = Cart.objects.get(cart_id=_cart_id(request))
    except Cart.DoesNotExist:
        cart = Cart.objects.create(cart_id=_cart_id(request))
    cart.save()

    # CartItem check aur save logic
    try:
        cart_item = CartItem.objects.get(product=product, variant=variant, cart=cart)
        
        # Variant ke stock se validation check
        if (cart_item.quantity + quantity) <= variant.stock_quantity:
            cart_item.quantity += quantity
            cart_item.save()
        else:
            return JsonResponse({'status': 'error', 'message': f'Stock limited! Sirf {variant.stock_quantity} pieces bache hain.'})
            
    except CartItem.DoesNotExist:
        if quantity <= variant.stock_quantity:
            cart_item = CartItem.objects.create(
                product=product,
                variant=variant,
                quantity=quantity,
                cart=cart
            )
            cart_item.save()
        else:
            return JsonResponse({'status': 'error', 'message': 'Out of Stock!'})
    
    # Total quantity ka sum nikal kar badge real-time sync karenge
    total_qty_dict = CartItem.objects.filter(cart=cart).aggregate(total_qty=Sum('quantity'))
    cart_count = total_qty_dict['total_qty'] or 0

    return JsonResponse({
        'status': 'success', 
        'message': f'{product.name} ({variant.weight_or_size or variant.color or ""}) cart me add ho gaya! 🛒', 
        'cart_count': cart_count
    })

# --- 2. CART DETAILS (Database Wala) ---
# store/views.py

# =========================================================================
# 2. CART DETAILS (Variant Price Calculation)
# =========================================================================
def cart_details(request):
    total_price = 0
    total_items = 0
    cart_items = []

    try:
        cart = Cart.objects.get(cart_id=_cart_id(request))
        cart_items = CartItem.objects.filter(cart=cart, is_active=True)
        
        for cart_item in cart_items:
            # AGAR variant mapped hai, toh rate variant ka lagega warna main product ka
            if cart_item.variant:
                item_price = cart_item.variant.selling_price
            else:
                item_price = cart_item.product.selling_price
                
            item_total = item_price * cart_item.quantity
            cart_item.item_total_price = item_total # Template me access karne ke liye dynamic attribute
            
            total_price += item_total
            total_items += cart_item.quantity

    except ObjectDoesNotExist:
        pass 

    context = {
        'cart_items': cart_items,
        'total_price': total_price,
        'total_items': total_items,
    }
    return render(request, 'cart.html', context)


# =========================================================================
# 3. UPDATE CART (Variant Stock Validation)
# =========================================================================
def update_cart(request, product_id, action):
    # Idhar hum cart_item_id se handle karein toh safe hai, par tumhare structure ke hisab se:
    variant_id = request.GET.get('variant_id') # URL target parameter
    product = get_object_or_404(Product, id=product_id)
    cart = Cart.objects.get(cart_id=_cart_id(request))
    
    if variant_id:
        cart_item = get_object_or_404(CartItem, product=product, variant_id=variant_id, cart=cart)
        max_stock = cart_item.variant.stock_quantity
    else:
        cart_item = CartItem.objects.filter(product=product, cart=cart).first()
        max_stock = product.stock_quantity

    if action == 'plus':
        if cart_item.quantity < max_stock:
            cart_item.quantity += 1
            cart_item.save()
        else:
            messages.warning(request, f"Sorry, sirf {max_stock} pieces hi stock me hain.")
    
    elif action == 'minus':
        if cart_item.quantity > 1:
            cart_item.quantity -= 1
            cart_item.save()
        else:
            cart_item.delete()
    
    elif action == 'remove':
        cart_item.delete()

    return redirect('cart')


# =========================================================================
# 4. CHECKOUT & STOCK DECREMENT (Variant Friendly)
# =========================================================================
def checkout(request):
    try:
        cart = Cart.objects.get(cart_id=_cart_id(request))
        cart_items = CartItem.objects.filter(cart=cart, is_active=True)
        
        if not cart_items.exists():
             messages.warning(request, "Cart khali hai bhai!")
             return redirect('home')
    except ObjectDoesNotExist:
        messages.warning(request, "Cart khali hai bhai!")
        return redirect('home')

    # Total Price calculation based on Variant Prices
    total_price = 0
    for item in cart_items:
        if item.variant:
            total_price += (item.variant.selling_price * item.quantity)
        else:
            total_price += (item.product.selling_price * item.quantity)

    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            if request.user.is_authenticated:
                order.user = request.user
            order.total_amount = total_price
            order.save()
            request.session['customer_phone'] = order.customer_phone

            Notification.objects.create(
                title="🎉 New Order Received!",
                message=f"{order.customer_name} ne order kiya hai (₹{order.total_amount}). Jaldi pack karo!",
                for_admin=True,
                link=f"/admin/store/order/{order.id}/change/"
            )

            # Cart items ko Order Items me shift karo aur specific variant ka stock kam karo
            for item in cart_items:
                # Agar variant mapped hai toh uski selling price hi order billing me jayegi
                final_price = item.variant.selling_price if item.variant else item.product.selling_price
                
                # Note: Agar aapne OrderItem model me 'variant' field add kiya hai toh 'variant=item.variant' bhi dalo
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    price=final_price,
                    quantity=item.quantity
                )
                
                # Stock Minus Logic from Variant Table
                if item.variant:
                    variant = item.variant
                    variant.stock_quantity -= item.quantity
                    variant.total_sold += item.quantity
                    variant.save()
                    
                    # Back-up safety for main product overall counter
                    product = item.product
                    product.total_sold += item.quantity
                    product.save()
                else:
                    product = item.product
                    product.stock_quantity -= item.quantity
                    product.total_sold += item.quantity
                    product.save()

            cart_items.delete() 
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


# --- 2. Thermal Receipt (Updated: No GST) ---
def order_receipt_pdf(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    
    # HTML template me humne loop 'items' par chalaya tha: {% for item in items %}
    # Isliye yahan variable ka naam 'items' rakhna jaruri hai
    items = OrderItem.objects.filter(order=order) 
    
    # --- GST CALCULATION REMOVED ---
    # Ab hume alag se tax calculate karne ki jarurat nahi hai.
    # HTML me hum seedha order.total_amount dikha rahe hain.

    context = {
        'order': order,
        'items': items,  # HTML ke saath match karne ke liye key 'items' rakhi hai
        'today': datetime.date.today(),
    }
    
    # Template ka naam wahi rakhna jo tumne banaya hai (invoice.html ya receipt_pdf.html)
    return render_to_pdf('invoice.html', context)

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


def product_detail(request, product_id):
    # Current product ko fetch karein
    product = get_object_or_404(Product, id=product_id)
    
    # Is product ke saare active variants (weight ya color) nikalo
    variants = product.variants.filter(is_active=True)
    
    # Related Products: Same category ke baaki items (current product ko chhod kar)
    # .exclude(id=product.id) se vahi product dobara suggestion me nahi dikhega
    # related_products = Product.objects.filter(category=product.category, is_active=True).exclude(id=product.id)[:4]
    
    # product_detail view ke andar jahan related_products nikalte ho:
    related_products = Product.objects.filter(category=product.category).exclude(id=product.id)[:4]

# 👇 YE LOGIC ADD KARO: Agar related products khali hain, toh koi bhi random 4 products utha lo
    if not related_products.exists():
        related_products = Product.objects.exclude(id=product.id).order_by('?')[:4]

    context = {
        'product': product,
        'variants': variants,
        'related_products': related_products,
    }
    return render(request, 'product_detail.html', context)



# api code start from here 
# 1. API to get all categories
@api_view(['GET'])
def api_category_list(request):
    categories = Category.objects.all()
    serializer = CategorySerializer(categories, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

# 2. API to get all products (with search and category filter built-in)
@api_view(['GET'])
def api_product_list(request):
    products = Product.objects.all()
    
    # Flutter developer agar filter ya search bhejna chahe:
    category_id = request.GET.get('category')
    search_query = request.GET.get('search')
    
    if category_id:
        products = products.filter(category_id=category_id)
        
    if search_query:
        products = products.filter(name__icontains=search_query)
        
    # Serializer ko data denge aur ye nested variants ke sath JSON bana dega
    serializer = ProductSerializer(products, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
def api_add_to_cart(request):
    # App developer JSON ya form-data me product_id aur variant_id bhejega
    product_id = request.data.get('product_id')
    variant_id = request.data.get('variant_id')
    
    try:
        quantity = int(request.data.get('quantity', 1))
    except (ValueError, TypeError):
        quantity = 1

    if not product_id or not variant_id:
        return Response({'status': 'error', 'message': 'product_id aur variant_id dono zaroori hain!'}, status=status.HTTP_400_BAD_REQUEST)

    product = get_object_or_404(Product, id=product_id)
    variant = get_object_or_404(ProductVariant, id=variant_id, product=product)

    # Cart session handle (jaise normal view me karte the)
    try:
        cart = Cart.objects.get(cart_id=_cart_id(request))
    except Cart.DoesNotExist:
        cart = Cart.objects.create(cart_id=_cart_id(request))
    cart.save()

    # CartItem logic
    try:
        cart_item = CartItem.objects.get(product=product, variant=variant, cart=cart)
        if (cart_item.quantity + quantity) <= variant.stock_quantity:
            cart_item.quantity += quantity
            cart_item.save()
        else:
            return Response({'status': 'error', 'message': f'Stock limited! Sirf {variant.stock_quantity} pieces bache hain.'}, status=status.HTTP_400_BAD_REQUEST)
    except CartItem.DoesNotExist:
        if quantity <= variant.stock_quantity:
            cart_item = CartItem.objects.create(
                product=product, variant=variant, quantity=quantity, cart=cart
            )
            cart_item.save()
        else:
            return Response({'status': 'error', 'message': 'Out of Stock!'}, status=status.HTTP_400_BAD_REQUEST)

    # Naya total cart count nikalenge
    total_qty_dict = CartItem.objects.filter(cart=cart).aggregate(total_qty=Sum('quantity'))
    cart_count = total_qty_dict['total_qty'] or 0

    return Response({
        'status': 'success',
        'message': f'{product.name} cart me add ho gaya!',
        'cart_count': cart_count
    }, status=status.HTTP_200_OK)


# 1. GET API: Cart ke saare items aur Total Bill dikhane ke liye
@api_view(['GET'])
def api_cart_view(request):
    try:
        cart = Cart.objects.get(cart_id=_cart_id(request))
        cart_items = CartItem.objects.filter(cart=cart)
    except Cart.DoesNotExist:
        return Response({
            'cart_items': [],
            'total_price': 0,
            'cart_count': 0
        }, status=status.HTTP_200_OK)

    # Saare items ko serialize karenge
    serializer = CartItemSerializer(cart_items, many=True)
    
    # Poore cart ka Total Bill nikalenge
    total_price = sum(item.variant.selling_price * item.quantity for item in cart_items)
    cart_count = sum(item.quantity for item in cart_items)

    return Response({
        'cart_items': serializer.data,
        'total_price': total_price,
        'cart_count': cart_count
    }, status=status.HTTP_200_OK)


# 2. POST API: Cart se quantity kam karne ya delete karne ke liye
@api_view(['POST'])
def api_remove_from_cart(request):
    product_id = request.data.get('product_id')
    variant_id = request.data.get('variant_id')

    if not product_id or not variant_id:
        return Response({'status': 'error', 'message': 'product_id aur variant_id dono zaroori hain!'}, status=status.HTTP_400_BAD_REQUEST)

    product = get_object_or_404(Product, id=product_id)
    variant = get_object_or_404(ProductVariant, id=variant_id, product=product)
    
    try:
        cart = Cart.objects.get(cart_id=_cart_id(request))
        cart_item = CartItem.objects.get(product=product, variant=variant, cart=cart)
        
        # Agar quantity 1 se zyada hai toh kam karo, nahi toh poora delete kar do
        if cart_item.quantity > 1:
            cart_item.quantity -= 1
            cart_item.save()
            message = f"{product.name} ki quantity kam kar di gayi."
        else:
            cart_item.delete()
            message = f"{product.name} ko cart se hata diya gaya."
            
    except (Cart.DoesNotExist, CartItem.DoesNotExist):
        return Response({'status': 'error', 'message': 'Item cart me nahi mila!'}, status=status.HTTP_404_NOT_FOUND)

    # Naya total count aur price nikal kar bhejenge real-time update ke liye
    cart_items = CartItem.objects.filter(cart=cart)
    total_price = sum(item.variant.selling_price * item.quantity for item in cart_items)
    cart_count = sum(item.quantity for item in cart_items)

    return Response({
        'status': 'success',
        'message': message,
        'total_price': total_price,
        'cart_count': cart_count
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
def api_place_order(request):
    try:
        cart = Cart.objects.get(cart_id=_cart_id(request))
        cart_items = CartItem.objects.filter(cart=cart)
    except Cart.DoesNotExist:
        return Response({'status': 'error', 'message': 'Cart nahi mila!'}, status=status.HTTP_404_NOT_FOUND)

    if not cart_items.exists():
        return Response({'status': 'error', 'message': 'Apka cart khali hai!'}, status=status.HTTP_400_BAD_REQUEST)

    customer_name = request.data.get('customer_name')
    customer_phone = request.data.get('customer_phone')
    address_details = request.data.get('address_details')
    area = request.data.get('area') 

    if not customer_name or not customer_phone or not address_details:
        return Response({'status': 'error', 'message': 'Name, Phone, aur Address zaroori hain!'}, status=status.HTTP_400_BAD_REQUEST)

    total_price = sum(item.variant.selling_price * item.quantity for item in cart_items)
    tax = 0 
    grand_total = total_price + tax

    # 🛒 Order Table me data save
    order = Order.objects.create(
    customer_name=customer_name,
    customer_phone=customer_phone,
    address_details=address_details,
    area=area,
    total_amount=grand_total,  
    status=True
    )
    
    # Items transfer aur stock reduction
    for item in cart_items:
        OrderItem.objects.create(
        order=order,
        product=item.product,
        variant=item.variant,
        quantity=item.quantity,
        product_price=item.variant.price
    )
        
        variant = item.variant
        variant.stock_quantity -= item.quantity
        variant.save()

    request.session['customer_phone'] = customer_phone
    cart_items.delete()

    return Response({
        'status': 'success',
        'message': 'Mubarak ho! Order place ho gaya hai. 🎉',
        'order_id': order.id,
        'grand_total': grand_total
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
def api_my_orders(request):
    orders = []
    phone = request.GET.get('phone')

    # 1. PRIORITY 1: Agar URL me saaf-saaf phone number bheja hai (Testing aur Guest user ke liye best)
    if phone:
        orders = Order.objects.filter(customer_phone=phone).order_by('-id')
        
    # 2. PRIORITY 2: Agar URL me phone nahi hai par user logged in hai
    elif request.user.is_authenticated:
        orders = Order.objects.filter(user=request.user).order_by('-id')
        
    # 3. PRIORITY 3: Agar dono nahi hai to browser session se phone uthao
    else:
        phone = request.session.get('customer_phone')
        if phone:
            orders = Order.objects.filter(customer_phone=phone).order_by('-id')
        else:
            return Response({
                'status': 'error', 
                'message': 'Phone number ya user authentication zaroori hai!'
            }, status=status.HTTP_400_BAD_REQUEST)

    # Data ko serialize karke return karenge
    serializer = OrderHistorySerializer(orders, many=True, context={'request': request})
    
    return Response({
        'status': 'success',
        'orders_count': orders.count(),
        'orders': serializer.data
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
def api_product_detail(request, product_id):
    try:
        product = Product.objects.get(id=product_id)
        # Tumhara ProductSerializer is single product ko nested variants ke sath parse kar dega
        serializer = ProductSerializer(product)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Product.DoesNotExist:
        return Response({
            'status': 'error', 
            'message': 'Product nahi mila!'
        }, status=status.HTTP_404_NOT_FOUND)    
    
@api_view(['GET'])
def api_product_search(request):
    # Flutter app se query parameter uthayenge (Jaise: /api/search/?q=namkeen)
    query = request.GET.get('q', '').strip()
    
    if query:
        # 🎯 SUPER SEARCH: Name, Description, aur Category Name teeno me ek sath dhoondo
        products = Product.objects.filter(
            Q(name__icontains=query) | 
            Q(description__icontains=query) |
            Q(category__name__icontains=query)
        ).distinct() # distinct() se duplicate products nahi aayenge
    else:
        # Agar user ne kuch type nahi kiya, toh khali list bhej do
        products = Product.objects.none()
        
    # Hamara wahi naya dynamic serializer use karenge jo variants bhi nikal ke dega
    serializer = ProductSerializer(products, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)    