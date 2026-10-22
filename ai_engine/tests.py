"""Tests for the offline AI layer.

These cover the maths (pricing, similarity, classification), the guardrails
(no invented data, no crashes on empty marketplaces) and the JSON endpoints.
"""
import json

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from books.models import Book, Category, Wishlist

from .assistant import parse_query, search
from .classify import predict_category
from .describe import draft_description
from .models import AIEvent
from .pricing import suggest_price
from .recommend import picks_for_user, similar_books
from .text import build_idf, cosine, tokenize, vectorize
from .trust import assess_listing


class TextEngineTests(TestCase):
    def test_tokenize_drops_stopwords_and_single_letters(self):
        self.assertEqual(tokenize('The Book of a Physics!'), ['physics'])

    def test_cosine_is_one_for_identical_documents(self):
        docs = [tokenize('organic chemistry neet guide'), tokenize('jee physics mechanics')]
        idf = build_idf(docs)
        vector = vectorize(docs[0], idf)
        self.assertAlmostEqual(cosine(vector, vector), 1.0, places=6)

    def test_unrelated_documents_score_low(self):
        docs = [tokenize('organic chemistry neet guide'), tokenize('romance novel love story')]
        idf = build_idf(docs)
        left, right = vectorize(docs[0], idf), vectorize(docs[1], idf)
        self.assertLess(cosine(left, right), 0.2)


class PriceSuggestionTests(TestCase):
    def setUp(self):
        self.seller = User.objects.create_user('seller', password='Bridge!2345')
        self.category = Category.objects.create(name='NEET')
        for price, condition in [(200, 'good'), (240, 'good'), (220, 'like_new'), (260, 'good'), (180, 'fair')]:
            Book.objects.create(
                seller=self.seller, title=f'NEET Book {price}', author='A',
                price=price, condition=condition, category=self.category,
                location_area='Madhapur',
            )

    def test_suggestion_uses_comparables_and_a_sane_range(self):
        result = suggest_price(category_id=self.category.pk, condition='good', title='NEET Biology')
        self.assertEqual(result['basis'], 'comparables')
        self.assertGreaterEqual(result['sample_size'], 4)
        self.assertTrue(150 <= result['suggested_price'] <= 300)
        self.assertLess(result['low'], result['suggested_price'])
        self.assertGreater(result['high'], result['suggested_price'])
        self.assertTrue(0.0 <= result['confidence'] <= 1.0)

    def test_condition_changes_the_suggestion(self):
        good = suggest_price(category_id=self.category.pk, condition='good')['suggested_price']
        poor = suggest_price(category_id=self.category.pk, condition='poor')['suggested_price']
        self.assertLess(poor, good)

    def test_mrp_is_a_ceiling_when_there_is_nothing_to_compare(self):
        empty_category = Category.objects.create(name='Health')
        result = suggest_price(category_id=empty_category.pk, condition='good', original_price=1000)
        self.assertEqual(result['basis'], 'mrp')
        self.assertLessEqual(result['suggested_price'], 900)

    def test_empty_marketplace_still_returns_a_suggestion(self):
        Book.objects.all().delete()
        result = suggest_price(condition='good')
        self.assertGreater(result['suggested_price'], 0)
        self.assertEqual(result['basis'], 'market')

    def test_free_listings_are_not_used_as_comparables(self):
        Book.objects.create(
            seller=self.seller, title='Free NEET', author='A', price=0,
            is_donation=True, category=self.category,
        )
        result = suggest_price(category_id=self.category.pk, condition='good')
        self.assertTrue(all(item['price'] > 0 for item in result['comparables']))


class CategoryClassifierTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='NEET')
        self.seller = User.objects.create_user('seller', password='Bridge!2345')
        for title in ['NEET Biology Guide', 'NEET Previous Year Papers', 'NEET Physics']:
            Book.objects.create(seller=self.seller, title=title, author='Allen',
                                price=100, category=self.category)

    def test_keyword_driven_prediction(self):
        predictions = predict_category(title='NEET Biology Complete Guide')
        self.assertTrue(predictions)
        self.assertEqual(predictions[0]['name'], 'NEET')
        self.assertGreater(predictions[0]['confidence'], 0.5)

    def test_blank_title_returns_nothing_instead_of_guessing(self):
        self.assertEqual(predict_category(title='', description=''), [])

    def test_unknown_category_is_not_invented(self):
        names = {item['name'] for item in predict_category(title='NEET Biology')}
        self.assertTrue(names.issubset(set(Category.objects.values_list('name', flat=True))))


class DescriptionWriterTests(TestCase):
    def test_uses_only_the_facts_given(self):
        text = draft_description(
            title='Concepts of Physics', author='H. C. Verma', category='IIT-JEE',
            condition='good', price=250, original_price=500, area='Madhapur',
        )
        self.assertIn('Concepts of Physics', text)
        self.assertIn('H. C. Verma', text)
        self.assertIn('₹250', text)
        self.assertIn('Madhapur', text)
        self.assertNotIn('mint', text.lower())

    def test_donation_is_described_as_free(self):
        text = draft_description(title='Ikigai', condition='like_new', is_donation=True)
        self.assertIn('free', text.lower())

    def test_works_with_almost_no_input(self):
        text = draft_description(title='')
        self.assertTrue(len(text) > 40)


class AssistantTests(TestCase):
    def setUp(self):
        self.seller = User.objects.create_user('seller', password='Bridge!2345')
        self.neet = Category.objects.create(name='NEET')
        self.jee = Category.objects.create(name='IIT-JEE')
        Book.objects.create(seller=self.seller, title='NEET Biology', author='Allen',
                            price=250, category=self.neet, location_area='Madhapur',
                            location_city='Hyderabad')
        Book.objects.create(seller=self.seller, title='JEE Physics', author='HC Verma',
                            price=400, category=self.jee, location_area='Ameerpet',
                            location_city='Hyderabad')

    def test_budget_category_and_location_are_understood(self):
        parsed = parse_query('neet books under 300 in madhapur')
        self.assertEqual(parsed['filters']['category_name'], 'NEET')
        self.assertEqual(parsed['filters']['max_price'], 300)
        self.assertEqual(parsed['filters']['location'], 'Madhapur')
        self.assertTrue(parsed['understood'])

    def test_search_applies_the_filters(self):
        result = search('neet books under 300 in madhapur')
        self.assertEqual(result['count'], 1)
        self.assertEqual(result['results'][0].title, 'NEET Biology')

    def test_free_and_cheapest_are_understood(self):
        self.assertTrue(parse_query('free novels')['filters']['free'])
        self.assertEqual(parse_query('cheapest jee books')['filters']['sort'], 'price_low')

    def test_zero_results_relax_the_area_not_the_budget(self):
        result = search('neet books under 300 in kurnool')
        self.assertEqual(result['relaxed_location'], 'Kurnool')
        self.assertEqual(result['count'], 1)
        self.assertIn('Kurnool', result['explanation'])

    def test_blank_query_is_safe(self):
        result = search('')
        self.assertEqual(result['filters']['q'], '')


