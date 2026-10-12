from django.urls import path
from . import views

app_name = 'books'

urlpatterns = [
    path('', views.book_list, name='book_list'),
    path('add/', views.book_add, name='book_add'),
    path('wishlist/', views.wishlist_view, name='wishlist'),
    path('<int:pk>/', views.book_detail, name='book_detail'),
    path('<int:pk>/edit/', views.book_edit, name='book_edit'),
    path('<int:pk>/delete/', views.book_delete, name='book_delete'),
    path('<int:pk>/wishlist-toggle/', views.wishlist_toggle, name='wishlist_toggle'),
]
