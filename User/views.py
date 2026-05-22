from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated
from rest_framework import serializers
from django.core.mail import send_mail
from django.contrib.auth.hashers import make_password, check_password
from django.conf import settings
from datetime import timedelta
from django.utils.timezone import now
from .models import *
from .serializers import *
import random
import re
import os

def generate_otp():
    return str(random.randint(100000, 999999))

def otp_expiry():
    return now() + timedelta(minutes=3)

def send_otp_email(email, otp):
    send_mail(
        subject='Your OTP Code',
        message=f'''Your OTP is: {otp} This OTP is valid for 3 minutes.''',
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[email],
        fail_silently=False
    )

def validate_password(value):

    if len(value) < 8:
        raise serializers.ValidationError({'status': 0,'error': 'InvalidPasswordFormat','message': 'Password must be at least 8 characters long.'})

    if not re.search(r'[A-Z]', value):
        raise serializers.ValidationError({'status': 0,'error': 'InvalidPasswordFormat','message': 'Password must include at least one uppercase letter.'})

    if not re.search(r'[a-z]', value):
        raise serializers.ValidationError({'status': 0,'error': 'InvalidPasswordFormat','message': 'Password must contain at least one lowercase letter.'})

    if not re.search(r'\d', value):
        raise serializers.ValidationError({'status': 0,'error': 'InvalidPasswordFormat','message': 'Password must contain at least one numeric character.'})

    if not re.search(r'[!@#$%^&*()_+\-=\[\]{};:"\\|,.<>\/?]', value):
        raise serializers.ValidationError({'status': 0,'error': 'InvalidPasswordFormat','message': 'Password must contain at least one special character.'})

    return value

# User Registration with OTP verification, including validation and email sending
class UserRegistrationAPI(APIView):

    def post(self, request):
        serializer = UserRegisterSerializer(data=request.data)

        if serializer.is_valid():
            password = serializer.validated_data.get('password')

            # Password Validation
            try:
                validate_password(password)

            except serializers.ValidationError as e:
                return Response({'status': 0,'message': 'Validation Error','errors': e.detail},status=200)

            email = serializer.validated_data['email']

            # Email Exists Check
            if User_Master.objects.filter(email=email).exists():
                return Response({'status': 0,'message': 'Email already exists','data': None},status=200)

            # Generate OTP
            otp = generate_otp()
            # Save Temp User
            temp_user = serializer.save()
            temp_user.otp = otp
            temp_user.otp_time_limit = otp_expiry()
            temp_user.save()

            # Send OTP Email
            send_otp_email(temp_user.email, otp)

            # Success Response with User Data
            return Response({'status': 1,'message': 'OTP sent successfully',
                    'data': {
                        'id': temp_user.id,
                        'username': temp_user.username,
                        'email': temp_user.email,
                        'phone': temp_user.phone,
                        'photo': request.build_absolute_uri(temp_user.photo.url) if temp_user.photo else None}},status=200)

        return Response({'status': 0,'message': 'Validation Error','errors': serializer.errors},status=200)

# OTP verification for registration, including expiry check, duplicate user check, and JWT token generation upon successful verification.
class OtpVerificationAPI(APIView):

    def post(self, request):
        email = request.data.get('email')
        otp = request.data.get('otp')
        try:
            temp_user = AdminTempUser.objects.filter(email=email).order_by('-created_at').first()
            if not temp_user:
                return Response({'status': 0,'message': 'User not found','data': None}, status=200)

            # OTP expiry check
            if not temp_user.is_otp_valid():
                return Response({'status': 0,'message': 'OTP Expired','data': None}, status=200)
            
            if temp_user.otp != otp:
                return Response({'status': 0,'message': 'Invalid OTP','data': None}, status=200)

            # Duplicate user check
            if User_Master.objects.filter(email=temp_user.email).exists():
                return Response({'status': 0,'message': 'User already verified','data': None}, status=200)

            # User type check
            user_type, created = User_Type.objects.get_or_create(user_type_name='User')
           
            # Create main user
            user = User_Master.objects.create(
                username=temp_user.username,
                photo=temp_user.photo,
                email=temp_user.email,
                password=temp_user.password,
                phone=temp_user.phone,
                user_type=user_type
            )
            refresh = RefreshToken.for_user(user)
            # Delete temp user
            temp_user.delete()

            return Response({
                'status': 1,
                'message': 'Account verified successfully',
                'refresh': str(refresh),
                'access': str(refresh.access_token)
            }, status=200)

        except Exception as e:
            return Response({'status': 0,'message': 'Internal Server Error','data': None}, status=200)

