from django.urls import path
from .views import *

urlpatterns = [

    path('api/v1/Register', UserRegistrationAPI.as_view()),
    path('api/v1/RegisterVerifyOtp', OtpVerificationAPI.as_view()),
    path('api/v1/resend-otp', OtpResendAPI.as_view()),

    path('api/v1/login', LoginAPI.as_view()),
    path('api/v1/auth/verify-login', VerifyLoginAPI.as_view()),
    path('api/v1/auth/resend-login-otp', LoginOTPResendAPI.as_view()),

    path('api/v1/forgot-password', ForgotPasswordAPI.as_view()),
    path('api/v1/forgot-password-verify-otp', Forgot_Otp_API.as_view()),
    path('api/v1/reset-password', Resend_Forgot_Otp_API.as_view()),
    path('api/v1/change-password', Reset_Password_API.as_view()),

    path('api/v1/update-profile', UserUpdateProfileAPI.as_view()),
    path('api/v1/delete-account', DeleteUserAPI.as_view()),
    path('api/v1/logout', LogoutAPI.as_view()),

    path('api/v1/create-campaign', CreateCampaignAPI.as_view()),
    path('api/v1/update-campaign/<uuid:id>', UpdateCampaignAPI.as_view()),
    path('api/v1/delete-campaign/<uuid:id>', DeleteCampaignAPI.as_view()),

    path('voice/', voice),

    path('transcribe/', transcribe),
]


