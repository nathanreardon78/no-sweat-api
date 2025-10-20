from rest_framework import serializers
from .models import Order

class CartItemSerializer(serializers.Serializer):
    name = serializers.CharField()
    size = serializers.CharField()
    quantity = serializers.IntegerField(min_value=1)

class CheckoutRequestSerializer(serializers.Serializer):
    items = CartItemSerializer(many=True)

class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = "__all__"
