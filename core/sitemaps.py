"""Sitemap definitions so search engines can index the marketplace."""
from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from books.models import Book


class StaticViewSitemap(Sitemap):
    priority = 0.6
    changefreq = 'weekly'

    def items(self):
        return ['core:home', 'books:book_list', 'core:safety']

    def location(self, item):
        return reverse(item)


class BookSitemap(Sitemap):
    priority = 0.8
    changefreq = 'daily'

    def items(self):
        return Book.objects.filter(is_sold=False, is_hidden=False)

    def lastmod(self, obj):
        return obj.updated_at
