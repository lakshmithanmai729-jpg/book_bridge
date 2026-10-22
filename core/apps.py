from django.apps import AppConfig
from django.contrib import admin


class CoreConfig(AppConfig):
    name = 'core'

    def ready(self):
        """Brand the Django admin so it looks like part of BookBridge."""
        admin.site.site_header = 'BookBridge — team backend'
        admin.site.site_title = 'BookBridge'
        admin.site.index_title = 'Marketplace data'