class TrustScoreTests(TestCase):
    def setUp(self):
        self.seller = User.objects.create_user('seller', password='Bridge!2345')
        self.category = Category.objects.create(name='Engineering')
        for price in (300, 320, 280, 310):
            Book.objects.create(seller=self.seller, title=f'Engineering Book {price}',
                                author='A', price=price, category=self.category)

    def test_clean_listing_scores_low(self):
        result = assess_listing(
            title='Operating Systems', description='Good condition, all pages intact, no writing.',
            price=300, category_id=self.category.pk, seller=self.seller, image_present=True,
        )
        self.assertEqual(result['level'], 'low')
        self.assertEqual(result['reasons'], [])

    def test_phone_number_in_description_is_flagged(self):
        result = assess_listing(
            title='Operating Systems', description='Call me on 9876543210 to buy fast.',
            price=300, category_id=self.category.pk, seller=self.seller,
        )
        self.assertEqual(result['level'], 'high')
        self.assertTrue(any('Phone number' in reason for reason in result['reasons']))

    def test_duplicate_listing_is_flagged(self):
        Book.objects.create(seller=self.seller, title='Operating Systems', author='Galvin', price=300)
        result = assess_listing(
            title='Operating Systems', description='Selling my copy of the Galvin book, good condition.',
            price=300, category_id=self.category.pk, seller=self.seller,
        )
        self.assertTrue(any('duplicate' in reason.lower() for reason in result['reasons']))

    def test_extreme_price_is_flagged(self):
        result = assess_listing(
            title='Operating Systems', description='Good condition, all pages intact, no writing.',
            price=5000, category_id=self.category.pk, seller=self.seller,
        )
        self.assertTrue(any('median' in reason for reason in result['reasons']))


class RecommendationTests(TestCase):
    def setUp(self):
        self.seller = User.objects.create_user('seller', password='Bridge!2345')
        self.buyer = User.objects.create_user('buyer', password='Bridge!2345')
        self.neet = Category.objects.create(name='NEET')
        self.novel = Category.objects.create(name='Novels')
        self.biology = Book.objects.create(seller=self.seller, title='NEET Biology Guide',
                                           author='Allen', price=200, category=self.neet)
        self.chemistry = Book.objects.create(seller=self.seller, title='NEET Chemistry Guide',
                                             author='Allen', price=220, category=self.neet)
        self.novel_book = Book.objects.create(seller=self.seller, title='Ikigai',
                                              author='Garcia', price=150, category=self.novel)

    def test_similar_books_prefers_the_same_category(self):
        results = similar_books(self.biology, limit=3)
        ids = [item['book'].pk for item in results]
        self.assertIn(self.chemistry.pk, ids)
        self.assertNotIn(self.biology.pk, ids)
        self.assertTrue(all(item['reason'] for item in results))

    def test_similar_books_never_recommend_hidden_listings(self):
        self.chemistry.is_hidden = True
        self.chemistry.save(update_fields=['is_hidden'])
        ids = [item['book'].pk for item in similar_books(self.biology, limit=5)]
        self.assertNotIn(self.chemistry.pk, ids)

    def test_picks_use_wishlist_history(self):
        Wishlist.objects.create(user=self.buyer, book=self.biology)
        picks = picks_for_user(self.buyer, limit=5)
        ids = [item['book'].pk for item in picks]
        self.assertIn(self.chemistry.pk, ids)
        self.assertNotIn(self.biology.pk, ids)   # already saved

    def test_picks_never_include_the_users_own_listing(self):
        picks = picks_for_user(self.seller, limit=5)
        self.assertFalse([item for item in picks if item['book'].seller_id == self.seller.pk])


class AIBlockingTests(TestCase):
    """Blocking a seller must hide their books from every AI surface too."""

    def setUp(self):
        from accounts.models import UserBlock

        self.buyer = User.objects.create_user('buyer', password='Bridge!2345')
        self.blocked = User.objects.create_user('blocked', password='Bridge!2345')
        self.category = Category.objects.create(name='NEET')
        self.book = Book.objects.create(
            seller=self.blocked, title='Blocked NEET Biology', author='X',
            price=200, category=self.category, location_area='Madhapur',
        )
        UserBlock.objects.create(blocker=self.buyer, blocked=self.blocked)

    def test_picks_skip_blocked_sellers(self):
        picks = picks_for_user(self.buyer, limit=10)
        self.assertNotIn(self.book.pk, [item['book'].pk for item in picks])

    def test_similar_books_skip_blocked_sellers(self):
        other = Book.objects.create(
            seller=User.objects.create_user('other', password='Bridge!2345'),
            title='Another NEET Book', author='Y', price=210, category=self.category,
        )
        results = similar_books(other, limit=10, viewer=self.buyer)
        self.assertNotIn(self.book.pk, [item['book'].pk for item in results])

    def test_assistant_search_skips_blocked_sellers(self):
        result = search('neet biology', viewer=self.buyer)
        self.assertNotIn(self.book.pk, [book.pk for book in result['results']])


