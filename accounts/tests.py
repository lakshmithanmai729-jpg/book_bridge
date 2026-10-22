from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from books.models import Book, Category

from .models import BookRequest, ChatMessage


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