# Resend OTP for registration, reusing valid OTP or generating a new one if expired, and sending it via email.
class OtpResendAPI(APIView):
    def post(self, request):
        email = request.data.get('email')

        if not email:
            return Response({'status': 0,'message': 'Email is required','data': None}, status=200)

        temp_user = AdminTempUser.objects.filter(email=email).order_by('-created_at').first()

        if not temp_user:
            return Response({'status': 0,'message': 'User not found','data': None}, status=200)

        # Check OTP valid
        if temp_user.is_otp_valid():
            otp = temp_user.otp
        else:
            otp = generate_otp()
            temp_user.otp = otp
            temp_user.otp_time_limit = otp_expiry()

            temp_user.save()

        # Send Email
        send_otp_email(temp_user.email, otp)
        return Response({'status': 1,'message': 'OTP resent successfully'}, status=200)

# Login API with email and password, including validation, JWT token generation, and error handling for invalid credentials and unregistered emails.
class LoginAPI(APIView):
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        if not email or not password:
            return Response({'status': 0,'message': 'Email and password are required',"data": None}, status=200)
        try:
            user = User_Master.objects.get(email=email)
            if password != user.password:
                return Response({'status': 0,'message': 'Invalid password',"data": None}, status=200)
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)

            return Response({'status': 1,'message': 'Login successfully', 'data': {'access': access_token, 'refresh': refresh_token}}, status=200)
        except User_Master.DoesNotExist:
            return Response({'status': 0,'message': 'Email not registered','data': None}, status=200)
        except Exception as e:
            return Response({'status': 0,'message': 'Login failed','data': None}, status=200)

# Sends OTP to user's email for password reset after validating registered email
class ForgotPasswordAPI(APIView):
    def post(self, request):
        email = request.data.get("email")  

        if not email:
            return Response({'status':0 ,'message':'Email are required','data':None},status=200)
        try:
            user = User_Master.objects.get(email = email)
            if not user.email:
                return Response({'status': 0, 'message': 'Email not registered','data':None}, status=200)

            otp = generate_otp()

            User_OTP_Master.objects.create(user=user,otp=otp,otp_time_limit=otp_expiry())
            send_otp_email(user.email, otp)

            return Response({'status': 1,'message': 'OTP sent to your email','data':[{'otp expired in': '3 min'}]}, status=200)

        except Exception as e:
            return Response({'status': 0, 'message': 'Internal Server Error', 'data': None},status=200)            

# Verifies forgot password OTP and checks expiry before allowing password reset
class Forgot_Otp_API(APIView):
   
    def post(self, request):
        email = request.data.get('email')
        otp = request.data.get('otp')
        if not email or not otp:
            return Response({'status': 0, 'message': 'Email and OTP are required','data':None}, status=200)
        try:
            email_otp = User_OTP_Master.objects.filter(user__email=email, otp=otp).order_by('-created_at').first()
            if not email_otp:
                return Response({'status': 0, 'message': 'Invalid OTP','data':None}, status=200)

            if now() > email_otp.otp_time_limit:
                return Response({'status': 0, 'message': 'OTP Expired','data':None}, status=200)

            return Response({'status': 1, 'message': 'OTP verified. Proceed to reset password.','data':None}, status=200)
        except Exception as e:
            return Response({'status': 0, 'message': 'Internal Server Error', 'data': None}, status=200)

