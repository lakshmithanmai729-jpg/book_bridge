from django.contrib.sitemaps.views import sitemap
from django.urls import path
from django.views.generic import TemplateView

from . import views
from .sitemaps import BookSitemap, StaticViewSitemap

app_name = 'core'

sitemaps = {
    'static': StaticViewSitemap,
    'books': BookSitemap,
}

urlpatterns = [
    path('', views.home, name='home'),
    path('safety/', views.safety, name='safety'),
    path('healthz/', views.healthz, name='healthz'),
    path('staff/', views.staff_dashboard, name='staff_dashboard'),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='sitemap'),
    path(
        'robots.txt',
        TemplateView.as_view(template_name='robots.txt', content_type='text/plain'),
        name='robots',
    ),
    path(
        'manifest.webmanifest',
        TemplateView.as_view(
            template_name='manifest.webmanifest',
            content_type='application/manifest+json',
        ),
        name='manifest',
    ),
]
