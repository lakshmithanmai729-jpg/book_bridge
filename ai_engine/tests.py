"""Tests for the offline AI layer.

These cover the maths (pricing, similarity, classification), the guardrails
(no invented data, no crashes on empty marketplaces) and the JSON endpoints.
"""
import json

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from books.models import Book, Category, Wishlist

from .answers import answer_question
from .assistant import parse_query, search
from .classify import predict_category
from .describe import draft_description
from .models import AIEvent
from .pricing import suggest_price
from .recommend import picks_for_user, similar_books
from .scope import classify_scope, refusal_message
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


class ScopeGuardTests(TestCase):
    """The guard decides what the assistant is allowed to talk about."""

    def test_book_questions_are_in_scope(self):
        questions = [
            'how much is HC Verma?',
            'NEET books under 300',
            'is this book available?',
            'cheapest novel',
            'who is selling organic chemistry',
            'how do I sell a book?',
            'is my phone number shown',
        ]
        for question in questions:
            with self.subTest(question=question):
                decision = classify_scope(question)
                self.assertTrue(decision['in_scope'], decision)
                self.assertNotEqual(decision['reason'], 'off_topic', decision)

    def test_off_topic_questions_are_refused(self):
        questions = [
            "what's the weather today?",
            'ipl score today',
            'who is the CM of Telangana?',
            'write a python program',
            'tell me a joke',
            'solve this equation for me',
        ]
        for question in questions:
            with self.subTest(question=question):
                decision = classify_scope(question)
                self.assertFalse(decision['in_scope'], decision)
                self.assertEqual(decision['reason'], 'off_topic')

    def test_a_book_word_always_wins(self):
        # "medical" is an off-topic group word, but the student is asking about
        # a book, so the book word must win.
        decision = classify_scope('which book for NEET biology')
        self.assertTrue(decision['in_scope'])

    def test_unknown_topics_are_attempted_rather_than_refused(self):
        # Silence is better than a wrong refusal: if we recognise nothing,
        # the search runs and the student sees real results.
        decision = classify_scope('zorblax quint')
        self.assertTrue(decision['in_scope'])
        self.assertEqual(decision['reason'], 'unknown')

    def test_greetings_are_friendly_not_refused(self):
        decision = classify_scope('hello sir')
        self.assertTrue(decision['in_scope'])
        self.assertTrue(decision['is_greeting'])

    def test_empty_question_is_flagged_not_answered(self):
        decision = classify_scope('   ')
        self.assertTrue(decision['is_empty'])
        self.assertEqual(decision['reason'], 'empty')

    def test_refusal_names_the_topic_and_offers_examples(self):
        message, suggestions = refusal_message('what is the weather today')
        self.assertIn('books', message.lower())
        self.assertIn('weather', message.lower())
        self.assertEqual(len(suggestions), 3)
        self.assertTrue(all(isinstance(item, str) and item for item in suggestions))

    def test_refusal_never_leaks_an_off_topic_answer(self):
        message, suggestions = refusal_message('ipl score today')
        for banned in ('23 degrees', 'sunny', 'cricket score'):
            self.assertNotIn(banned, message.lower())
        for item in suggestions:
            self.assertTrue(classify_scope(item)['in_scope'], item)

    def test_telugu_price_question_is_understood(self):
        decision = classify_scope('పుస్తకం ధర ఎంత?')
        self.assertTrue(decision['in_scope'])
        self.assertEqual(decision['intent'], 'price')


