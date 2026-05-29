from django.urls import path
from .views import *

urlpatterns = [
    path('api/v1/auth/Register', UserRegistrationAPI.as_view()),
    path('api/v1/auth/RegisterVerifyOtp', OtpVerificationAPI.as_view()),
    path('api/v1/auth/resend-otp/', OtpResendAPI.as_view()),

    path('api/v1/auth/login', LoginAPI.as_view()),
    path('api/v1/auth/verify-login', VerifyLoginAPI.as_view()),
    path('api/v1/auth/resend-login-otp', LoginOTPResendAPI.as_view()),

    path('api/v1/auth/forgot-password/', ForgotPasswordAPI.as_view()),
    path('api/v1/auth/forgot-password-verify-otp/', Forgot_Otp_API.as_view()),
    path('api/v1/auth/reset-password/', Resend_Forgot_Otp_API.as_view()),
    path('api/v1/auth/change-password/', Reset_Password_API.as_view()),

    path('api/v1/update-profile', UserUpdateProfileAPI.as_view()),
 
    path('api/v1/Admin-Delete-Acount', DeleteAdminAPI.as_view()),
    
    path('logout/', LogoutAPI.as_view()),


]