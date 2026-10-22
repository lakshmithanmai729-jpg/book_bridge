import io
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from .images import MAX_UPLOAD_BYTES, optimize_upload
from .models import Book, Category, Report, Wishlist


def make_image_bytes(size=(1600, 2200), color=(20, 90, 160), fmt='JPEG'):
    buffer = io.BytesIO()
    Image.new('RGB', size, color).save(buffer, fmt, quality=92)
    return buffer.getvalue()


class BookListPaginationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.seller = User.objects.create_user('seller', password='Bridge!2345')
        cls.category = Category.objects.create(name='IIT-JEE')
        for i in range(25):
            Book.objects.create(
                seller=cls.seller,
                title=f'Book {i:02d}',
                author='Author',
                price=100 + i,
                category=cls.category,
                location_city='Hyderabad',
            )
        # hidden + sold books must never appear in the public list
        Book.objects.create(seller=cls.seller, title='Sold book', author='A', price=10, is_sold=True)
        Book.objects.create(seller=cls.seller, title='Hidden book', author='A', price=10, is_hidden=True)

    def test_first_page_has_twenty_books(self):
        response = self.client.get(reverse('books:book_list'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['books']), 20)
        self.assertEqual(response.context['result_count'], 25)

    def test_second_page_has_remaining_books(self):
        response = self.client.get(reverse('books:book_list'), {'page': 2})
        self.assertEqual(len(response.context['books']), 5)

    def test_sold_and_hidden_books_are_excluded(self):
        response = self.client.get(reverse('books:book_list'))
        titles = [book.title for book in response.context['books']]
        self.assertNotIn('Sold book', titles)
        self.assertNotIn('Hidden book', titles)

    def test_search_and_filters(self):
        response = self.client.get(reverse('books:book_list'), {'q': 'Book 01'})
        self.assertEqual(response.context['result_count'], 1)

        response = self.client.get(reverse('books:book_list'), {'min_price': 120, 'max_price': 124})
        self.assertEqual(response.context['result_count'], 5)

    def test_invalid_page_number_is_safe(self):
        response = self.client.get(reverse('books:book_list'), {'page': 'abc'})
        self.assertEqual(response.status_code, 200)

    def test_pagination_keeps_filters_in_links(self):
        response = self.client.get(reverse('books:book_list'), {'category': self.category.id})
        self.assertEqual(response.context['result_count'], 25)
        self.assertIn('category=', response.context['query_without_page'])


class MarkSoldTests(TestCase):
    def setUp(self):
        self.seller = User.objects.create_user('seller', password='Bridge!2345')
        self.other = User.objects.create_user('other', password='Bridge!2345')
        self.book = Book.objects.create(seller=self.seller, title='Atomic Habits', author='James Clear', price=190)

    def test_seller_can_mark_sold_and_relist(self):
        self.client.force_login(self.seller)
        response = self.client.post(reverse('books:toggle_sold', args=[self.book.pk]))
        self.assertRedirects(response, reverse('books:my_listings'))

        self.book.refresh_from_db()
        self.assertTrue(self.book.is_sold)
        self.assertIsNotNone(self.book.sold_at)
        self.assertEqual(self.book.status_label, 'Sold')

        self.client.post(reverse('books:toggle_sold', args=[self.book.pk]))
        self.book.refresh_from_db()
        self.assertFalse(self.book.is_sold)
        self.assertIsNone(self.book.sold_at)

    def test_other_user_cannot_mark_sold(self):
        self.client.force_login(self.other)
        response = self.client.post(reverse('books:toggle_sold', args=[self.book.pk]))
        self.assertEqual(response.status_code, 404)
        self.book.refresh_from_db()
        self.assertFalse(self.book.is_sold)

    def test_get_request_is_rejected(self):
        self.client.force_login(self.seller)
        response = self.client.get(reverse('books:toggle_sold', args=[self.book.pk]))
        self.assertEqual(response.status_code, 405)

    def test_sold_book_shows_banner_and_hides_contact(self):
        self.book.mark_sold(True)
        response = self.client.get(reverse('books:book_detail', args=[self.book.pk]))
        self.assertContains(response, 'This book has been sold')
        self.assertContains(response, 'Already sold')
        self.assertNotContains(response, '/accounts/chat/start/')
        self.assertNotContains(response, 't.me/')


