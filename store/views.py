# api code start from line number 630 here 
from django.contrib.admin.views.decorators import staff_member_required
from .models import Product, Order, OrderItem, Category, Banner, DeliveryZone
import datetime
import os
from django.conf import settings
from django.shortcuts import redirect, get_object_or_404, render
from .forms import OrderForm
from django.db.models import Q, Sum, Count
from .utils import render_to_pdf 
from django.db import transaction
import csv # Excel export ke liye
from django.http import HttpResponse
from django.db.models.functions import TruncMonth
from .models import Notification, Cart, CartItem # notification ke liye h 
from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
import json
from .utils import is_location_deliverable
from django.contrib import messages

# api vale 
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .serializers import ProductSerializer, CategorySerializer, CartItemSerializer, OrderHistorySerializer
from .models import Product, ProductVariant, Cart, CartItem, Category


# views.py me admin_dashboard function ko update karein:

@staff_member_required
def admin_dashboard(request):
    total_products = Product.objects.count()
    total_orders = Order.objects.count()
    total_stock = Product.objects.aggregate(Sum('stock_quantity'))['stock_quantity__sum'] or 0
    
    orders = Order.objects.all().order_by('-id')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    search_query = request.GET.get('search_query')
    if search_query:
        orders = orders.filter(
            Q(customer_name__icontains=search_query) | 
            Q(customer_phone__icontains=search_query)
        )

    if start_date and end_date:
        orders = orders.filter(date__range=[start_date, end_date])

    pending_orders = Order.objects.filter(status=False, is_cancelled=False).count()
    completed_orders = Order.objects.filter(status=True).count()

    total_sales = Order.objects.filter(status=True).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    recent_orders = Order.objects.all().order_by('-id')[:5]

    # 📊 DYNAMIC GRAPH LOGIC (Last 6 Months Real-time Sales)
    today = datetime.date.today()
    months = []
    sales = []

    for i in range(5, -1, -1):
        # Current month se picche 6 mahine calculate karne ke liye
        year = today.year
        month = today.month - i
        if month <= 0:
            month += 12
            year -= 1
        
        date_obj = datetime.date(year, month, 1)
        month_name = date_obj.strftime('%b %Y') # Format: Jan 2026
        months.append(month_name)
        
        monthly_sales = Order.objects.filter(
            date__year=year, 
            date__month=month, 
            status=True
        ).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        
        sales.append(int(monthly_sales))

    admin_notifs = Notification.objects.filter(for_admin=True).order_by('-date')[:5]

    context = {
        'total_products': total_products,
        'orders': orders,
        'total_orders': total_orders,
        'total_stock': total_stock,
        'months': json.dumps(months), # JS array ke liye JSON convert
        'sales': json.dumps(sales),   # JS array ke liye JSON convert
        'pending_orders': pending_orders,
        'completed_orders': completed_orders,
        'total_sales': total_sales,
        'recent_orders': recent_orders,
        'admin_notifs': admin_notifs, 
    }
    return render(request, 'admin_dashboard.html', context)


def home(request):
    products = Product.objects.all()
    categories = Category.objects.all()

    category_id = request.GET.get('category')
    if category_id:
        products = products.filter(category_id=category_id)

    search_query = request.GET.get('search')
    if search_query:
        products = products.filter(Q(name__icontains=search_query) | Q(description__icontains=search_query))

    banners = Banner.objects.filter(is_active=True)

    context = {
        'products': products,
        'categories': categories,
        'banners': banners,
    }
    return render(request, 'index.html', context)


def _cart_id(request):
    cart = request.session.session_key
    if not cart:
        cart = request.session.create()
    return cart


