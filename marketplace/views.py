"""
AgroMentor 360 - Marketplace Views
Product listings, orders, and reviews endpoints
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q, Avg, Count
from django.utils import timezone

from .models import Product, Order, OrderItem, Review
from .serializers import (
    ProductSerializer,
    ProductDetailSerializer,
    OrderSerializer,
    OrderDetailSerializer,
    ReviewSerializer
)


@api_view(['GET'])
@permission_classes([AllowAny])
def product_list(request):
    """List all products"""
    products = Product.objects.filter(
        status='active',
        quantity__gt=0
    )
    
    # Filter by category
    category = request.query_params.get('category')
    if category:
        products = products.filter(category=category)
    
    # Filter by location
    location = request.query_params.get('location')
    if location:
        products = products.filter(location__icontains=location)
    
    # Search
    search = request.query_params.get('search')
    if search:
        products = products.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search)
        )
    
    # Sort
    sort_by = request.query_params.get('sort', '-created_at')
    products = products.order_by(sort_by)
    
    serializer = ProductSerializer(products, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def product_detail(request, product_id):
    """Get product details"""
    product = get_object_or_404(Product, id=product_id)
    serializer = ProductDetailSerializer(product)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_product(request):
    """Create a new product listing"""
    serializer = ProductSerializer(data=request.data)
    
    if serializer.is_valid():
        product = serializer.save(seller=request.user)
        return Response(
            ProductDetailSerializer(product).data,
            status=status.HTTP_201_CREATED
        )
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_product(request, product_id):
    """Update product listing"""
    product = get_object_or_404(Product, id=product_id, seller=request.user)
    
    serializer = ProductSerializer(product, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(ProductDetailSerializer(product).data)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_product(request, product_id):
    """Delete product listing"""
    product = get_object_or_404(Product, id=product_id, seller=request.user)
    product.delete()
    return Response(
        {'message': 'Product deleted successfully'},
        status=status.HTTP_204_NO_CONTENT
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_products(request):
    """Get user's product listings"""
    products = Product.objects.filter(seller=request.user).order_by('-created_at')
    serializer = ProductSerializer(products, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_order(request):
    """Create a new order"""
    items = request.data.get('items', [])
    
    if not items:
        return Response(
            {'error': 'Order items required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Calculate total
    total_amount = 0
    order_items = []
    
    for item_data in items:
        product = get_object_or_404(Product, id=item_data['product_id'])
        quantity = item_data['quantity']
        
        if product.quantity_available < quantity:
            return Response(
                {'error': f'Insufficient stock for {product.name}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        subtotal = product.price_agrocoin * quantity
        total_amount += subtotal
        
        order_items.append({
            'product': product,
            'quantity': quantity,
            'price': product.price_agrocoin,
            'subtotal': subtotal
        })
    
    # Create order
    order = Order.objects.create(
        buyer=request.user,
        total_amount=total_amount,
        shipping_address=request.data.get('shipping_address', ''),
        phone_number=request.data.get('phone_number', request.user.phone_number)
    )
    
    # Create order items and update stock
    for item in order_items:
        OrderItem.objects.create(
            order=order,
            product=item['product'],
            quantity=item['quantity'],
            price=item['price'],
            subtotal=item['subtotal']
        )
        
        # Reduce stock
        item['product'].quantity -= item['quantity']
        item['product'].save(update_fields=['quantity'])
    
    serializer = OrderDetailSerializer(order)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def order_list(request):
    """Get user's orders"""
    orders = Order.objects.filter(buyer=request.user).order_by('-created_at')
    serializer = OrderSerializer(orders, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def order_detail(request, order_id):
    """Get order details"""
    order = get_object_or_404(Order, id=order_id, buyer=request.user)
    serializer = OrderDetailSerializer(order)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_order(request, order_id):
    """Cancel an order"""
    order = get_object_or_404(Order, id=order_id, buyer=request.user)
    
    if order.status not in ['pending', 'confirmed']:
        return Response(
            {'error': 'Cannot cancel order in current status'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Restore stock
    for item in order.items.all():
        item.product.quantity += item.quantity
        item.product.save(update_fields=['quantity'])
    
    order.status = 'cancelled'
    order.save()
    
    return Response({
        'message': 'Order cancelled successfully',
        'order': OrderDetailSerializer(order).data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def seller_orders(request):
    """Get orders for seller's products"""
    # Get all orders containing seller's products
    order_items = OrderItem.objects.filter(
        product__seller=request.user
    ).select_related('order')
    
    orders = Order.objects.filter(
        id__in=order_items.values_list('order_id', flat=True)
    ).distinct().order_by('-created_at')
    
    serializer = OrderSerializer(orders, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_order_status(request, order_id):
    """Update order status (for sellers)"""
    new_status = request.data.get('status')
    
    if new_status not in ['confirmed', 'shipped', 'delivered']:
        return Response(
            {'error': 'Invalid status'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    order = get_object_or_404(Order, id=order_id)
    
    # Verify seller owns products in this order
    if not order.items.filter(product__seller=request.user).exists():
        return Response(
            {'error': 'Unauthorized'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    order.status = new_status
    order.save()
    
    return Response({
        'message': 'Order status updated',
        'order': OrderDetailSerializer(order).data
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_review(request, product_id):
    """Create a product review"""
    product = get_object_or_404(Product, id=product_id)
    
    # Check if user has purchased this product
    has_purchased = OrderItem.objects.filter(
        order__buyer=request.user,
        product=product,
        order__status='delivered'
    ).exists()
    
    if not has_purchased:
        return Response(
            {'error': 'You must purchase this product before reviewing'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Check if already reviewed
    if Review.objects.filter(product=product, user=request.user).exists():
        return Response(
            {'error': 'You have already reviewed this product'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    serializer = ReviewSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(product=product, user=request.user)
        
        # Update product rating
        avg_rating = product.reviews.aggregate(Avg('rating'))['rating__avg']
        product.average_rating = avg_rating
        product.save(update_fields=['rating'])
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([AllowAny])
def product_reviews(request, product_id):
    """Get product reviews"""
    product = get_object_or_404(Product, id=product_id)
    reviews = product.reviews.order_by('-created_at')
    serializer = ReviewSerializer(reviews, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def marketplace_stats(request):
    """Get marketplace statistics"""
    stats = {
        'total_products': Product.objects.filter(status='active').count(),
        'total_orders': Order.objects.count(),
        'total_reviews': Review.objects.count(),
        'categories': Product.objects.values('category').annotate(
            count=Count('id')
        ).order_by('-count')[:5],
        'top_rated': ProductSerializer(
            Product.objects.filter(status='active').order_by('-rating')[:5],
            many=True
        ).data
    }
    
    return Response(stats)