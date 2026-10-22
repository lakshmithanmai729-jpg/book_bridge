from django.contrib.auth.models import User
from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from books.models import Book, Category

from .models import BookRequest, ChatMessage, Notification, SellerReview, UserBlock


class UserProfilePrivacyTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('buyer', password='Bridge!2345')

    def test_profile_is_created_automatically(self):
        self.assertTrue(hasattr(self.user, 'profile'))
        self.assertEqual(self.user.profile.contact_preference, 'in_app')

    def test_telegram_username_is_normalised(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('accounts:profile_edit'), {
            'name': 'Buyer One',
            'phone_number': '9876543210',
            'location': 'Hyderabad',
            'account_privacy': 'private',
            'telegram_username': 'https://t.me/@buyer_one',
            'contact_preference': 'telegram',
        })
        self.assertRedirects(response, reverse('accounts:profile'))
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.telegram_username, 'buyer_one')
        self.assertEqual(self.user.profile.telegram_url, 'https://t.me/buyer_one')
        self.assertEqual(self.user.profile.contact_preference, 'telegram')

    def test_invalid_contact_preference_falls_back_to_in_app(self):
        self.client.force_login(self.user)
        self.client.post(reverse('accounts:profile_edit'), {
            'name': 'Buyer One',
            'contact_preference': 'carrier-pigeon',
            'account_privacy': 'private',
        })
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.contact_preference, 'in_app')


class BookDetailPrivacyTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='IIT-JEE')
        self.seller = User.objects.create_user('seller', password='Bridge!2345')
        self.buyer = User.objects.create_user('buyer', password='Bridge!2345')
        self.book = Book.objects.create(
            seller=self.seller,
            category=self.category,
            title='Concepts of Physics',
            author='H. C. Verma',
            price=250,
            contact_phone='9876543210',
        )

    def _detail(self):
        return self.client.get(reverse('books:book_detail', args=[self.book.pk]))

    def test_telegram_button_and_phone_hidden(self):
        profile = self.seller.profile
        profile.telegram_username = '@hcverma_fan'
        profile.contact_preference = 'telegram'
        profile.save()

        response = self._detail()
        self.assertContains(response, 'https://t.me/hcverma_fan')
        self.assertContains(response, 'In-App Chat')
        self.assertNotContains(response, 'wa.me')
        self.assertNotContains(response, '9876543210')

    def test_whatsapp_only_when_seller_opts_in(self):
        profile = self.seller.profile
        profile.contact_preference = 'whatsapp'
        profile.save()

        response = self._detail()
        self.assertContains(response, 'wa.me/919876543210')
        self.assertContains(response, 'WhatsApp')

    def test_whatsapp_hidden_for_in_app_preference(self):
        self.seller.profile.contact_preference = 'in_app'
        self.seller.profile.save()

        response = self._detail()
        self.assertNotContains(response, 'wa.me')
        self.assertContains(response, 'Phone number hidden')


class ChatTests(TestCase):
    def setUp(self):
        self.seller = User.objects.create_user('seller', password='Bridge!2345')
        self.buyer = User.objects.create_user('buyer', password='Bridge!2345')
        self.book = Book.objects.create(
            seller=self.seller,
            title='Atomic Habits',
            author='James Clear',
            price=190,
        )

    def test_start_chat_opens_room_with_seller(self):
        self.client.force_login(self.buyer)
        response = self.client.get(reverse('accounts:start_chat', args=[self.book.pk]))
        self.assertRedirects(
            response,
            f"{reverse('accounts:chat_detail', args=[self.seller.pk])}?book={self.book.pk}",
            fetch_redirect_response=False,
        )

    def test_buyer_can_send_message_and_seller_sees_it(self):
        self.client.force_login(self.buyer)
        url = reverse('accounts:chat_detail', args=[self.seller.pk])
        response = self.client.post(url, {'text': 'Is this still available?', 'book': self.book.pk})
        self.assertRedirects(response, f'{url}?book={self.book.pk}', fetch_redirect_response=False)

        message = ChatMessage.objects.get()
        self.assertEqual(message.sender, self.buyer)
        self.assertEqual(message.receiver, self.seller)
        self.assertFalse(message.is_read)

        self.client.force_login(self.seller)
        seller_room = reverse('accounts:chat_detail', args=[self.buyer.pk])
        self.client.get(f'{seller_room}?book={self.book.pk}')
        message.refresh_from_db()
        self.assertTrue(message.is_read)

    def test_cannot_chat_with_yourself(self):
        self.client.force_login(self.buyer)
        response = self.client.get(reverse('accounts:chat_detail', args=[self.buyer.pk]))
        self.assertRedirects(response, reverse('accounts:messages'))

    def test_empty_messages_state(self):
        self.client.force_login(self.buyer)
        response = self.client.get(reverse('accounts:messages'))
        self.assertContains(response, 'No Chats yet')
        self.assertContains(response, 'Buyers queries regarding your books will appear here')

    def test_messages_list_shows_active_chats(self):
        ChatMessage.objects.create(
            sender=self.buyer, receiver=self.seller, book=self.book, text='Hello!'
        )
        self.client.force_login(self.buyer)
        response = self.client.get(reverse('accounts:messages'))
        self.assertContains(response, 'Active chats')
        self.assertContains(response, 'Atomic Habits')
        self.assertNotContains(response, 'No Chats yet')


class BookRequestTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('student', password='Bridge!2345')

    def test_request_page_handles_get(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('accounts:request_book'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Request a Book')

    def test_post_creates_book_request(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('accounts:request_book'), {
            'book_title': 'Organic Chemistry',
            'category': 'NEET',
            'location': 'Dhone',
            'notes': 'Need the 7th edition',
        })
        self.assertRedirects(response, reverse('accounts:request_book'))
        request_obj = BookRequest.objects.get()
        self.assertEqual(request_obj.user, self.user)
        self.assertEqual(request_obj.book_title, 'Organic Chemistry')

    def test_blank_title_is_rejected(self):
        self.client.force_login(self.user)
        self.client.post(reverse('accounts:request_book'), {'book_title': '   '})
        self.assertEqual(BookRequest.objects.count(), 0)


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class EmailVerificationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            'newbie', email='newbie@example.com', password='Bridge!2345'
        )

    def test_signup_sends_verification_email(self):
        response = self.client.post(reverse('accounts:signup'), {
            'username': 'fresh',
            'email': 'fresh@example.com',
            'password1': 'Bridge!2345',
            'password2': 'Bridge!2345',
        })
        self.assertRedirects(response, reverse('accounts:login'))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Confirm your BookBridge email address', mail.outbox[0].subject)
        self.assertIn('/accounts/email/verify/', mail.outbox[0].body)

    def test_valid_token_marks_email_verified(self):
        from .emails import make_verification_token

        token = make_verification_token(self.user)
        self.client.force_login(self.user)
        response = self.client.get(reverse('accounts:verify_email', args=[token]))
        self.assertRedirects(response, reverse('accounts:profile'))

        self.user.profile.refresh_from_db()
        self.assertTrue(self.user.profile.email_verified)

    def test_invalid_token_does_not_verify(self):
        self.client.force_login(self.user)
        self.client.get(reverse('accounts:verify_email', args=['not-a-token']))
        self.user.profile.refresh_from_db()
        self.assertFalse(self.user.profile.email_verified)

    def test_resend_requires_post(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse('accounts:resend_verification')).status_code, 302)
        self.assertEqual(len(mail.outbox), 0)

    def test_resend_sends_new_link(self):
        self.client.force_login(self.user)
        self.client.post(reverse('accounts:resend_verification'))
        self.assertEqual(len(mail.outbox), 1)


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class PasswordResetTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            'forgetful', email='forgetful@example.com', password='Bridge!2345'
        )

    def test_reset_page_renders(self):
        response = self.client.get(reverse('accounts:password_reset'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Forgot your password?')

    def test_reset_email_is_sent_and_link_works(self):
        response = self.client.post(reverse('accounts:password_reset'), {'email': 'forgetful@example.com'})
        self.assertRedirects(response, reverse('accounts:password_reset_done'))
        self.assertEqual(len(mail.outbox), 1)

        body = mail.outbox[0].body
        path = body.split('http://testserver')[1].split()[0]
        response = self.client.get(path, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="new_password1"')

    def test_unknown_email_does_not_leak(self):
        response = self.client.post(reverse('accounts:password_reset'), {'email': 'nobody@example.com'})
        self.assertRedirects(response, reverse('accounts:password_reset_done'))
        self.assertEqual(len(mail.outbox), 0)


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class ChatNotificationTests(TestCase):
    def setUp(self):
        self.seller = User.objects.create_user('seller', email='seller@example.com', password='Bridge!2345')
        self.buyer = User.objects.create_user('buyer', email='buyer@example.com', password='Bridge!2345')
        self.book = Book.objects.create(seller=self.seller, title='Notify me', author='A', price=100)

    def test_verified_recipient_gets_email(self):
        self.seller.profile.email_verified = True
        self.seller.profile.save(update_fields=['email_verified'])
        mail.outbox = []

        self.client.force_login(self.buyer)
        self.client.post(
            reverse('accounts:chat_detail', args=[self.seller.pk]),
            {'text': 'Is this available?', 'book': self.book.pk},
        )

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('New message from buyer', mail.outbox[0].subject)
        self.assertIn('Is this available?', mail.outbox[0].body)

    def test_unverified_recipient_gets_no_email(self):
        self.seller.profile.email_verified = False
        self.seller.profile.save(update_fields=['email_verified'])
        mail.outbox = []

        self.client.force_login(self.buyer)
        self.client.post(
            reverse('accounts:chat_detail', args=[self.seller.pk]),
            {'text': 'Hello there', 'book': self.book.pk},
        )
        self.assertEqual(len(mail.outbox), 0)


# ---------------------------------------------------------------------------
# Phase 2 - trust & safety
# ---------------------------------------------------------------------------

class SellerReviewTests(TestCase):
    def setUp(self):
        cache.clear()
        self.seller = User.objects.create_user('seller', password='Bridge!2345')
        self.buyer = User.objects.create_user('buyer', password='Bridge!2345')
        self.other = User.objects.create_user('other', password='Bridge!2345')
        self.book = Book.objects.create(
            seller=self.seller, title='Physics Volume 1', author='H. C. Verma',
            price=250, condition='good',
        )
        self.client.force_login(self.buyer)

    def _say_hello(self):
        ChatMessage.objects.create(sender=self.buyer, receiver=self.seller, book=self.book, text='Hi')

    def test_seller_profile_is_public(self):
        response = self.client.get(reverse('accounts:seller_profile', args=[self.seller.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Seller profile')
        self.assertContains(response, 'Physics Volume 1')

    def test_review_requires_a_conversation(self):
        response = self.client.get(reverse('accounts:review_seller', args=[self.seller.pk]))
        self.assertRedirects(response, reverse('accounts:seller_profile', args=[self.seller.pk]))

        self.client.post(reverse('accounts:review_seller', args=[self.seller.pk]), {
            'rating': '5', 'comment': 'Great',
        })
        self.assertEqual(SellerReview.objects.count(), 0)

    def test_review_is_saved_after_chatting(self):
        self._say_hello()
        response = self.client.post(reverse('accounts:review_seller', args=[self.seller.pk]), {
            'rating': '5', 'comment': 'Very smooth deal',
        })
        self.assertRedirects(response, reverse('accounts:seller_profile', args=[self.seller.pk]))

        review = SellerReview.objects.get(seller=self.seller, reviewer=self.buyer)
        self.assertEqual(review.rating, 5)
        self.assertEqual(review.book, self.book)

        profile_page = self.client.get(reverse('accounts:seller_profile', args=[self.seller.pk]))
        self.assertContains(profile_page, 'Very smooth deal')

    def test_second_review_updates_instead_of_duplicating(self):
        self._say_hello()
        url = reverse('accounts:review_seller', args=[self.seller.pk])
        self.client.post(url, {'rating': '3', 'comment': 'Okay'})
        self.client.post(url, {'rating': '5', 'comment': 'Actually great'})

        self.assertEqual(SellerReview.objects.filter(seller=self.seller, reviewer=self.buyer).count(), 1)
        review = SellerReview.objects.get(seller=self.seller, reviewer=self.buyer)
        self.assertEqual(review.rating, 5)
        self.assertEqual(review.comment, 'Actually great')

    def test_rating_outside_one_to_five_is_clamped(self):
        self._say_hello()
        self.client.post(reverse('accounts:review_seller', args=[self.seller.pk]), {
            'rating': '99', 'comment': 'Spammy score',
        })
        review = SellerReview.objects.get(seller=self.seller, reviewer=self.buyer)
        self.assertEqual(review.rating, 5)

    def test_hidden_reviews_are_excluded_from_the_average(self):
        self._say_hello()
        SellerReview.objects.create(reviewer=self.buyer, seller=self.seller, book=self.book, rating=5)
        SellerReview.objects.create(reviewer=self.other, seller=self.seller, book=self.book, rating=1)
        SellerReview.invalidate_summary(self.seller.pk)

        self.assertEqual(SellerReview.summary_for(self.seller)['average'], 3.0)

        SellerReview.objects.filter(rating=1).update(is_hidden=True)
        SellerReview.invalidate_summary(self.seller.pk)
        self.assertEqual(SellerReview.summary_for(self.seller)['average'], 5.0)

    def test_three_good_reviews_make_a_top_seller(self):
        third = User.objects.create_user('third', password='Bridge!2345')
        for reviewer, rating in ((self.buyer, 5), (self.other, 5), (third, 4)):
            SellerReview.objects.create(
                reviewer=reviewer, seller=self.seller, book=self.book, rating=rating,
            )
        SellerReview.invalidate_summary(self.seller.pk)

        self.assertTrue(self.seller.profile.is_top_seller)
        self.assertEqual(self.seller.profile.rating_count, 3)

    def test_seller_cannot_review_themselves(self):
        self.client.force_login(self.seller)
        ChatMessage.objects.create(sender=self.seller, receiver=self.buyer, book=self.book, text='Hi')
        response = self.client.post(reverse('accounts:review_seller', args=[self.seller.pk]), {
            'rating': '5',
        })
        self.assertRedirects(response, reverse('accounts:seller_profile', args=[self.seller.pk]))
        self.assertEqual(SellerReview.objects.count(), 0)


class UserBlockTests(TestCase):
    def setUp(self):
        cache.clear()
        self.seller = User.objects.create_user('seller', password='Bridge!2345')
        self.buyer = User.objects.create_user('buyer', password='Bridge!2345')
        self.book = Book.objects.create(
            seller=self.seller, title='Blocked Book', author='Someone', price=100, condition='good',
        )

    def test_blocking_hides_the_seller_listings(self):
        self.client.force_login(self.buyer)
        self.assertContains(self.client.get(reverse('books:book_list')), 'Blocked Book')

        self.client.post(reverse('accounts:toggle_block', args=[self.seller.pk]))

        self.assertTrue(UserBlock.objects.filter(blocker=self.buyer, blocked=self.seller).exists())
        listing = self.client.get(reverse('books:book_list'))
        self.assertNotContains(listing, 'Blocked Book')
        home = self.client.get(reverse('core:home'))
        self.assertNotContains(home, 'Blocked Book')
        detail = self.client.get(reverse('books:book_detail', args=[self.book.pk]))
        self.assertEqual(detail.status_code, 404)

    def test_unblocking_restores_the_listings(self):
        self.client.force_login(self.buyer)
        url = reverse('accounts:toggle_block', args=[self.seller.pk])
        self.client.post(url)
        self.client.post(url)

        self.assertFalse(UserBlock.objects.exists())
        self.assertContains(self.client.get(reverse('books:book_list')), 'Blocked Book')

    def test_chat_is_blocked_between_the_two_people(self):
        self.client.force_login(self.buyer)
        self.client.post(reverse('accounts:toggle_block', args=[self.seller.pk]))

        response = self.client.post(
            reverse('accounts:chat_detail', args=[self.seller.pk]),
            {'text': 'Are you there?', 'book': str(self.book.pk)},
        )
        self.assertRedirects(response, reverse('accounts:messages'))
        self.assertEqual(ChatMessage.objects.count(), 0)

    def test_cannot_block_yourself(self):
        self.client.force_login(self.buyer)
        response = self.client.post(reverse('accounts:toggle_block', args=[self.buyer.pk]))
        self.assertRedirects(response, reverse('accounts:profile'))
        self.assertFalse(UserBlock.objects.exists())

    def test_blocked_list_page_lists_them(self):
        self.client.force_login(self.buyer)
        self.client.post(reverse('accounts:toggle_block', args=[self.seller.pk]))
        response = self.client.get(reverse('accounts:blocked_users'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'seller')

    def test_blocking_requires_post(self):
        self.client.force_login(self.buyer)
        response = self.client.get(reverse('accounts:toggle_block', args=[self.seller.pk]))
        self.assertEqual(response.status_code, 405)
        self.assertFalse(UserBlock.objects.exists())


@override_settings(RATE_LIMITS={
    'chat': (2, 300),
    'listing': (1, 300),
    'report': (5, 300),
    'review': (10, 300),
    'request': (5, 300),
})
class RateLimitTests(TestCase):
    def setUp(self):
        cache.clear()
        self.seller = User.objects.create_user('seller', password='Bridge!2345')
        self.buyer = User.objects.create_user('buyer', password='Bridge!2345')
        self.client.force_login(self.buyer)

    def test_chat_messages_are_throttled(self):
        url = reverse('accounts:chat_detail', args=[self.seller.pk])
        for index in range(2):
            self.client.post(url, {'text': f'message {index}'})
        self.assertEqual(ChatMessage.objects.count(), 2)

        response = self.client.post(url, {'text': 'one too many'}, follow=True)
        self.assertEqual(ChatMessage.objects.count(), 2)
        self.assertContains(response, 'going a bit fast')

    def test_listing_creation_is_throttled(self):
        first = self.client.post(reverse('books:book_add'), {
            'title': 'First Listing', 'author': 'A', 'price': '10', 'condition': 'good',
        })
        self.assertEqual(first.status_code, 302)

        second = self.client.post(reverse('books:book_add'), {
            'title': 'Second Listing', 'author': 'B', 'price': '20', 'condition': 'good',
        })
        self.assertEqual(second.status_code, 200)
        self.assertFalse(Book.objects.filter(title='Second Listing').exists())


class SafetyCentreTests(TestCase):
    def test_safety_page_is_public(self):
        response = self.client.get(reverse('core:safety'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Safety Centre')
        self.assertContains(response, 'Report a listing')

    def test_anonymous_visitors_can_open_a_seller_profile(self):
        seller = User.objects.create_user('seller', password='Bridge!2345')
        response = self.client.get(reverse('accounts:seller_profile', args=[seller.pk]))
        self.assertEqual(response.status_code, 200)


# ---------------------------------------------------------------------------
# Phase 3 - notifications & seller analytics
# ---------------------------------------------------------------------------

class NotificationTests(TestCase):
    def setUp(self):
        cache.clear()
        self.seller = User.objects.create_user('seller', password='Bridge!2345')
        self.buyer = User.objects.create_user('buyer', password='Bridge!2345')
        self.book = Book.objects.create(
            seller=self.seller, title='Organic Chemistry', author='Morrison',
            price=400, condition='good', location_city='Hyderabad',
        )

    def test_price_drop_notifies_wishlist_users_only(self):
        from books.models import Wishlist
        Wishlist.objects.create(user=self.buyer, book=self.book)

        self.client.force_login(self.seller)
        self.client.post(reverse('books:book_edit', args=[self.book.pk]), {
            'title': self.book.title,
            'author': self.book.author,
            'price': '250',
            'condition': 'good',
        })

        note = Notification.objects.filter(recipient=self.buyer, kind='price_drop').first()
        self.assertIsNotNone(note)
        self.assertIn('250', note.body)
        self.assertFalse(Notification.objects.filter(recipient=self.seller, kind='price_drop').exists())

    def test_price_increase_does_not_notify(self):
        from books.models import Wishlist
        Wishlist.objects.create(user=self.buyer, book=self.book)

        self.client.force_login(self.seller)
        self.client.post(reverse('books:book_edit', args=[self.book.pk]), {
            'title': self.book.title,
            'author': self.book.author,
            'price': '500',
            'condition': 'good',
        })
        self.assertFalse(Notification.objects.filter(recipient=self.buyer, kind='price_drop').exists())

    def test_relisting_notifies_people_who_saved_the_book(self):
        from books.models import Wishlist
        Wishlist.objects.create(user=self.buyer, book=self.book)
        self.book.mark_sold(True)

        self.client.force_login(self.seller)
        self.client.post(reverse('books:toggle_sold', args=[self.book.pk]))

        self.assertTrue(
            Notification.objects.filter(recipient=self.buyer, kind='back_on_sale').exists()
        )

    def test_new_listing_matches_open_book_requests(self):
        BookRequest.objects.create(
            user=self.buyer, book_title='Organic Chemistry Morrison', category='NEET',
        )
        self.client.force_login(self.seller)
        self.client.post(reverse('books:book_add'), {
            'title': 'Organic Chemistry', 'author': 'Morrison', 'price': '300',
            'condition': 'good', 'location_city': 'Hyderabad',
        })
        self.assertTrue(
            Notification.objects.filter(recipient=self.buyer, kind='request_match').exists()
        )

    def test_review_notifies_the_seller(self):
        ChatMessage.objects.create(sender=self.buyer, receiver=self.seller, book=self.book, text='Hi')
        self.client.force_login(self.buyer)
        self.client.post(reverse('accounts:review_seller', args=[self.seller.pk]), {
            'rating': '5', 'comment': 'Great seller',
        })
        note = Notification.objects.filter(recipient=self.seller, kind='review').first()
        self.assertIsNotNone(note)
        self.assertIn('5-star', note.title)

    def test_blocked_people_do_not_get_notifications(self):
        from books.models import Wishlist
        Wishlist.objects.create(user=self.buyer, book=self.book)
        UserBlock.objects.create(blocker=self.buyer, blocked=self.seller)

        self.client.force_login(self.seller)
        self.client.post(reverse('books:book_edit', args=[self.book.pk]), {
            'title': self.book.title, 'author': self.book.author,
            'price': '100', 'condition': 'good',
        })
        self.assertFalse(Notification.objects.filter(recipient=self.buyer, kind='price_drop').exists())

    def test_bell_count_and_notification_page(self):
        Notification.objects.create(
            recipient=self.buyer, kind='system', title='Welcome to BookBridge',
        )
        self.client.force_login(self.buyer)
        response = self.client.get(reverse('accounts:notifications'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Welcome to BookBridge')
        self.assertEqual(response.context['unread_count'], 1)

    def test_opening_a_notification_marks_it_read(self):
        Notification.objects.create(
            recipient=self.buyer, kind='system', title='Hello', url='/books/',
        )
        note = Notification.objects.get(recipient=self.buyer)
        self.client.force_login(self.buyer)
        response = self.client.get(reverse('accounts:notification_open', args=[note.pk]))
        self.assertRedirects(response, '/books/')
        note.refresh_from_db()
        self.assertTrue(note.is_read)

    def test_mark_all_read(self):
        for index in range(3):
            Notification.objects.create(recipient=self.buyer, kind='system', title=f'Note {index}')
        self.client.force_login(self.buyer)
        self.client.post(reverse('accounts:notifications_read_all'))
        self.assertEqual(Notification.objects.filter(recipient=self.buyer, is_read=False).count(), 0)

    def test_members_cannot_open_someone_elses_notification(self):
        Notification.objects.create(recipient=self.seller, kind='system', title='Private')
        note = Notification.objects.get(recipient=self.seller)
        self.client.force_login(self.buyer)
        response = self.client.get(reverse('accounts:notification_open', args=[note.pk]))
        self.assertEqual(response.status_code, 404)


class SellerAnalyticsTests(TestCase):
    def setUp(self):
        cache.clear()
        self.seller = User.objects.create_user('seller', password='Bridge!2345')
        self.buyer = User.objects.create_user('buyer', password='Bridge!2345')
        self.book = Book.objects.create(
            seller=self.seller, title='Analytics Book', author='A', price=120, condition='good',
        )
        Book.objects.filter(pk=self.book.pk).update(views_count=7)

    def test_analytics_page_totals(self):
        from books.models import Wishlist
        Wishlist.objects.create(user=self.buyer, book=self.book)
        self.client.force_login(self.seller)
        response = self.client.get(reverse('accounts:seller_analytics'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_views'], 7)
        self.assertEqual(response.context['total_saves'], 1)
        self.assertEqual(response.context['active_count'], 1)

    def test_analytics_requires_login(self):
        response = self.client.get(reverse('accounts:seller_analytics'))
        self.assertEqual(response.status_code, 302)

    def test_my_listings_feedback_strip(self):
        self.client.force_login(self.seller)
        response = self.client.get(reverse('books:my_listings'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['feedback']['views'], 7)