# =========================================================================
# 1. ADD TO CART (Variant Supported)
# =========================================================================
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    variant_id = request.GET.get('variant_id')
    
    if not variant_id:
        first_variant = ProductVariant.objects.filter(product=product, is_active=True).first()
        if first_variant:
            variant_id = first_variant.id
        else:
            return JsonResponse({'status': 'error', 'message': 'Is product ka koi variant available nahi hai!'})

    variant = get_object_or_404(ProductVariant, id=variant_id, product=product)

    try:
        quantity = int(request.GET.get('quantity', 1))
        if quantity <= 0: quantity = 1
    except ValueError:
        quantity = 1

    try:
        cart = Cart.objects.get(cart_id=_cart_id(request))
    except Cart.DoesNotExist:
        cart = Cart.objects.create(cart_id=_cart_id(request))
    cart.save()

    try:
        cart_item = CartItem.objects.get(product=product, variant=variant, cart=cart)
        total_requested = cart_item.quantity + quantity
        
        if total_requested <= variant.stock_quantity:
            cart_item.quantity = total_requested
            cart_item.save()
        else:
            return JsonResponse({
                'status': 'error', 
                'message': f'Stock Limit Exceeded! Maximum {variant.stock_quantity} pieces hi available hain.'
            })
            
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
            return JsonResponse({'status': 'error', 'message': f'Out of Stock! Sirf {variant.stock_quantity} bache hain.'})
    
    total_qty_dict = CartItem.objects.filter(cart=cart).aggregate(total_qty=Sum('quantity'))
    cart_count = total_qty_dict['total_qty'] or 0

    return JsonResponse({
        'status': 'success', 
        'message': f'{product.name} ({variant.weight_or_size or variant.color or ""}) cart me add ho gaya! 🛒', 
        'cart_count': cart_count
    })


# =========================================================================
# 2. CART DETAILS
# =========================================================================
def cart_details(request):
    total_price = 0
    total_items = 0
    cart_items = []

    try:
        cart = Cart.objects.get(cart_id=_cart_id(request))
        cart_items = CartItem.objects.filter(cart=cart, is_active=True)
        
        for cart_item in cart_items:
            if cart_item.variant:
                item_price = cart_item.variant.selling_price
            else:
                item_price = cart_item.product.selling_price
                
            item_total = item_price * cart_item.quantity
            cart_item.item_total_price = item_total
            
            total_price += item_total
            total_items += cart_item.quantity

    except ObjectDoesNotExist:
        pass 

    if total_price > 0 and total_price < 1000:
        delivery_charge = 15
    else:
        delivery_charge = 0

    grand_total = total_price + delivery_charge

    context = {
        'cart_items': cart_items,
        'total_price': total_price,
        'total_items': total_items,
        'delivery_charge': delivery_charge,
        'grand_total': grand_total,
    }
    return render(request, 'cart.html', context)


# =========================================================================
# 3. UPDATE CART
# =========================================================================
def update_cart(request, product_id, action):
    variant_id = request.GET.get('variant_id') 
    product = get_object_or_404(Product, id=product_id)
    cart = Cart.objects.get(cart_id=_cart_id(request))
    
    if variant_id:
        cart_item = get_object_or_404(CartItem, product=product, variant_id=variant_id, cart=cart)
        max_stock = cart_item.variant.stock_quantity
    else:
        cart_item = CartItem.objects.filter(product=product, cart=cart).first()
        max_stock = cart_item.variant.stock_quantity if (cart_item and cart_item.variant) else product.stock_quantity

    if not cart_item:
        return redirect('cart')

    if action == 'plus':
        if cart_item.quantity < max_stock:
            cart_item.quantity += 1
            cart_item.save()
        else:
            messages.warning(request, f"Sorry, is variant ke sirf {max_stock} pieces hi stock me hain!")
    
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
# 4. CHECKOUT & STOCK DECREMENT (FIXED VARIANT LINKING)
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

    total_price = 0
    for item in cart_items:
        if item.variant:
            total_price += (item.variant.selling_price * item.quantity)
        else:
            total_price += (item.product.selling_price * item.quantity)

    if total_price > 0 and total_price < 1000:
        delivery_charge = 15
    else:
        delivery_charge = 0

    grand_total = total_price + delivery_charge

    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            if request.user.is_authenticated:
                order.user = request.user
            
            order.total_amount = grand_total
            order.save()
            request.session['customer_phone'] = order.customer_phone

            Notification.objects.create(
                title="🎉 New Order Received!",
                message=f"{order.customer_name} ne order kiya hai (₹{order.total_amount}). Jaldi pack karo!",
                for_admin=True,
                link=f"/admin/store/order/{order.id}/change/"
            )

            for item in cart_items:
                final_price = item.variant.selling_price if item.variant else item.product.selling_price
                
                # 🔥 FIX HERE: Added variant=item.variant so cancellation works perfectly!
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    variant=item.variant,
                    price=final_price,
                    quantity=item.quantity
                )
                
                if item.variant:
                    variant = item.variant
                    variant.stock_quantity -= item.quantity
                    variant.total_sold += item.quantity
                    variant.save()
                    
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
        'total_price': total_price,
        'delivery_charge': delivery_charge,
        'grand_total': grand_total
    }
    return render(request, 'checkout.html', context)


