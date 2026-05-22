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
    photo = models.ImageField(upload_to='users/', null=True, blank=True)
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
    phone = models.CharField(max_length=10)
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

# this model use in Admin login otp save 
class AdminLoginOTP(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User_Master,on_delete=models.CASCADE)
    otp = models.CharField(max_length=6, null=True)   
    otp_time_limit = models.DateTimeField(null=True, blank=True) 
    created_at_otp = models.DateTimeField(default=now) 
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'Login_otp'


# this model use in forgot password and reset password api, because both api use otp for verification. 
class User_OTP_Master(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User_Master,on_delete=models.CASCADE)
    otp = models.CharField(max_length=6, null=True) 
    created_at = models.DateTimeField(default=now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_otp_master'

# FILE UPLOAD PATH FUNCTION
def media_file_upload_path(instance, filename):

    if instance.file_type == 'Image':
        return f'images/{filename}'

    elif instance.file_type == 'Document':
        return f'documents/{filename}'

    elif instance.file_type == 'Video':
        return f'videos/{filename}'

    return f'others/{filename}'

class MediaFile(models.Model):
    FILE_TYPE = (('Image', 'Image'),('Document', 'Document'),('Video', 'Video'))
    id = models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    user = models.ForeignKey(User_Master,on_delete=models.CASCADE)
    file_type = models.CharField(max_length=20,choices=FILE_TYPE)
    file = models.FileField(upload_to=media_file_upload_path)
    file_name = models.CharField(max_length=255)
    file_url = models.URLField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'media_files'

# NOTIFICATION MODEL
class Notification(models.Model):
    NOTIFICATION_TYPE = (('Email', 'Email'),('Push', 'Push'))
    STATUS = (('Unread', 'Unread'),('Read', 'Read'))
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User_Master, on_delete=models.CASCADE)
    notification_type = models.CharField(max_length=10, choices=NOTIFICATION_TYPE)
    title = models.CharField(max_length=255)
    message = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS, default='Unread')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        db_table = 'notifications'

class Category(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category_name=models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        db_table = "Category"

# PRODUCT MODEL (CRUD API)
class Product(models.Model):
    STATUS = (('Available', 'Available'),('OutOfStock', 'OutOfStock'))
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product_name = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.IntegerField()
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    product_image = models.ImageField(upload_to='products/', null=True, blank=True)
    product_image_url = models.URLField(null=True,blank=True)
    status = models.CharField(max_length=20,choices=STATUS,default='Available')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'products'