class MyListingsTests(TestCase):
    def setUp(self):
        self.seller = User.objects.create_user('seller', password='Bridge!2345')
        self.active = Book.objects.create(seller=self.seller, title='Active book', author='A', price=100)
        self.sold = Book.objects.create(seller=self.seller, title='Sold book', author='A', price=100, is_sold=True)
        Book.objects.create(seller=self.seller, title='Hidden book', author='A', price=100, is_hidden=True)

    def test_tabs_filter_listings(self):
        self.client.force_login(self.seller)

        response = self.client.get(reverse('books:my_listings'))
        self.assertEqual([b.title for b in response.context['books']], ['Active book'])

        response = self.client.get(reverse('books:my_listings'), {'tab': 'sold'})
        self.assertEqual([b.title for b in response.context['books']], ['Sold book'])

        response = self.client.get(reverse('books:my_listings'), {'tab': 'hidden'})
        self.assertEqual([b.title for b in response.context['books']], ['Hidden book'])

    def test_counts(self):
        self.client.force_login(self.seller)
        response = self.client.get(reverse('books:my_listings'))
        self.assertEqual(response.context['counts'], {'active': 1, 'sold': 1, 'hidden': 1, 'all': 3})

    def test_login_required(self):
        response = self.client.get(reverse('books:my_listings'))
        self.assertEqual(response.status_code, 302)


class ReportTests(TestCase):
    def setUp(self):
        self.seller = User.objects.create_user('seller', password='Bridge!2345')
        self.buyer = User.objects.create_user('buyer', password='Bridge!2345')
        self.book = Book.objects.create(seller=self.seller, title='Suspicious', author='A', price=100)

    def test_buyer_can_report_listing(self):
        self.client.force_login(self.buyer)
        response = self.client.post(
            reverse('books:report_book', args=[self.book.pk]),
            {'reason': 'scam', 'details': 'Asked for advance payment'},
        )
        self.assertRedirects(response, reverse('books:book_detail', args=[self.book.pk]))

        report = Report.objects.get()
        self.assertEqual(report.reason, 'scam')
        self.assertEqual(report.status, Report.STATUS_OPEN)
        self.assertEqual(report.reporter, self.buyer)

    def test_duplicate_report_is_blocked(self):
        self.client.force_login(self.buyer)
        url = reverse('books:report_book', args=[self.book.pk])
        self.client.post(url, {'reason': 'fake'})
        self.client.post(url, {'reason': 'spam'})
        self.assertEqual(Report.objects.count(), 1)

    def test_owner_cannot_report_own_listing(self):
        self.client.force_login(self.seller)
        response = self.client.get(reverse('books:report_book', args=[self.book.pk]))
        self.assertRedirects(response, reverse('books:book_detail', args=[self.book.pk]))
        self.assertEqual(Report.objects.count(), 0)

    def test_invalid_reason_falls_back_to_other(self):
        self.client.force_login(self.buyer)
        self.client.post(reverse('books:report_book', args=[self.book.pk]), {'reason': 'nonsense'})
        self.assertEqual(Report.objects.get().reason, 'other')

    def test_hidden_listing_hides_from_public_but_not_owner(self):
        self.book.is_hidden = True
        self.book.save(update_fields=['is_hidden'])

        anon = self.client.get(reverse('books:book_detail', args=[self.book.pk]))
        self.assertEqual(anon.status_code, 404)

        self.client.force_login(self.seller)
        owner = self.client.get(reverse('books:book_detail', args=[self.book.pk]))
        self.assertEqual(owner.status_code, 200)
        self.assertContains(owner, 'hidden by moderators')


