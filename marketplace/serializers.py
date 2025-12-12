from rest_framework import serializers
from .models import Product, Order, OrderItem, Review
from accounts.serializers import UserSerializer # Assuming you have this

# ----------------------------------------------------------------
# Review Serializers
# ----------------------------------------------------------------

class ReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_avatar = serializers.ImageField(source='user.profile.avatar', read_only=True)
    
    class Meta: #type:ignore
        model = Review
        fields = [
            'id', 'user', 'user_name', 'user_avatar', 
            'rating', 'comment', 'created_at'
        ]
        read_only_fields = ['id', 'user', 'created_at']


# ----------------------------------------------------------------
# Product Serializers
# ----------------------------------------------------------------

class ProductSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for lists and cards
    """
    seller_name = serializers.CharField(source='seller.get_full_name', read_only=True)
    seller_location = serializers.CharField(source='location_city', read_only=True)
    
    class Meta: #type:ignore
        model = Product
        fields = [
            'id', 'name', 'category', 'price', 'price_agrocoin',
            'quantity', 'unit', 'primary_image', 
            'seller_name', 'seller_location', 'rating', 
            'status', 'created_at'
        ]
        read_only_fields = ['id', 'seller', 'rating', 'created_at']


class ProductDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer including description, reviews, and seller info
    """
    seller = UserSerializer(read_only=True)
    reviews = ReviewSerializer(many=True, read_only=True)
    review_count = serializers.IntegerField(source='reviews.count', read_only=True)
    
    class Meta: #type:ignore
        model = Product
        fields = [
            'id', 'name', 'category', 'description',
            'price', 'price_agrocoin', 
            'quantity', 'unit', 'minimum_order',
            'primary_image', 'additional_images',
            'organic_certified', 'quality_grade',
            'harvest_date', 'location_city', 'location_state',
            'delivery_available', 'pickup_available', 'delivery_fee',
            'seller', 'rating', 'reviews', 'review_count',
            'status', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'seller', 'rating', 'created_at', 'updated_at']


# ----------------------------------------------------------------
# Order Serializers
# ----------------------------------------------------------------

class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_image = serializers.ImageField(source='product.primary_image', read_only=True)
    
    class Meta: #type:ignore
        model = OrderItem
        fields = [
            'id', 'product', 'product_name', 'product_image',
            'quantity', 'price', 'subtotal'
        ]


class OrderSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for order history lists
    """
    item_count = serializers.IntegerField(source='items.count', read_only=True)
    first_item_name = serializers.SerializerMethodField()
    
    class Meta: #type:ignore
        model = Order
        fields = [
            'id', 'order_number', 'status', 'total_amount', 
            'created_at', 'item_count', 'first_item_name'
        ]
        read_only_fields = ['id', 'order_number', 'created_at']

    def get_first_item_name(self, obj):
        first_item = obj.items.first()
        if first_item and first_item.product:
            return first_item.product.name
        return "Unknown Item"


class OrderDetailSerializer(serializers.ModelSerializer):
    """
    Full order details including all items and buyer info
    """
    items = OrderItemSerializer(many=True, read_only=True)
    buyer_name = serializers.CharField(source='buyer.get_full_name', read_only=True)
    buyer_phone = serializers.CharField(source='buyer.phone_number', read_only=True)
    
    class Meta: #type:ignore
        model = Order
        fields = [
            'id', 'order_number', 'status', 
            'buyer', 'buyer_name', 'buyer_phone',
            'items', 'total_amount', 
            'shipping_address', 'phone_number', # Contact phone for this specific order
            'tracking_number', 'notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'order_number', 'buyer', 'total_amount', 'created_at']