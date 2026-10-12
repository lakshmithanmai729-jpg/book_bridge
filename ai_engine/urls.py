from django.urls import path
from . import views

app_name = 'ai_engine'

urlpatterns = [
    path('suggest-price/', views.suggest_price_api, name='suggest_price_api'),
]