# Resends forgot password OTP, reusing valid OTP or generating a new one if expired
class Resend_Forgot_Otp_API(APIView):
    def post(self, request):
        email = request.data.get("email")
        if not email:
            return Response({'status': 0, 'message': 'Email is required','data':None}, status=200)
        try:
            user = User_Master.objects.get(email=email)
            if not user.email:
                return Response({'status': 0, 'message': 'Email not registered','data':None}, status=200)
            email_otp = User_OTP_Master.objects.filter(user=user).order_by('-created_at').first()
            if email_otp and now() <= email_otp.otp_time_limit:
                otp = email_otp.otp
            else:
                otp = generate_otp()
                User_OTP_Master.objects.create(user=user, otp=otp, otp_time_limit=otp_expiry())
            send_otp_email(user.email, otp)
            return Response({
                'status': 1,
                'message': f"OTP sent to your email. It is valid for 3 minutes.",
                'data': {
                    'email': user.email,
                    'otp_valid_till': email_otp.otp_time_limit.strftime("%Y-%m-%d %H:%M:%S"),}}, status=200)
        
        except Exception as e:
            return Response({'status': 0, 'message': 'Internal Server Error', 'data': None}, status=200)

# Validates new password, matches confirmation, updates hashed password, and removes OTP record
class Reset_Password_API(APIView):
    def post(self, request):
        new_password = request.data.get('new_password')
        confirm_password = request.data.get('confirm_password')

        email = request.data.get('email')
        if not email:
            return Response({'status': 0, 'message': 'Email not found. Try again.','data':None}, status=200)
        
        if not new_password or not confirm_password:
            return Response({'status': 0, 'message': 'Both new_password and confirm_password are required','data':None}, status=200)
        
        if new_password != confirm_password:
            return Response({'status': 0, 'message': 'Passwords do not match','data':None}, status=200)
        try:
            validate_password(new_password)
            user = User_Master.objects.get(email=email)
            if not user.email:
                return Response({'status': 0, 'message': 'Email not registered','data':None}, status=200)

            # Check if new password matches old password
            if check_password(new_password, user.password):
                return Response({'status': 0, 'message': 'You cannot use your previous password. Try another password.','data':None}, status=200)

            # Hash and update the new password
            user.password = make_password(new_password)
            user.save()

            # Delete OTP 
            User_OTP_Master.objects.filter(user=user).delete()
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)

            return Response({'status': 1,'message': 'Password reset successfully.','data': {"access": access_token, "refresh": refresh_token}}, status=200)
        except Exception as e:
            return Response({'status': 0, 'message': 'Internal Server Error', 'data': None},status=200)

# User profile update API that allows authenticated users to update their username, phone, and photo with validation and returns updated profile data.
class UserUpdateProfileAPI(APIView):
    permission_classes = [IsAuthenticated]
    def put(self, request):
        try:
            user = request.user
            serializer = UserUpdateSerializer(user,data=request.data,partial=True)
            if serializer.is_valid():
                serializer.save()

                return Response({
                    'status': 1,
                    'message': 'Profile updated successfully',
                    'data': {
                        'id': str(user.id),
                        'username': user.username,
                        'phone': user.phone,
                        'photo': request.build_absolute_uri(user.photo.url) if user.photo else None}}, status=200)

            return Response({'status': 0,'message': 'Validation Error','errors': serializer.errors}, status=200)
        except Exception as e:
            return Response({'status': 0,'message': str(e)}, status=200)
                
# Logout API that blacklists the refresh token to invalidate the session, ensuring secure logout functionality.
class LogoutAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            token = RefreshToken(refresh_token)
            token.blacklist()

            return Response({'status': 1,'message': 'Logout successful'}, status=200)

        except Exception as e:
            return Response({'status': 0,'message': 'Invalid token',"data": None}, status=200)
        
