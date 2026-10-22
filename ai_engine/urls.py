from django.urls import path

from . import views

app_name = 'ai_engine'

urlpatterns = [
    # Pages
    path('', views.ai_hub, name='hub'),

    # JSON helpers used by the sell form and the assistant
    path('api/price/', views.suggest_price_api, name='price_api'),
    path('api/describe/', views.describe_api, name='describe_api'),
    path('api/classify/', views.classify_api, name='classify_api'),
    path('api/risk/', views.risk_api, name='risk_api'),
    path('api/search/', views.assistant_search_api, name='search_api'),
    path('api/parse/', views.parse_api, name='parse_api'),
    path('api/similar/<int:pk>/', views.similar_api, name='similar_api'),

    # Backwards-compatible alias kept for older clients
    path('suggest-price/', views.suggest_price_api, name='suggest_price_api'),
]
