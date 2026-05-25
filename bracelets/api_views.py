from rest_framework import viewsets, permissions
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from .models import Bracelet, Category, Product, CartItem
from .serializers import BraceletSerializer, CategorySerializer, ProductSerializer, CartItemSerializer


class BraceletViewSet(viewsets.ModelViewSet):
    queryset = Bracelet.objects.all()
    serializer_class = BraceletSerializer


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.select_related('category').all()
    serializer_class = ProductSerializer


class CartItemViewSet(viewsets.ModelViewSet):
    queryset = CartItem.objects.select_related('bracelet').all()
    serializer_class = CartItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        bracelet_id = self.request.data.get('bracelet')
        if bracelet_id:
            bracelet = get_object_or_404(Bracelet, pk=bracelet_id)
            cart_item, created = CartItem.objects.get_or_create(
                user=self.request.user,
                bracelet=bracelet,
                defaults={'quantity': 1}
            )
            if not created:
                cart_item.quantity += 1
                cart_item.save(update_fields=['quantity', 'updated_at'])
                serializer.instance = cart_item
        else:
            serializer.save(user=self.request.user)