class DeleteUserAPI(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        user_id = request.query_params.get("user_id")

        if not user_id:
            return Response({"status": 0, "message": "user_id is required","data":None}, status=200)

        try:
            user = User_Master.objects.get(id=user_id, user_type__user_type_name="User")
            user.delete()
            return Response({"status": 1, "message": "User deleted successfully"}, status=200)
        except User_Master.DoesNotExist:
            return Response({"status": 0, "message": "User not found","data":None}, status=200)

class UploadMediaFileAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user_id = request.data.get('user_id')
        file_type = request.data.get('file_type')
        uploaded_file = request.FILES.get('file')
        try:
            if not user_id:
                return Response({'status': 0,'message': 'User ID is required',"data":None}, status=200)

            if not file_type:
                return Response({'status': 0,'message': 'File type(Image, Document, Video) is required.',"data":None}, status=200)

            if not uploaded_file:
                return Response({'status': 0,'message': 'File is required'}, status=200)

            try:
                user = User_Master.objects.get(id=user_id)

            except User_Master.DoesNotExist:
                return Response({'status': 0,'message': 'User not found',"data":None}, status=200)

            extension = os.path.splitext(uploaded_file.name)[1].lower()

            image = ['.jpg','.jpeg','.png']
            document = ['.pdf','.doc','.docx','.txt','.xls','.xlsx','.ppt','.pptx']
            video = ['.mp4','.avi','.mkv','.mov']

            if file_type == 'Image':
                if extension not in image:
                    return Response({'status': 0,'message': 'Only image files(.jpg,.jpeg,.png) are allowed.',"data":None}, status=200)
                
                # IMAGE SIZE VALIDATION (5MB)
                if uploaded_file.size > 5 * 1024 * 1024:
                    return Response({'status': 0,'message': 'Image size exceeds 5MB limit.',"data":None}, status=200)

            elif file_type == 'Document':
                if extension not in document:
                    return Response({'status': 0,'message': 'Only document files(.pdf,.doc,.docx,.txt,.xls,.xlsx,.ppt,.pptx) are allowed.',"data":None}, status=200)

            elif file_type == 'Video':
                if extension not in video:
                    return Response({'status': 0,'message': 'Only video files(.mp4,.avi,.mkv,.mov) are allowed.',"data":None}, status=200)

            else:
                return Response({'status': 0,'message': 'Invalid file type',"data":None}, status=200)

            media_obj = MediaFile.objects.create(
                user=user,
                file_type=file_type,
                file=uploaded_file,
                file_name=uploaded_file.name
            )
            # FILE URL CREATE
            media_obj.file_url = request.build_absolute_uri(media_obj.file.url)

            media_obj.save()
            serializer = MediaFileSerializer(media_obj,context={'request': request})

            return Response({'status': 1,'message': 'File uploaded successfully','data': serializer.data}, status=200)
        except Exception as e:
            return Response({'status': 0, 'message': 'Internal Server Error', 'data': None},status=200)


# GET ALL FILES API
class MediaFileListAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, id=None):
        try:
            user = request.user
            # SINGLE FILE GET
            if id:
                try:
                    media_file = MediaFile.objects.get(id=id,user=user)
                except MediaFile.DoesNotExist:
                    return Response({'status': 0,'message': 'Media file not found','data': None}, status=200)

                serializer = MediaFileSerializer(media_file,context={'request': request})

                return Response({'status': 1,'message': 'Single media file','data': serializer.data}, status=200)
            # ALL FILES GET
            media_files = MediaFile.objects.filter(user=user).order_by('-created_at')

            if not media_files.exists():
                return Response({'status': 0,'message': 'No media files found','data': None}, status=200)

            serializer = MediaFileSerializer(media_files,many=True,context={'request': request})

            return Response({'status': 1,'message': 'Media file list','data': serializer.data}, status=200)

        except Exception as e:
            return Response({'status': 0,'message': 'Internal Server Error','data': None}, status=200)

