from django.conf import settings
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path, re_path

from core import views as core_views

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
# deployed site. One route now serves them in every mode, reading from the
# database when MEDIA_STORAGE=db and from disk otherwise.
urlpatterns += [
    re_path(
        r'^media/(?P<path>.*)$',
        core_views.serve_media,
        name='serve_media',
    )
]
