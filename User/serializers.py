from rest_framework import serializers
from User.models import *

class UserRegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdminTempUser
        fields = ['username', 'email', 'phone', 'password','photo']

    def validate_photo(self, value):

        # Image size validation (5MB)
        if value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError("Image size exceeds 5MB limit.")

        return value
    def validate_phone(self, value):

        if not value.isdigit():
            raise serializers.ValidationError("Phone number must contain only numbers.")
        if len(value) != 10:
            raise serializers.ValidationError("Phone number must be exactly 10 digits.")
        return value

class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User_Master
        fields = ['username', 'phone', 'photo']

    def validate_phone(self, value):

        if not value.isdigit():
            raise serializers.ValidationError("Phone number must contain only numbers.")

        if len(value) != 10:
            raise serializers.ValidationError("Phone number must be exactly 10 digits.")

        return value
    def validate_photo(self, value):

        # Image size validation (5MB)
        if value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError("Image size exceeds 5MB limit.")

        return value
    
class MediaFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = MediaFile

        fields = [
            'id',
            'user',
            'file_type',
            'file',
            'file_url',
            'file_name',
            'created_at',
            'updated_at'
        ]
    
class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.category_name',read_only=True)
    class Meta:
        model = Product

        fields = [
            'id',
            'product_name',
            'description',
            'price',
            'quantity',
            'category',
            'category_name',
            'product_image',
            'product_image_url',
            'status',
            'created_at',
            'updated_at'
        ]