# UPDATE FILE API
class UpdateMediaFileAPI(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, id):
        user = request.user
        try:
            media_file = MediaFile.objects.get(id=id,user=user)

        except MediaFile.DoesNotExist:
            return Response({'status': 0,'message': 'Media file not found','data': None}, status=200)

        try:
            file_type = request.data.get('file_type')
            uploaded_file = request.FILES.get('file')

            if not file_type:
                return Response({'status': 0,'message': 'File type(Image, Document, Video) is required.',"data":None}, status=200)

            if not uploaded_file:
                return Response({'status': 0,'message': 'File is required'}, status=200)

            extension = os.path.splitext(uploaded_file.name)[1].lower()

            image = ['.jpg', '.jpeg', '.png']
            document = ['.pdf','.doc','.docx','.txt','.xls','.xlsx','.ppt','.pptx']
            video = ['.mp4','.avi','.mkv','.mov']

            # IMAGE VALIDATION
            if file_type == 'Image':
                if extension not in image:
                    return Response({'status': 0,'message': 'Only image files(.jpg,.jpeg,.png) are allowed.',"data":None}, status=200)
                
                if uploaded_file.size > 5 * 1024 * 1024:
                    return Response({'status': 0,'message': 'Image size exceeds 5MB limit.',"data":None}, status=200)
                
            # DOCUMENT VALIDATION
            elif file_type == 'Document':
                if extension not in document:
                    return Response({'status': 0,'message': 'Only document files(.pdf,.doc,.docx,.txt,.xls,.xlsx,.ppt,.pptx) are allowed.',"data":None}, status=200)

            # VIDEO VALIDATION
            elif file_type == 'Video':
                if extension not in video:
                    return Response({'status': 0,'message': 'Only video files(.mp4,.avi,.mkv,.mov) are allowed.',"data":None}, status=200)

            else:
                return Response({'status': 0,'message': 'Invalid file type',"data":None}, status=200)

            # UPDATE FILE
            media_file.file_type = file_type
            media_file.file = uploaded_file
            media_file.file_name = uploaded_file.name
            # UPDATE FILE URL
            media_file.file_url = request.build_absolute_uri(uploaded_file.name)

            media_file.save()

            serializer = MediaFileSerializer(media_file,context={'request': request})

            return Response({'status': 1,'message': 'Media file updated successfully','data': serializer.data}, status=200)

        except Exception as e:
            return Response({'status': 0,'message': 'Internal Server Error','data': None}, status=200)
        
# DELETE FILE API
class DeleteMediaFileAPI(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, id):
        user = request.user
        try:
            media_file = MediaFile.objects.get(id=id,user=user)

        except MediaFile.DoesNotExist:
            return Response({'status': False,'message': 'Media file not found',"data":None}, status=200)

        media_file.delete()

        return Response({'status': True,'message': 'Media file deleted successfully',"data":None}, status=200)
    
# CREATE PRODUCT API
class CreateProductAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            product_name = request.data.get('product_name')
            description = request.data.get('description')
            price = request.data.get('price')
            quantity = request.data.get('quantity')
            category_id = request.data.get('category_id')
            status_value = request.data.get('status')
            product_image = request.FILES.get('product_image')

            # REQUIRED FIELD VALIDATION
            if not category_id:
                return Response({'status': 0,'message': 'Category ID is required',"data":None}, status=200)
            
            if not product_name:
                return Response({'status': 0,'message': 'Product name is required',"data":None}, status=200)

            if not description:
                return Response({'status': 0,'message': 'Description is required',"data":None}, status=200)

            if not price:
                return Response({'status': 0,'message': 'Price is required',"data":None}, status=200)

            if not quantity:
                return Response({'status': 0,'message': 'Quantity is required',"data":None}, status=200)

            # CATEGORY VALIDATION
            try:
                category = Category.objects.get(id=category_id)
            except Category.DoesNotExist:
                return Response({'status': 0,'message': 'Category not found',"data":None}, status=200)

            # IMAGE VALIDATION
            if product_image:
                extension = os.path.splitext(product_image.name)[1].lower()
                image_extensions = ['.jpg','.jpeg','.png']

                if extension not in image_extensions:
                    return Response({'status': 0,'message': 'Only image files(.jpg,.jpeg,.png) are allowed.',"data":None}, status=200)

                if product_image.size > 5 * 1024 * 1024:
                    return Response({'status': 0,'message': 'Image size exceeds 5MB limit.',"data":None}, status=200)

            # CREATE PRODUCT
            product_obj = Product.objects.create(
                category=category,
                product_name=product_name,
                description=description,
                price=price,
                quantity=quantity,
                product_image=product_image,
                status=status_value
            )
            if product_obj.product_image:
                product_obj.product_image_url = (request.build_absolute_uri(product_obj.product_image.url))

                product_obj.save()

            serializer = ProductSerializer(product_obj,context={'request': request})

            return Response({'status': 1,'message': 'Product created successfully','data': serializer.data}, status=200)

        except Exception as e:
            return Response({'status': 0,'message': 'Internal Server Error','data': None}, status=200)