class ImageProcessingTests(TestCase):
    def test_upload_is_converted_to_smaller_webp(self):
        raw = make_image_bytes((2400, 3200))
        upload = SimpleUploadedFile('photo.jpg', raw, content_type='image/jpeg')

        optimized = optimize_upload(upload)
        self.assertTrue(optimized.name.endswith('.webp'))
        self.assertLess(len(optimized.read()), len(raw))

    def test_resizes_large_dimensions(self):
        raw = make_image_bytes((3000, 4000))
        upload = SimpleUploadedFile('big.jpg', raw, content_type='image/jpeg')
        optimized = optimize_upload(upload)
        image = Image.open(io.BytesIO(optimized.read()))
        self.assertLessEqual(max(image.size), 1400)

    def test_rejects_non_image(self):
        upload = SimpleUploadedFile('evil.jpg', b'definitely not an image', content_type='image/jpeg')
        with self.assertRaises(ValidationError):
            optimize_upload(upload)

    def test_rejects_oversized_file(self):
        upload = SimpleUploadedFile('huge.jpg', b'0' * (MAX_UPLOAD_BYTES + 1), content_type='image/jpeg')
        with self.assertRaises(ValidationError):
            optimize_upload(upload)


@override_settings(MEDIA_ROOT='/tmp/bookbridge-test-media')
class BookUploadTests(TestCase):
    def setUp(self):
        self.seller = User.objects.create_user('seller', password='Bridge!2345')
        self.client.force_login(self.seller)

    def test_cover_and_gallery_are_stored_as_webp(self):
        cover = SimpleUploadedFile('cover.jpg', make_image_bytes(), content_type='image/jpeg')
        extra = SimpleUploadedFile('extra.png', make_image_bytes(fmt='PNG'), content_type='image/png')

        response = self.client.post(reverse('books:book_add'), {
            'title': 'Compressed Cover',
            'author': 'QA',
            'price': '199',
            'condition': 'good',
            'location_city': 'Hyderabad',
            'location_area': 'Madhapur',
            'pincode': '500081',
            'image': cover,
            'images': [extra],
        })

        book = Book.objects.get(title='Compressed Cover')
        self.assertRedirects(response, reverse('books:book_detail', args=[book.pk]))
        self.assertTrue(book.image.name.endswith('.webp'))
        self.assertEqual(book.images.count(), 1)
        self.assertTrue(book.images.first().image.name.endswith('.webp'))

    def test_listing_requires_a_title(self):
        response = self.client.post(reverse('books:book_add'), {'title': '   ', 'price': '10'})
        self.assertEqual(response.status_code, 200)          # form shown again, not an error page
        self.assertContains(response, 'Please enter the book name.')
        self.assertEqual(Book.objects.count(), 0)

    def test_invalid_category_value_never_crashes_the_form(self):
        response = self.client.post(reverse('books:book_add'), {
            'title': 'No Category Book',
            'author': 'QA',
            'category': 'academic',      # stale/tampered value, not an id
            'price': '99',
            'condition': 'good',
        })
        book = Book.objects.get(title='No Category Book')
        self.assertRedirects(response, reverse('books:book_detail', args=[book.pk]))
        self.assertIsNone(book.category)

    def test_validation_error_keeps_what_the_seller_typed(self):
        response = self.client.post(reverse('books:book_add'), {
            'title': '',
            'author': 'H. C. Verma',
            'price': '250',
            'description': 'My typed description',
            'category': '5',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'H. C. Verma')
        self.assertContains(response, 'My typed description')
        self.assertContains(response, 'value="250"')


class PriceValidationTests(TestCase):
    """A price must never be saved outside the column's range.

    An oversized price used to be written to SQLite and then broke every page
    that rendered the book (decimal.InvalidOperation -> HTTP 500).
    """

    def setUp(self):
        # The rate limiter lives in the cache, which is not rolled back with the
        # database — clear it so these tests do not trip the listing throttle.
        cache.clear()
        self.seller = User.objects.create_user('seller', password='Bridge!2345')
        self.client.force_login(self.seller)

    def _post(self, price, **extra):
        data = {'title': 'Priced Book', 'author': 'QA', 'price': price, 'condition': 'good'}
        data.update(extra)
        return self.client.post(reverse('books:book_add'), data)

    def test_oversized_price_is_rejected_and_saved_nowhere(self):
        response = self._post('9' * 20)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'too high')
        self.assertEqual(Book.objects.count(), 0)

    def test_negative_price_is_rejected(self):
        response = self._post('-50')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'cannot be negative')
        self.assertEqual(Book.objects.count(), 0)

    def test_text_price_is_an_error_not_a_silent_zero(self):
        response = self._post('abc')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'as a number')
        self.assertEqual(Book.objects.count(), 0)

    def test_blank_price_is_an_error_unless_donation(self):
        response = self._post('')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Please enter a price')
        self.assertEqual(Book.objects.count(), 0)

    def test_reasonable_price_with_currency_symbol_is_accepted(self):
        response = self._post('₹1,299.50')
        book = Book.objects.get(title='Priced Book')
        self.assertEqual(book.price, Decimal('1299.50'))
        self.assertRedirects(response, reverse('books:book_detail', args=[book.pk]))

    def test_database_rejects_out_of_range_price_as_a_last_resort(self):
        with self.assertRaises(IntegrityError):
            Book.objects.create(seller=self.seller, title='Rogue', author='X', price=Decimal('1E+20'))

    def test_home_page_still_renders_with_extreme_but_valid_price(self):
        Book.objects.create(seller=self.seller, title='Max', author='X', price=Decimal('999999.99'))
        self.assertEqual(self.client.get(reverse('books:book_list')).status_code, 200)

    def test_overlong_title_is_rejected_instead_of_truncated(self):
        response = self._post('199', title='T' * 400)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'too long')
        self.assertEqual(Book.objects.count(), 0)

    def test_overlong_phone_is_rejected(self):
        response = self._post('199', contact_phone='9' * 40)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'too long')
        self.assertEqual(Book.objects.count(), 0)


