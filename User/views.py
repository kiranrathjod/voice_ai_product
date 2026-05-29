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
    


print("User views loaded successfully.")

# from django.http import HttpResponse
# from django.views.decorators.csrf import csrf_exempt
# from twilio.twiml.voice_response import VoiceResponse, Gather

# from .voice_assistant import (
#     ask_llm,
#     synthesize
# )

# PUBLIC_URL = "https://YOUR_NGROK_URL.ngrok-free.app"


# @csrf_exempt
# def voice(request):

#     vr = VoiceResponse()

#     gather = Gather(
#         input="speech",
#         action=f"{PUBLIC_URL}/user/transcribe/",
#         method="POST",
#         speech_timeout="auto",
#         language="en-US",
#     )

#     gather.say("Hello! I am your AI assistant. How can I help you?",voice="alice")

#     vr.append(gather)

#     return HttpResponse(str(vr),content_type="application/xml")


# @csrf_exempt
# def transcribe(request):

#     user_text = request.POST.get("SpeechResult", "").strip()
#     vr = VoiceResponse()

#     if not user_text:
#         vr.say("Sorry I did not catch that.",voice="alice")
#         vr.redirect(f"{PUBLIC_URL}/user/voice/",method="POST")

#         return HttpResponse(str(vr),content_type="application/xml")

#     print("USER:", user_text)

#     if user_text.lower() in ["bye","goodbye","exit","quit"]:
#         vr.say("Goodbye!",voice="alice")

#         vr.hangup()

#         return HttpResponse(str(vr),content_type="application/xml")

#     # AI RESPONSE
#     reply = ask_llm(user_text)

#     print("AI:", reply)

#     # GENERATE AUDIO
#     audio_file = synthesize(reply)

#     audio_url = f"{PUBLIC_URL}/media/tts_audio/{audio_file}"

#     vr.play(audio_url)

#     vr.redirect(f"{PUBLIC_URL}/user/voice/",method="POST")

#     return HttpResponse(str(vr),content_type="application/xml")


def generate_otp():
    return str(random.randint(100000, 999999))

def otp_expiry():
    return now() + timedelta(minutes=10)

def send_otp_email(email, otp):
    send_mail(
        subject='Your OTP Code',
        message=f'''Your OTP is: {otp} This OTP is valid for 10 minutes.''',
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[email],
        fail_silently=False
    )

def validate_password(value):

    if len(value) < 8:
        raise serializers.ValidationError({'status': 0,'error': 'InvalidPasswordFormat','message': 'Password must be at least 8 characters long.'},status=200)

    if not re.search(r'[A-Z]', value):
        raise serializers.ValidationError({'status': 0,'error': 'InvalidPasswordFormat','message': 'Password must include at least one uppercase letter.'},status=200)

    if not re.search(r'[a-z]', value):
        raise serializers.ValidationError({'status': 0,'error': 'InvalidPasswordFormat','message': 'Password must contain at least one lowercase letter.'},status=200)

    if not re.search(r'\d', value):
        raise serializers.ValidationError({'status': 0,'error': 'InvalidPasswordFormat','message': 'Password must contain at least one numeric character.'},status=200)

    if not re.search(r'[!@#$%^&*()_+\-=\[\]{};:"\\|,.<>\/?]', value):
        raise serializers.ValidationError({'status': 0,'error': 'InvalidPasswordFormat','message': 'Password must contain at least one special character.'},status=200)

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
            
            temp_user = serializer.save(
                password=make_password(password)
            )
            # Save Temp User
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

        if not email or not otp:
            return Response({'status': 0,'message': 'Email and OTP are required','data': None}, status=200)

        temp_user = AdminTempUser.objects.filter(email=email).order_by('-created_at').first()

        if not temp_user:
            return Response({'status': 0,'message': 'User not found','data': None}, status=200)

        # OTP expiry check
        if not temp_user.is_otp_valid():
            return Response({'status': 0,'message': 'OTP Expired','data': None}, status=200)

        # OTP match check
        if str(temp_user.otp) != str(otp):
            return Response({'status': 0,'message': 'Invalid OTP','data': None}, status=200)

        # Duplicate user check
        if User_Master.objects.filter(email=temp_user.email).exists():
            return Response({'status': 0,'message': 'User already verified','data': None}, status=200)

        # User type check
        try:
            user_type = User_Type.objects.get(user_type_name='User')

        except User_Type.DoesNotExist:
            return Response({'status': 0,'message': 'User type not found','data': None}, status=200)

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
            return Response({'status': 0,'message': 'Email and password required'}, status=200)

        try:
            user = User_Master.objects.get(email=email)

            if user.status != 'Active':
                return Response({'status': 0, 'message': 'Your account is deactivated. Please contact support.', 'data': None},status=200)

            if not check_password(password, user.password):
                return Response({'status': 0,'message': 'Invalid Password'}, status=200)

            otp = generate_otp()

            user.otp = otp
            user.otp_time_limit = otp_expiry()
            user.save()

            send_otp_email(user.email, otp)

            return Response({'status': 1,'message': 'OTP sent successfully'}, status=200)

        except User_Master.DoesNotExist:
            return Response({'status': 0,'message': 'Email not registered'}, status=200)