# PRODUCT LIST + SINGLE PRODUCT API
class ProductListAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, id=None):
        try:
            # SINGLE PRODUCT
            if id:
                try:
                    product = Product.objects.get(id=id)
                except Product.DoesNotExist:
                    return Response({'status': 0,'message': 'Product not found','data': None}, status=200)

                serializer = ProductSerializer(product,context={'request': request})

                return Response({'status': 1,'message': 'Single product','data': serializer.data}, status=200)

            # ALL PRODUCTS
            products = Product.objects.all().order_by('-created_at')

            if not products.exists():
                return Response({'status': 0,'message': 'No products found','data': None}, status=200)

            serializer = ProductSerializer(products,many=True,context={'request': request})

            return Response({'status': 1,'message': 'Product list','data': serializer.data}, status=200)
        except Exception as e:
            return Response({'status': 0,'message': 'Internal Server Error','data': None}, status=200)

# UPDATE PRODUCT API
class UpdateProductAPI(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, id):
        try:
            try:
                product = Product.objects.get(id=id)
            except Product.DoesNotExist:
                return Response({'status': 0,'message': 'Product not found','data': None}, status=200)

            product_name = request.data.get('product_name')
            description = request.data.get('description')
            price = request.data.get('price')
            quantity = request.data.get('quantity')
            category_id = request.data.get('category_id')
            status_value = request.data.get('status')
            product_image = request.FILES.get('product_image')

            # CATEGORY
            if category_id:
                try:
                    category = Category.objects.get(id=category_id)
                    product.category = category
                except Category.DoesNotExist:
                    return Response({'status': 0,'message': 'Category not found',"data":None}, status=200)

            # IMAGE VALIDATION
            if product_image:
                extension = os.path.splitext(product_image.name)[1].lower()
                image_extensions = ['.jpg', '.jpeg', '.png']

                if extension not in image_extensions:
                    return Response({'status': 0,'message': 'Only image files(.jpg,.jpeg,.png) are allowed.',"data":None}, status=200)

                if product_image.size > 5 * 1024 * 1024:
                    return Response({'status': 0,'message': 'Image size exceeds 5MB limit.',"data":None}, status=200)

                # IMAGE UPDATE
                product.product_image = product_image
                product.product_image_url = request.build_absolute_uri(product.product_image.url)

            # UPDATE DATA
            if product_name:
                product.product_name = product_name

            if description:
                product.description = description

            if price:
                product.price = price

            if quantity:
                product.quantity = quantity

            if status_value:
                product.status = status_value

            product.save()

            serializer = ProductSerializer(product,context={'request': request})

            return Response({'status': 1,'message': 'Product updated successfully','data': serializer.data}, status=200)
        except Exception as e:
            return Response({'status': 0,'message': 'Internal Server Error','data': None}, status=200)

# DELETE PRODUCT API
class DeleteProductAPI(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, id):
        try:
            try:
                product = Product.objects.get(id=id)
            except Product.DoesNotExist:
                return Response({'status': 0,'message': 'Product not found','data': None}, status=200)

            product.delete()

            return Response({'status': 1,'message': 'Product deleted successfully'}, status=200)
        except Exception as e:
            return Response({'status': 0,'message': 'Internal Server Error','data': None}, status=200)
        

