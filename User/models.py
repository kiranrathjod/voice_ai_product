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
    otp = models.CharField(max_length=6, null=True, blank=True)
    otp_time_limit = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    USERNAME_FIELD = 'email'
    
    def __str__(self):
        return self.email
    
    class Meta:
        db_table ='User_Master'
        
    objects = UserManager()



class Campaign(models.Model):
    STATUS_CHOICES = (('Draft', 'Draft'),('Running', 'Running'),('Completed', 'Completed'),('Paused', 'Paused'),('Failed', 'Failed'),)
    id = models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    user = models.ForeignKey(User_Master,on_delete=models.CASCADE,related_name='campaigns')
    campaign_name = models.CharField(max_length=255)
    agent_name = models.CharField(max_length=255)
    language = models.CharField(max_length=50)
    voice_gender = models.CharField(max_length=20)
    voice_type = models.CharField(max_length=100)
    calling_start_time = models.DateTimeField()
    calling_end_time = models.DateTimeField()
    max_retry_attempts = models.IntegerField(default=3)
    status = models.CharField(max_length=50,choices=STATUS_CHOICES,default='Draft')
    instruction_prompt = models.TextField(blank=True,null=True)
    generated_prompt = models.TextField(blank=True,null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.campaign_name
    class Meta:
        db_table = 'campaigns'

class ContactList(models.Model):
    STATUS_CHOICES = (('Processing', 'Processing'),('Completed', 'Completed'),)
    id = models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    campaign = models.ForeignKey(Campaign,on_delete=models.CASCADE,related_name='contact_lists')
    file_name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=50)
    upload_status = models.CharField(max_length=50,choices=STATUS_CHOICES,default='Processing')
    file = models.FileField(upload_to='contact_lists/')
    file_url = models.URLField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.file_name
    
    class Meta:
        db_table = 'contact_lists'

class Contact(models.Model):
    VALID_STATUS = (('Valid', 'Valid'),('Invalid', 'Invalid'),('Duplicate', 'Duplicate'),)
    id = models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    contact_list = models.ForeignKey(ContactList,on_delete=models.CASCADE,related_name='contacts')
    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20)
    email = models.EmailField(max_length=255)
    validation_status = models.CharField(max_length=50,choices=VALID_STATUS,default='Valid')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.full_name
    
    class Meta:
        db_table = 'contacts'

# class CallLog(models.Model):


#     campaign = models.ForeignKey(Campaign)

#     contact = models.ForeignKey(Contact)

#     user_text = models.TextField()

#     ai_response = models.TextField()

#     call_sid = models.CharField(max_length=255)

#     status = models.CharField(max_length=50)

#     created_at = models.DateTimeField(auto_now_add=True)