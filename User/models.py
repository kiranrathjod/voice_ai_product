from django.db import models
from django.contrib.auth.models import AbstractBaseUser,UserManager
from django.contrib.auth.models import PermissionsMixin
from django.utils.timezone import now
import uuid

# this model is store temporary save users data then otp verification after delete data and then create in user master model.
class AdminTempUser(models.Model):
    id = models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    username = models.CharField(max_length=150,null=False)
    email = models.EmailField(null=False)
    phone = models.CharField(max_length=10,null=False)
    password = models.CharField(max_length=255,null=False)
    otp = models.CharField(max_length=6, null=True, blank=True)
    otp_time_limit = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.email

    def is_otp_valid(self):
        """Check if OTP is still valid (within 3 minutes)."""
        if self.otp_time_limit:
            return now() <= self.otp_time_limit

        return False

    class Meta:
        db_table = 'admin_temp_user'

# This model use for store user type data like admin etc.
class User_Type(models.Model):
    id = models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    user_type_name = models.CharField(max_length=100, null=False, blank=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'User_Type'

# This model use for store user data after registration complete then user create and also use for login.
class User_Master(AbstractBaseUser,PermissionsMixin):
    STATUS_CHOICES = (('Active','Active'),('Deactive','Deactive'))
    id = models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    username= models.CharField(max_length=150, null=False)
    email = models.EmailField(unique=True, null=False)
    password = models.CharField(max_length=255, null=False)
    phone_number = models.CharField(max_length=10)
    photo = models.ImageField(upload_to='users/', null=True, blank=True)
    user_type = models.ForeignKey(User_Type,on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'phone_number']
    
    def __str__(self):
        return self.email
    
    class Meta:
        db_table ='User_Master'
        
    objects = UserManager()


# this model use in forgot password and reset password api, because both api use otp for verification. 
class User_OTP_Master(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User_Master,on_delete=models.CASCADE)
    otp = models.CharField(max_length=6, null=True) 
    created_at = models.DateTimeField(default=now)

    class Meta:
        db_table = 'user_otp_master'