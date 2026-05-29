from rest_framework import serializers
from User.models import *

class UserRegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdminTempUser
        fields = ['username', 'email', 'phone', 'password','photo']

        extra_kwargs = {
            'photo': {'required': False}
        }

    def validate_photo(self, value):

        if not value:
            return value

        if value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError(
                "Image size exceeds 5MB limit."
            )

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
    
class CampaignSerializer(serializers.ModelSerializer):

    class Meta:
        model = Campaign
        fields = '__all__'
        read_only_fields =  ['user']


class CampaignUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model = Campaign
        fields =['campaign_name','agent_name','language','voice_gender','voice_type','calling_start_time','calling_end_time','max_retry_attempts','status','calling_end_time','max_retry_attempts','status']