# OTP verification for login, including expiry check and JWT token generation upon successful verification.
class VerifyLoginAPI(APIView):

    def post(self, request):

        email = request.data.get('email')
        otp = request.data.get('otp')

        try:
            user = User_Master.objects.get(email=email)

            if user.otp != otp:
                return Response({'status': 0,'message': 'Invalid OTP'}, status=200)

            if now() > user.otp_time_limit:
                return Response({'status': 0,'message': 'OTP Expired'}, status=200)

            # Clear OTP
            user.otp = None
            user.otp_time_limit = None
            user.save()

            refresh = RefreshToken.for_user(user)

            return Response({
                'status': 1,
                'message': 'Login successful',
                'access': str(refresh.access_token),
                'refresh': str(refresh)})

        except User_Master.DoesNotExist:
            return Response({'status': 0,'message': 'User not found'}, status=200)

# Resend OTP for login, reusing valid OTP or generating a new one if expired, and sending it via email.
class LoginOTPResendAPI(APIView):

    def post(self, request):
        email = request.data.get('email')
        try:
            user = User_Master.objects.get(email=email)
            otp = generate_otp()
            user.otp = otp
            user.otp_time_limit = otp_expiry()
            user.save()

            send_otp_email(user.email, otp)

            return Response({'status': 1,'message': 'OTP resent successfully'}, status=200)

        except User_Master.DoesNotExist:
            return Response({'status': 0,'message': 'User not found'}, status=200)

# Sends OTP to user's email for password reset after validating registered email
class ForgotPasswordAPI(APIView):

    def post(self, request):

        email = request.data.get('email')

        try:
            user = User_Master.objects.get(email=email)

            otp = generate_otp()

            user.otp = otp
            user.otp_time_limit = otp_expiry()
            user.save()

            send_otp_email(user.email, otp)

            return Response({'status': 1,'message': 'OTP sent successfully'}, status=200)

        except User_Master.DoesNotExist:
            return Response({'status': 0,'message': 'Email not registered'}, status=200)

# Verifies forgot password OTP and checks expiry before allowing password reset
class Forgot_Otp_API(APIView):

    def post(self, request):

        email = request.data.get('email')
        otp = request.data.get('otp')

        try:
            user = User_Master.objects.get(email=email)

            if user.otp != otp:
                return Response({'status': 0,'message': 'Invalid OTP'}, status=200)

            if now() > user.otp_time_limit:
                return Response({'status': 0,'message': 'OTP Expired'}, status=200)

            return Response({'status': 1,'message': 'OTP verified successfully'}, status=200)

        except User_Master.DoesNotExist:
            return Response({'status': 0,'message': 'User not found'}, status=200)