class WishlistTests(TestCase):
    def setUp(self):
        self.seller = User.objects.create_user('seller', password='Bridge!2345')
        self.buyer = User.objects.create_user('buyer', password='Bridge!2345')
        self.book = Book.objects.create(seller=self.seller, title='Saved', author='A', price=100)

    def test_toggle_adds_and_removes(self):
        self.client.force_login(self.buyer)
        url = reverse('books:wishlist_toggle', args=[self.book.pk])

        self.client.post(url)
        self.assertTrue(Wishlist.objects.filter(user=self.buyer, book=self.book).exists())

        self.client.post(url)
        self.assertFalse(Wishlist.objects.filter(user=self.buyer, book=self.book).exists())

    def test_get_does_not_change_the_wishlist(self):
        """Link prefetchers and old bookmarks must not toggle saved books."""
        self.client.force_login(self.buyer)
        url = reverse('books:wishlist_toggle', args=[self.book.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 405)
        self.assertFalse(Wishlist.objects.filter(user=self.buyer, book=self.book).exists())

    def test_wishlist_page_lists_items(self):
        Wishlist.objects.create(user=self.buyer, book=self.book)
        self.client.force_login(self.buyer)
        response = self.client.get(reverse('books:wishlist'))
        self.assertContains(response, 'Saved')


class ThumbnailTests(TestCase):
    def setUp(self):
        self.seller = User.objects.create_user('seller', password='Bridge!2345')
        self.book = Book.objects.create(
            seller=self.seller,
            title='With cover',
            author='A',
            price=100,
            image=SimpleUploadedFile('cover.jpg', make_image_bytes((900, 1200)), content_type='image/jpeg'),
        )

    def test_list_page_uses_generated_thumbnail(self):
        response = self.client.get(reverse('books:book_list'))
        html = response.content.decode()
        self.assertIn('/media/thumbs/', html)
        self.assertIn('_400.webp', html)

    def test_missing_image_falls_back_to_empty_string(self):
        from .templatetags.book_extras import thumb

        self.assertEqual(thumb(None), '')
        self.assertEqual(thumb(''), '')


class SearchRankingTests(TestCase):
    def setUp(self):
        self.seller = User.objects.create_user('seller', password='Bridge!2345')
        self.title_match = Book.objects.create(
            seller=self.seller, title='Physics Galaxy', author='Other', price=100, condition='good',
        )
        self.author_match = Book.objects.create(
            seller=self.seller, title='Mechanics', author='Physics Academy', price=200, condition='good',
        )

    def test_title_matches_rank_before_author_matches(self):
        from django.conf import settings
        settings.ALLOWED_HOSTS = list(settings.ALLOWED_HOSTS) + ['testserver']
        response = self.client.get(reverse('books:book_list'), {'q': 'physics'})
        self.assertEqual(response.status_code, 200)
        results = list(response.context['books'])
        self.assertEqual(results[0].pk, self.title_match.pk)

    def test_explicit_sort_still_wins(self):
        from django.conf import settings
        settings.ALLOWED_HOSTS = list(settings.ALLOWED_HOSTS) + ['testserver']
        response = self.client.get(reverse('books:book_list'), {'q': 'physics', 'sort': 'price_high'})
        results = list(response.context['books'])
        self.assertEqual(results[0].pk, self.author_match.pk)


class SeoAndMetaTests(TestCase):
    def setUp(self):
        self.seller = User.objects.create_user('seller', password='Bridge!2345')
        self.book = Book.objects.create(
            seller=self.seller, title='Visible Book', author='A', price=150, condition='good',
        )
        Book.objects.create(
            seller=self.seller, title='Sold Book', author='B', price=90, condition='good', is_sold=True,
        )

    def test_sitemap_lists_live_books_only(self):
        response = self.client.get('/sitemap.xml')
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn(f'/books/{self.book.pk}/', body)
        self.assertNotIn('/books/2/', body)

    def test_robots_txt_points_at_the_sitemap(self):
        response = self.client.get('/robots.txt')
        self.assertEqual(response.status_code, 200)
        self.assertIn('Sitemap:', response.content.decode())

    def test_web_manifest_is_served(self):
        response = self.client.get('/manifest.webmanifest')
        self.assertEqual(response.status_code, 200)
        self.assertIn('BookBridge', response.content.decode())

    def test_book_detail_has_social_meta(self):
        response = self.client.get(reverse('books:book_detail', args=[self.book.pk]))
        body = response.content.decode()
        self.assertIn('og:title', body)
        self.assertIn('Visible Book', body)
        self.assertIn('name="description"', body)

    def test_health_check_reports_ok(self):
        response = self.client.get('/healthz/')
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['status'], 'ok')
        self.assertEqual(payload['checks']['database'], 'ok')