class AssistantAnswerTests(TestCase):
    """Every question gets an answer, and book questions get real data."""

    def setUp(self):
        self.seller = User.objects.create_user('seller', password='Bridge!2345')
        self.neet = Category.objects.create(name='NEET')
        self.jee = Category.objects.create(name='IIT-JEE')
        self.novels = Category.objects.create(name='Novels')
        Book.objects.create(seller=self.seller, title='NEET Biology', author='Allen',
                            price=250, category=self.neet, location_area='Madhapur',
                            location_city='Hyderabad', condition='good')
        Book.objects.create(seller=self.seller, title='JEE Physics', author='HC Verma',
                            price=400, category=self.jee, location_area='Ameerpet',
                            location_city='Hyderabad', condition='good')
        Book.objects.create(seller=self.seller, title='The Alchemist', author='Coelho',
                            price=90, category=self.novels, location_area='Ameerpet',
                            location_city='Hyderabad', condition='fair')

    def ask(self, question, viewer=None):
        result = answer_question(question, viewer=viewer)
        self.assertTrue(result['ok'])
        self.assertTrue(result['answer'])
        return result

    def test_price_question_returns_the_real_listing(self):
        result = self.ask('how much is HC Verma?')
        self.assertEqual(result['intent'], 'price')
        self.assertIn('400', result['answer'])
        self.assertEqual(result['books'][0]['title'], 'JEE Physics')

    def test_availability_question_is_answered_yes_or_no(self):
        result = self.ask('is NEET Biology available?')
        self.assertIn('Yes', result['answer'])
        self.assertEqual(result['books'][0]['title'], 'NEET Biology')

    def test_budget_answer_never_shows_a_book_above_the_budget(self):
        result = self.ask('NEET books under 300')
        self.assertTrue(result['books'])
        for card in result['books']:
            self.assertLessEqual(card['price'], 300)

    def test_budget_above_everything_explains_instead_of_crashing(self):
        result = self.ask('JEE books under 100')
        self.assertTrue(result['answer'])
        for card in result['books']:
            self.assertLessEqual(card['price'], 100)

    def test_cheapest_picks_the_lowest_price(self):
        result = self.ask('cheapest novel')
        self.assertEqual(result['intent'], 'cheapest')
        self.assertEqual(result['books'][0]['title'], 'The Alchemist')

    def test_cheapest_on_an_empty_shelf_falls_back_to_the_shop(self):
        Category.objects.create(name='Commerce')
        result = self.ask('cheapest commerce book')
        self.assertTrue(result['answer'])
        self.assertTrue(result['books'])

    def test_count_lists_books_not_availability(self):
        result = self.ask('how many books are there?')
        self.assertEqual(result['intent'], 'how_many')
        self.assertIn('3', result['answer'])

    def test_count_can_target_one_shelf(self):
        result = self.ask('how many NEET books are there?')
        self.assertEqual(result['intent'], 'how_many')
        self.assertIn('1', result['answer'])
        self.assertTrue(all(card['category'] == 'NEET' for card in result['books']))

    def test_seller_question_names_the_seller_and_protects_the_phone(self):
        result = self.ask('who is selling NEET Biology')
        self.assertEqual(result['intent'], 'seller')
        self.assertIn('seller', result['answer'].lower())
        self.assertNotRegex(result['answer'], r'\b\d{10}\b')

    def test_free_books_answer_only_lists_free_books(self):
        Book.objects.create(seller=self.seller, title='NEET Free Notes', author='Allen',
                            price=0, category=self.neet, is_donation=True)
        result = self.ask('free books')
        self.assertTrue(result['books'])
        self.assertTrue(all(card['is_donation'] for card in result['books']))

    def test_recommendation_respects_the_requested_shelf(self):
        result = self.ask('recommend a novel')
        self.assertEqual(result['intent'], 'recommend')
        self.assertTrue(result['books'])
        self.assertTrue(all(card['category'] == 'Novels' for card in result['books']))

    def test_recommendation_says_so_when_the_shelf_is_empty(self):
        Category.objects.create(name='Commerce')
        result = self.ask('recommend a commerce book')
        self.assertTrue(result['answer'])
        self.assertNotIn('Good picks', result['answer'])

    def test_price_question_without_a_title_asks_which_book(self):
        result = self.ask('పుస్తకం ధర ఎంత?')
        self.assertEqual(result['intent'], 'price')
        self.assertIn('Which book', result['answer'])
        self.assertEqual(result['books'], [])

    def test_greeting_gets_a_friendly_books_answer(self):
        result = self.ask('hello sir')
        self.assertEqual(result['intent'], 'greeting')
        self.assertIn('3', result['answer'])

    def test_off_topic_question_is_refused_calmly(self):
        result = self.ask('what is the weather today')
        self.assertTrue(result['refused'])
        self.assertFalse(result['in_scope'])
        self.assertIn('books', result['answer'].lower())
        self.assertEqual(len(result['suggestions']), 3)
        self.assertEqual(result['books'], [])

    def test_how_to_sell_never_shows_a_phone_number(self):
        result = self.ask('how do I sell a book?')
        self.assertEqual(result['intent'], 'how_to_sell')
        self.assertNotRegex(result['answer'], r'\b\d{10}\b')

    def test_empty_question_is_answered_with_examples(self):
        result = self.ask('')
        self.assertTrue(result['answer'])
        self.assertTrue(result['suggestions'])

    def test_a_broken_question_can_never_raise(self):
        for question in ('???', '\x00', 'x' * 300, '“”', 'book' * 40):
            with self.subTest(question=question[:20]):
                result = answer_question(question)
                self.assertTrue(result['ok'])
                self.assertTrue(result['answer'])

    def test_logged_in_user_still_gets_plain_answers(self):
        result = self.ask('cheapest book', viewer=self.seller)
        self.assertTrue(result['books'])


