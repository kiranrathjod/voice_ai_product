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
from User.models import *
from .serializers import *
import random
import re

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
        serializer = AdminRegisterSerializer(data=request.data)

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
            user_type, created = User_Type.objects.get_or_create(user_type_name='Admin')
           
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

# Login API that validates credentials, generates OTP for login, and sends it via email.
class LoginAPI(APIView):
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        if not email or not password:
            return Response({'status': 0,'message': 'Email and password are required',"data": None}, status=200)

        try:
            user = User_Master.objects.get(email=email)
            if password != user.password:
                return Response({'status': 0,'message': 'Invalid password',"data": None},status=200)
            AdminLoginOTP.objects.filter(user=user).delete()
            otp = generate_otp()

            AdminLoginOTP.objects.create(
                user=user,
                otp=otp,
                otp_time_limit=otp_expiry())

            send_otp_email(user.email, otp)
            return Response({'status': 1,'message': 'Login OTP sent successfully'},status=200)
        except User_Master.DoesNotExist:
            return Response({'status': 0,'message': 'Email not registered','data': None}, status=200)
        except Exception as e:
            return Response({'status': 0,'message': 'Login failed. Please check email service or server logs.','data': None}, status=200)

# OTP verification for login, including expiry check and JWT token generation upon successful verification.
class VerifyLoginAPI(APIView):

    def post(self, request):
        email = request.data.get('email')
        otp = request.data.get('otp')
        if not email or not otp:
            return Response({'status': 0,'message': 'Email and OTP are required',"data": None}, status=200)

        try:
            user = User_Master.objects.get(email=email)
            if not user.email:
                return Response({'status': 0,'message': 'Email not registered','data': None}, status=200)
            login_otp = AdminLoginOTP.objects.filter(user=user).order_by('-id').first()

            if not login_otp:
                return Response({'status':0,'message':'OTP not found',"data": None}, status=200)

            if now() > login_otp.otp_time_limit:
                return Response({'status': 0,'message': 'OTP Expired',"data": None}, status=200)

            if login_otp.otp != otp:
                return Response({'status': 0,'message': 'Invalid OTP',"data": None}, status=200)

            refresh = RefreshToken.for_user(user)
            login_otp.delete()
            return Response({
                'status': 1,
                'message': 'Login successful',
                'refresh': str(refresh),
                'access': str(refresh.access_token)
            }, status=200)

        except User_Master.DoesNotExist:
            return Response({'status': 0,'message': 'Email not registered','data': None}, status=200)
        except Exception as e:
            return Response({'status':0,'message':'Internal Server Error',"data": None}, status=200)

# Resend OTP for login, reusing valid OTP or generating a new one if expired, and sending it via email.
class LoginOTPResendAPI(APIView):
    def post(self, request):
        email = request.data.get('email')
        try:
            user = User_Master.objects.get(email=email)
            if not user.email:
                return Response({'status': 0,'message': 'Email not registered','data': None}, status=200)
            login_otp = AdminLoginOTP.objects.filter(user=user).last()

            if login_otp and now() <= login_otp.otp_time_limit:
                otp = login_otp.otp
            else:
                otp = generate_otp()
                AdminLoginOTP.objects.create(user=user,otp=otp,otp_time_limit=otp_expiry())

            send_otp_email(user.email, otp)

            return Response({'status': 1,'message': 'Login OTP resent successfully'}, status=200)
        except Exception as e:
            return Response({'status': 0,'message': 'Internal Server Error','data': None}, status=200)
        
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

            return Response({'status': 1,'message': 'Password reset successfully.','data': {'refresh': str(refresh),'access': str(refresh.access_token),}}, status=200)
        except Exception as e:
            return Response({'status': 0, 'message': 'Internal Server Error', 'data': None},status=200)
        
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
        
class DeleteAdminAPI(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        user_id = request.query_params.get("user_id")

        if not user_id:
            return Response({"status": 0, "message": "user_id is required"}, status=200)

        try:
            user = User_Master.objects.get(id=user_id, user_type__user_type_name="Admin")
            user.delete()
            return Response({"status": 1, "message": "User deleted successfully"}, status=200)
        except User_Master.DoesNotExist:
            return Response({"status": 0, "message": "User not found"}, status=200)
