from django.urls import path

from . import views

app_name = 'accounts'

urlpatterns = [
    path('signup/', views.signup, name='signup'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    path('messages/', views.messages_view, name='messages'),
    path('chat/start/<int:book_id>/', views.start_chat, name='start_chat'),
    path('chat/<int:user_id>/', views.chat_detail, name='chat_detail'),
    path('request-book/', views.request_book, name='request_book'),
    path('request-book/<int:pk>/delete/', views.delete_book_request, name='delete_book_request'),
]