class AskApiTests(TestCase):
    """The endpoint the new panel talks to."""

    def setUp(self):
        self.seller = User.objects.create_user('seller', password='Bridge!2345')
        self.category = Category.objects.create(name='NEET')
        Book.objects.create(seller=self.seller, title='NEET Biology', author='Allen',
                            price=250, category=self.category, location_area='Madhapur')

    def test_ask_api_answers_a_book_question(self):
        response = self.client.get(reverse('ai_engine:ask_api'), {'q': 'how much is NEET Biology?'})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['ok'])
        self.assertTrue(data['in_scope'])
        self.assertFalse(data['refused'])
        self.assertIn('250', data['answer'])
        self.assertTrue(data['books'])

    def test_ask_api_refuses_an_off_topic_question(self):
        response = self.client.get(reverse('ai_engine:ask_api'), {'q': 'what is the weather today'})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['refused'])
        self.assertEqual(data['books'], [])
        self.assertEqual(len(data['suggestions']), 3)

    def test_ask_api_accepts_a_post(self):
        response = self.client.post(reverse('ai_engine:ask_api'), {'q': 'free books'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['ok'])

    def test_ask_api_is_happy_with_no_question(self):
        response = self.client.get(reverse('ai_engine:ask_api'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['answer'])

    def test_ask_api_logs_the_event(self):
        self.client.get(reverse('ai_engine:ask_api'), {'q': 'cheapest book'})
        self.assertTrue(AIEvent.objects.filter(kind=AIEvent.KIND_ASK).exists())

    def test_ask_api_works_for_anonymous_visitors(self):
        response = self.client.get(reverse('ai_engine:ask_api'), {'q': 'NEET books'})
        self.assertEqual(response.status_code, 200)

    def test_search_api_refuses_off_topic_instead_of_returning_nothing(self):
        response = self.client.get(reverse('ai_engine:search_api'), {'q': 'ipl score today'})
        data = response.json()
        self.assertTrue(data['refused'])
        self.assertEqual(data['count'], 0)
        self.assertTrue(data['answer'])

    def test_search_api_still_works_normally(self):
        response = self.client.get(reverse('ai_engine:search_api'), {'q': 'NEET books'})
        data = response.json()
        self.assertFalse(data.get('refused', False))
        self.assertEqual(data['count'], 1)

    def test_parse_api_reports_the_scope(self):
        response = self.client.get(reverse('ai_engine:parse_api'), {'q': 'tell me a joke'})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['scope']['in_scope'])
