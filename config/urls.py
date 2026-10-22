from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path, re_path
from django.views.static import serve

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/password_change/', auth_views.PasswordChangeView.as_view(
        template_name='accounts/password_change.html',
        success_url='/accounts/password_change/done/'
    ), name='password_change'),
    path('accounts/password_change/done/', auth_views.PasswordChangeDoneView.as_view(
        template_name='accounts/password_change_done.html'
    ), name='password_change_done'),
    path('accounts/', include('accounts.urls')),
    path('books/', include('books.urls')),
    path('ai/', include('ai_engine.urls')),
    path('', include('core.urls')),
]

# Uploaded book photos are user content, so they live outside STATIC_ROOT and
# WhiteNoise will not serve them. Django's static() helper does nothing when
# DEBUG is off, which used to leave every cover image as a broken link on the
# deployed site. serve() is protected against path traversal and is fine at
# this scale; move to object storage (S3/Cloudinary) if traffic grows.
urlpatterns += [
    re_path(
        r'^media/(?P<path>.*)$',
        serve,
        {'document_root': settings.MEDIA_ROOT, 'show_indexes': False},
        name='serve_media',
    )
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
