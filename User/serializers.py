from rest_framework import serializers
from User.models import *

class AdminRegisterSerializer(serializers.ModelSerializer):

    class Meta:
        model = AdminTempUser
        fields = ['username', 'email', 'phone', 'password','photo']

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
