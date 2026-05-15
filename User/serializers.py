import re
from rest_framework import serializers
from User.models import AdminTempUser


class AdminRegisterSerializer(serializers.ModelSerializer):

    class Meta:
        model = AdminTempUser
        fields = ['username', 'email', 'phone', 'password']

    def validate_phone(self, value):

        if not value.isdigit():
            raise serializers.ValidationError("Phone number must contain only numbers.")
        if len(value) != 10:
            raise serializers.ValidationError("Phone number must be exactly 10 digits.")
        return value

    def validate_password(self, value):
        if len(value) < 8:
            raise serializers.ValidationError("Password must be at least 8 characters.")

        if not re.search(r'[A-Z]', value):
            raise serializers.ValidationError("Password must contain at least 1 capital letter.")

        if not re.search(r'[a-z]', value):
            raise serializers.ValidationError("Password must contain at least 1 small letter.")

        if not re.search(r'[0-9]', value):
            raise serializers.ValidationError("Password must contain at least 1 number.")

        if not re.search(r'[@$!%*?&]', value):
            raise serializers.ValidationError("Password must contain at least 1 special character.")
        return value