class StaffDashboardTests(TestCase):
    def setUp(self):
        self.member = User.objects.create_user('member', password='Bridge!2345')
        self.staff = User.objects.create_user('staffer', password='Bridge!2345', is_staff=True)

    def test_anonymous_visitors_are_redirected_to_admin_login(self):
        response = self.client.get('/staff/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login/', response['Location'])

    def test_regular_members_cannot_open_it(self):
        self.client.force_login(self.member)
        response = self.client.get('/staff/')
        self.assertEqual(response.status_code, 302)

    def test_staff_see_the_numbers(self):
        Book.objects.create(
            seller=self.member, title='Dashboard Book', author='A', price=50, condition='good',
        )
        self.client.force_login(self.staff)
        response = self.client.get('/staff/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['stats']['listings'], 1)
        self.assertContains(response, 'Team dashboard')


class MediaServingTests(TestCase):
    """Book photos must load on the deployed site, not just in DEBUG."""

    def setUp(self):
        self.seller = User.objects.create_user('seller', password='Bridge!2345')

    def test_uploaded_photo_is_served_when_debug_is_off(self):
        from django.core.files.base import ContentFile

        book = Book.objects.create(seller=self.seller, title='With Photo', author='A', price=100)
        book.image.save('photo.jpg', ContentFile(b'jpeg-bytes'), save=True)

        with override_settings(DEBUG=False):
            response = self.client.get(book.image.url)

        self.assertEqual(response.status_code, 200)

    def test_missing_file_falls_back_to_the_placeholder(self):
        from django.template import Context, Template

        book = Book.objects.create(seller=self.seller, title='Lost Photo', author='A', price=100)
        book.image.name = 'book_images/does-not-exist.jpg'
        book.save(update_fields=['image'])

        rendered = Template('{% load book_extras %}{{ book.image|thumb:400 }}').render(
            Context({'book': book})
        )
        # Manifest storage may add a content hash to the file name.
        self.assertIn('book-placeholder', rendered)
        self.assertNotIn('does-not-exist.jpg', rendered)

    def test_placeholder_asset_exists(self):
        from django.contrib.staticfiles import finders

        self.assertIsNotNone(finders.find('icons/book-placeholder.svg'))