class AIApiTests(TestCase):
    def setUp(self):
        self.seller = User.objects.create_user('seller', password='Bridge!2345')
        self.category = Category.objects.create(name='NEET')
        Book.objects.create(seller=self.seller, title='NEET Biology', author='Allen',
                            price=250, category=self.category, location_area='Madhapur')

    def test_price_api_returns_a_suggestion(self):
        response = self.client.get(reverse('ai_engine:price_api'), {
            'category': self.category.pk, 'condition': 'good', 'title': 'NEET',
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['ok'])
        self.assertIn('suggested_price', data)
        self.assertIn('explanation', data)

    def test_price_api_survives_garbage_parameters(self):
        response = self.client.get(reverse('ai_engine:price_api'), {
            'category': 'not-a-number', 'condition': '../../etc', 'original_price': 'abc',
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['ok'])

    def test_describe_api_returns_a_draft(self):
        response = self.client.post(
            reverse('ai_engine:describe_api'),
            data=json.dumps({'title': 'Ikigai', 'condition': 'good', 'price': 150}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('Ikigai', response.json()['description'])

    def test_describe_api_needs_post(self):
        self.assertEqual(self.client.get(reverse('ai_engine:describe_api')).status_code, 405)

    def test_classify_api_returns_categories(self):
        response = self.client.post(
            reverse('ai_engine:classify_api'),
            data=json.dumps({'title': 'NEET Biology Complete Guide'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['categories'])

    def test_risk_api_requires_login(self):
        self.assertEqual(self.client.post(reverse('ai_engine:risk_api')).status_code, 302)

    def test_risk_api_works_for_a_logged_in_seller(self):
        self.client.force_login(self.seller)
        response = self.client.post(
            reverse('ai_engine:risk_api'),
            data=json.dumps({'title': 'NEET Biology', 'description': 'Good copy', 'price': 250}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(response.json()['level'], {'low', 'medium', 'high'})

    def test_search_api_returns_results_and_understood_filters(self):
        response = self.client.get(reverse('ai_engine:search_api'), {'q': 'neet under 300'})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['ok'])
        self.assertGreaterEqual(data['count'], 1)
        self.assertTrue(data['understood'])

    def test_search_api_rejects_an_empty_query(self):
        response = self.client.get(reverse('ai_engine:search_api'), {'q': '   '})
        self.assertEqual(response.status_code, 400)

    def test_similar_api_lists_other_books(self):
        other = Book.objects.create(seller=self.seller, title='NEET Chemistry',
                                    author='Allen', price=240, category=self.category)
        response = self.client.get(reverse('ai_engine:similar_api', args=[other.pk]))
        data = response.json()
        self.assertTrue(data['ok'])
        self.assertTrue(any(item['id'] != other.pk for item in data['results']))

    def test_every_call_is_logged_without_personal_data(self):
        self.client.get(reverse('ai_engine:price_api'), {'category': self.category.pk})
        event = AIEvent.objects.filter(kind='price').first()
        self.assertIsNotNone(event)
        self.assertNotIn('title', event.payload)


class AIHubPageTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('student', password='Bridge!2345')
        self.category = Category.objects.create(name='Novels')
        Book.objects.create(seller=self.user, title='Ikigai', author='Garcia',
                            price=150, category=self.category)

    def test_hub_loads_for_anonymous_visitors(self):
        response = self.client.get(reverse('ai_engine:hub'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ask the assistant')

    def test_hub_shows_picks_for_a_logged_in_user(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('ai_engine:hub'))
        self.assertEqual(response.status_code, 200)

    def test_home_page_renders_with_ai_picks(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('core:home'))
        self.assertEqual(response.status_code, 200)