# Resends forgot password OTP, reusing valid OTP or generating a new one if expired
class Resend_Forgot_Otp_API(APIView):

    def post(self, request):

        email = request.data.get("email")

        if not email:
            return Response({'status': 0,'message': 'Email is required','data': None}, status=200)

        try:
            user = User_Master.objects.get(email=email)

            # OTP still valid
            if user.otp and user.otp_time_limit and now() <= user.otp_time_limit:
                otp = user.otp

            else:
                otp = generate_otp()

                user.otp = otp
                user.otp_time_limit = otp_expiry()
                user.save()

            send_otp_email(user.email, otp)

            return Response({
                'status': 1,
                'message': 'OTP sent successfully',
                'data': {
                    'email': user.email,
                    'otp_valid_till': user.otp_time_limit.strftime("%Y-%m-%d %H:%M:%S")}}, status=200)

        except User_Master.DoesNotExist:
            return Response({'status': 0,'message': 'Email not registered','data': None}, status=200)

        except Exception as e:
            return Response({'status': 0,'message': 'Internal Server Error','data': str(e)}, status=200)

# Validates new password, matches confirmation, updates hashed password, and removes OTP record
class Reset_Password_API(APIView):

    def post(self, request):

        email = request.data.get('email')
        new_password = request.data.get('new_password')
        confirm_password = request.data.get('confirm_password')

        if not email:
            return Response({'status': 0,'message': 'Email is required','data': None}, status=200)

        if not new_password or not confirm_password:
            return Response({'status': 0,'message': 'Both passwords are required','data': None}, status=200)

        if new_password != confirm_password:
            return Response({'status': 0,'message': 'Passwords do not match','data': None}, status=200)

        try:
            validate_password(new_password)

            user = User_Master.objects.get(email=email)

            # Old password check
            if check_password(new_password, user.password):
                return Response({'status': 0,'message': 'You cannot use old password','data': None}, status=200)

            # Update password
            user.password = make_password(new_password)

            # Clear OTP
            user.otp = None
            user.otp_time_limit = None

            user.save()

            refresh = RefreshToken.for_user(user)

            return Response({
                'status': 1,
                'message': 'Password reset successfully',
                'data': {'access': str(refresh.access_token),'refresh': str(refresh)}}, status=200)

        except User_Master.DoesNotExist:
            return Response({'status': 0,'message': 'Email not registered','data': None}, status=200)

        except serializers.ValidationError as e:
            return Response({'status': 0,'message': 'Validation Error','errors': e.detail}, status=200)

        except Exception as e:
            return Response({'status': 0,'message': 'Internal Server Error','data': str(e)}, status=200)

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
        
# delete-user profile api
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
        
class CreateCampaignAPI(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        serializer = CampaignSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save(user=request.user)

            return Response({'status': 1,'message': 'Campaign created successfully','data': serializer.data})

        return Response({'status': 0,'message': 'Validation error','errors': serializer.errors},status=200)


class UpdateCampaignAPI(APIView):

    permission_classes = [IsAuthenticated]

    def put(self, request, id):

        try:
            campaign = Campaign.objects.get(id=id, user=request.user)

        except Campaign.DoesNotExist:
            return Response({'status': 0,'message': 'Campaign not found','data': None},status=200)

        serializer = CampaignUpdateSerializer(campaign,data=request.data,partial=True)

        if serializer.is_valid():

            serializer.save()

            return Response({'status': 1,'message': 'Campaign updated successfully','data': serializer.data},status=200)

        return Response({'status': 0,'message': 'Validation error','errors': serializer.errors},status=200)

class DeleteCampaignAPI(APIView):

    permission_classes = [IsAuthenticated]

    def delete(self, request, id):
        try:
            campaign = Campaign.objects.get(id=id, user=request.user)

        except Campaign.DoesNotExist:
            return Response({'status': 0,'message': 'Campaign not found','data': None},status=200)

        campaign.delete()

        return Response({'status': 1,'message': 'Campaign deleted successfully','data': None},status=200)