def my_orders(request):
    customer_info = {}
    orders = []

    if request.user.is_authenticated:
        orders = Order.objects.filter(user=request.user).order_by('-id')
        customer_info = {
            'name': request.user.first_name + ' ' + request.user.last_name,
            'phone': request.user.username,
            'address': 'Saved Address'
        }
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


def mark_order_received(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    order.status = True
    order.save()
    
    messages.success(request, "Shukriya! Order Complete ho gaya. ✅")
    return redirect('my_orders')    


def order_invoice(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    items = OrderItem.objects.filter(order=order)

    items_total = sum(item.get_cost() for item in items)

    if order.total_amount > items_total:
        delivery_charge = order.total_amount - items_total
    else:
        delivery_charge = 0

    # Windows Path Fix: Backslash ko Forwardslash me convert kar rahe hain
    raw_font_path = os.path.join(settings.BASE_DIR, 'static', 'fonts', 'NotoSans.ttf')
    font_path = raw_font_path.replace('\\', '/')

    context = {
        'order': order,
        'items': items,
        'items_total': items_total,
        'delivery_charge': delivery_charge,
        'today': datetime.date.today(),
        'font_path': font_path,
    }
    return render_to_pdf('invoice.html', context)


def packing_list(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    items = OrderItem.objects.filter(order=order)
    
    context = {
        'order': order,
        'items': items,
    }
    return render_to_pdf('packing_list.html', context)


def export_orders_xls(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="orders_report.csv"'

    writer = csv.writer(response)
    writer.writerow(['Order ID', 'Customer Name', 'Phone', 'Date', 'Total Amount', 'Status'])

    orders = Order.objects.all().values_list('id', 'customer_name', 'customer_phone', 'date', 'total_amount', 'status')
    for order in orders:
        status = "Delivered" if order[5] else "Pending"
        writer.writerow([order[0], order[1], order[2], order[3], order[4], status])

    return response    


def notifications(request):
    phone = request.session.get('customer_phone')
    
    notifs = Notification.objects.filter(
        (Q(for_user_phone__isnull=True) | Q(for_user_phone=phone)) & Q(for_admin=False)
    ).order_by('-date')

    return render(request, 'notifications.html', {'notifs': notifs})    


@staff_member_required
def admin_toggle_status(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    order.status = not order.status
    order.save()
    
    status_msg = "Completed" if order.status else "Pending"
    messages.success(request, f"Order #{order.id} is now {status_msg}")
    
    return redirect('admin_dashboard')


def order_receipt_pdf(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    items = OrderItem.objects.filter(order=order) 

    context = {
        'order': order,
        'items': items,
        'today': datetime.date.today(),
    }
    return render_to_pdf('invoice.html', context)


@staff_member_required
def customer_insights(request):
    query = request.GET.get('q')
    users_data = []
    
    if query:
        users = User.objects.filter(
            username__icontains=query
        ) | User.objects.filter(
            first_name__icontains=query
        ) | User.objects.filter(
            email__icontains=query
        )
        
        for user in users:
            total_orders = Order.objects.filter(user=user).count()
            total_spent = Order.objects.filter(user=user).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
            
            users_data.append({
                'id': user.id,
                'username': user.username,
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
    product = get_object_or_404(Product, id=product_id)
    variants = product.variants.filter(is_active=True)
    
    related_products = Product.objects.filter(category=product.category).exclude(id=product.id)[:4]

    if not related_products.exists():
        related_products = Product.objects.exclude(id=product.id).order_by('?')[:4]

    context = {
        'product': product,
        'variants': variants,
        'related_products': related_products,
    }
    return render(request, 'product_detail.html', context)


def privacy_policy(request):
    return render(request, 'privacy_policy.html')

def terms_conditions(request):
    return render(request, 'terms_conditions.html')    


# =========================================================================
# 5. ORDER CANCELLATION & STOCK RESTORATION
# =========================================================================
def cancel_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    
    if not order.status and not order.is_cancelled:
        with transaction.atomic():
            order.is_cancelled = True
            order.save()
            
            for item in order.orderitem_set.all():
                if item.variant:
                    item.variant.stock_quantity += item.quantity
                    item.variant.save()
                elif item.product:
                    first_variant = item.product.variants.filter(is_active=True).first()
                    if first_variant:
                        first_variant.stock_quantity += item.quantity
                        first_variant.save()
                    else:
                        item.product.stock_quantity += item.quantity
                        item.product.save()

        messages.success(request, f"Order #{order.id} cancel ho gaya hai aur stock restore kar diya gaya hai. 🔄")
    else:
        messages.error(request, "Is order ko cancel nahi kiya ja sakta.")
        
    phone = request.GET.get('phone', '')
    if phone:
        return redirect(f'/my-orders/?phone={phone}')
    return redirect('my_orders')


# =========================================================================
# API CODE STARTS FROM HERE
# =========================================================================

@api_view(['GET'])
def api_category_list(request):
    categories = Category.objects.all()
    serializer = CategorySerializer(categories, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
def api_product_list(request):
    products = Product.objects.all()
    
    category_id = request.GET.get('category')
    search_query = request.GET.get('search')
    
    if category_id:
        products = products.filter(category_id=category_id)
        
    if search_query:
        products = products.filter(name__icontains=search_query)
        
    serializer = ProductSerializer(products, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
def api_add_to_cart(request):
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

    try:
        cart = Cart.objects.get(cart_id=_cart_id(request))
    except Cart.DoesNotExist:
        cart = Cart.objects.create(cart_id=_cart_id(request))
    cart.save()

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

    total_qty_dict = CartItem.objects.filter(cart=cart).aggregate(total_qty=Sum('quantity'))
    cart_count = total_qty_dict['total_qty'] or 0

    return Response({
        'status': 'success',
        'message': f'{product.name} cart me add ho gaya!',
        'cart_count': cart_count
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
def api_cart_view(request):
    try:
        cart = Cart.objects.get(cart_id=_cart_id(request))
        cart_items = CartItem.objects.filter(cart=cart)
    except Cart.DoesNotExist:
        return Response({
            'cart_items': [],
            'total_price': 0,
            'delivery_charge': 0,
            'grand_total': 0,
            'cart_count': 0
        }, status=status.HTTP_200_OK)

    serializer = CartItemSerializer(cart_items, many=True)
    
    total_price = sum(item.variant.selling_price * item.quantity for item in cart_items)
    cart_count = sum(item.quantity for item in cart_items)

    if total_price > 0 and total_price < 1000:
        delivery_charge = 15
    else:
        delivery_charge = 0

    grand_total = total_price + delivery_charge

    return Response({
        'cart_items': serializer.data,
        'total_price': total_price,
        'delivery_charge': delivery_charge,
        'grand_total': grand_total,
        'cart_count': cart_count
    }, status=status.HTTP_200_OK)


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
        
        if cart_item.quantity > 1:
            cart_item.quantity -= 1
            cart_item.save()
            message = f"{product.name} ki quantity kam kar di gayi."
        else:
            cart_item.delete()
            message = f"{product.name} ko cart se hata diya gaya."
            
    except (Cart.DoesNotExist, CartItem.DoesNotExist):
        return Response({'status': 'error', 'message': 'Item cart me nahi mila!'}, status=status.HTTP_404_NOT_FOUND)

    cart_items = CartItem.objects.filter(cart=cart)
    total_price = sum(item.variant.selling_price * item.quantity for item in cart_items)
    cart_count = sum(item.quantity for item in cart_items)

    if total_price > 0 and total_price < 1000:
        delivery_charge = 15
    else:
        delivery_charge = 0

    grand_total = total_price + delivery_charge

    return Response({
        'status': 'success',
        'message': message,
        'total_price': total_price,
        'delivery_charge': delivery_charge,
        'grand_total': grand_total,
        'cart_count': cart_count
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@csrf_exempt
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
    
    if total_price > 0 and total_price < 1000:
        delivery_charge = 15
    else:
        delivery_charge = 0

    grand_total = total_price + delivery_charge

    order = Order.objects.create(
        customer_name=customer_name,
        customer_phone=customer_phone,
        address_details=address_details,
        area=area,
        total_amount=grand_total,  
        status=False
    )
    
    for item in cart_items:
        OrderItem.objects.create(
            order=order,
            product=item.product,
            variant=item.variant,
            quantity=item.quantity,
            price=item.variant.selling_price
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

    if phone:
        orders = Order.objects.filter(customer_phone=phone).order_by('-id')
    elif request.user.is_authenticated:
        orders = Order.objects.filter(user=request.user).order_by('-id')
    else:
        phone = request.session.get('customer_phone')
        if phone:
            orders = Order.objects.filter(customer_phone=phone).order_by('-id')
        else:
            return Response({
                'status': 'error', 
                'message': 'Phone number ya user authentication zaroori hai!'
            }, status=status.HTTP_400_BAD_REQUEST)

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
        serializer = ProductSerializer(product)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Product.DoesNotExist:
        return Response({
            'status': 'error', 
            'message': 'Product nahi mila!'
        }, status=status.HTTP_404_NOT_FOUND)    

    
@api_view(['GET'])
def api_product_search(request):
    query = request.GET.get('q', '').strip()
    
    if query:
        products = Product.objects.filter(
            Q(name__icontains=query) | 
            Q(description__icontains=query) |
            Q(category__name__icontains=query)
        ).distinct()
    else:
        products = Product.objects.none()
        
    serializer = ProductSerializer(products, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)   


def api_legal_urls(request):
    data = {
        "privacy_policy_url": "https://princemart.in/privacy-policy/",
        "terms_conditions_url": "https://princemart.in/terms-conditions/"
    }
    return JsonResponse(data)


# open street map adding lan-lat
def is_location_deliverable(user_lat, user_lng):
    from .models import DeliveryZone
    zones = DeliveryZone.objects.filter(is_active=True)
    
    for zone in zones:
        coords = zone.get_coordinates_list()
        if not coords or len(coords) < 3:
            continue
            
        inside = False
        n = len(coords)
        p1lat, p1lng = float(coords[0]['lat']), float(coords[0]['lng'])
        
        for i in range(n + 1):
            p2lat, p2lng = float(coords[i % n]['lat']), float(coords[i % n]['lng'])
            if user_lat > min(p1lat, p2lat):
                if user_lat <= max(p1lat, p2lat):
                    if user_lng <= max(p1lng, p2lng):
                        if p1lat != p2lat:
                            xinters = (user_lat - p1lat) * (p2lng - p1lng) / (p2lat - p1lat) + p1lng
                        if p1lng == p2lng or user_lng <= xinters:
                            inside = not inside
            p1lat, p1lng = p2lat, p2lng
            
        if inside:
            return True
            
    return False


@csrf_exempt
def check_delivery_availability(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            lat = float(data.get('lat'))
            lng = float(data.get('lng'))

            is_deliverable = is_location_deliverable(lat, lng)

            if is_deliverable:
                return JsonResponse({'available': True, 'message': 'Delivery is available at your location.'})
            else:
                return JsonResponse({'available': False, 'message': 'Sorry, we do not deliver to this location currently.'})
        except Exception as e:
            return JsonResponse({'available': False, 'error': str(e)}, status=400)

    return JsonResponse({'error': 'Invalid request method'}, status=405)