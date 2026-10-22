from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = 'accounts'

urlpatterns = [
    path('signup/', views.signup, name='signup'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    # Password reset (email link -> choose a new password)
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='accounts/password_reset.html',
        email_template_name='emails/password_reset.txt',
        html_email_template_name='emails/password_reset.html',
        subject_template_name='emails/password_reset_subject.txt',
        success_url='/accounts/password-reset/sent/',
    ), name='password_reset'),
    path('password-reset/sent/', auth_views.PasswordResetDoneView.as_view(
        template_name='accounts/password_reset_sent.html',
    ), name='password_reset_done'),
    path('password-reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='accounts/password_reset_confirm.html',
        success_url='/accounts/password-reset/complete/',
    ), name='password_reset_confirm'),
    path('password-reset/complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='accounts/password_reset_complete.html',
    ), name='password_reset_complete'),

    path('email/verify/<str:token>/', views.verify_email, name='verify_email'),
    path('email/resend/', views.resend_verification, name='resend_verification'),
    # Trust & safety
    path('sellers/<int:user_id>/', views.seller_profile, name='seller_profile'),
    path('sellers/<int:user_id>/review/', views.review_seller, name='review_seller'),
    path('block/<int:user_id>/', views.toggle_block, name='toggle_block'),
    path('blocked/', views.blocked_users, name='blocked_users'),

    # Notifications & seller analytics
    path('notifications/', views.notifications_list, name='notifications'),
    path('notifications/read/<int:pk>/', views.notification_open, name='notification_open'),
    path('notifications/read-all/', views.notifications_read_all, name='notifications_read_all'),
    path('analytics/', views.seller_analytics, name='seller_analytics'),

    path('messages/', views.messages_view, name='messages'),
    path('chat/start/<int:book_id>/', views.start_chat, name='start_chat'),
    path('chat/<int:user_id>/', views.chat_detail, name='chat_detail'),
    path('request-book/', views.request_book, name='request_book'),
    path('request-book/<int:pk>/delete/', views.delete_book_request, name='delete_book_request'),
]
