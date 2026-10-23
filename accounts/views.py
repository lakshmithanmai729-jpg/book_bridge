from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.utils.http import url_has_allowed_host_and_scheme

from django.utils import timezone

from books.models import Book, Category
from core.ratelimit import throttled
from core.validation import clamp, length_error
from . import notify as notify_service

from .emails import (
    email_delivery_configured,
    mark_verified,
    notify_new_message,
    read_verification_token,
    send_verification_email,
)
from .forms import SignInForm, SignUpForm
from .models import BookRequest, ChatMessage, Notification, SellerReview, UserBlock, UserProfile


def get_profile(user):
    """Return the profile for a user, creating it if it is missing."""
    profile, _ = UserProfile.objects.get_or_create(
        user=user,
        defaults={'name': user.username},
    )
    return profile


def clean_telegram_username(raw_value):
    """Normalise '@MyHandle' / 't.me/MyHandle' into 'MyHandle'."""
    handle = (raw_value or '').strip()
    if not handle:
        return ''
    handle = handle.replace('https://t.me/', '').replace('http://t.me/', '')
    handle = handle.replace('t.me/', '').strip().lstrip('@').strip()
    return handle[:100]  # UserProfile.telegram_username max_length


def save_profile_from_post(request, profile_obj):
    """Shared handler for the profile / profile-edit forms."""
    name = clamp(request.POST.get('name', ''), 150)
    phone_number = clamp(request.POST.get('phone_number', ''), 20)
    email = clamp(request.POST.get('email', ''), 254)
    location = clamp(request.POST.get('location', ''), 255)
    privacy = request.POST.get('account_privacy', 'private')
    telegram_username = clean_telegram_username(request.POST.get('telegram_username'))
    contact_preference = request.POST.get('contact_preference', UserProfile.CONTACT_IN_APP)

    valid_privacy = {choice[0] for choice in UserProfile.PRIVACY_CHOICES}
    valid_contact = {choice[0] for choice in UserProfile.CONTACT_CHOICES}

    if name:
        profile_obj.name = name
    profile_obj.phone_number = phone_number
    profile_obj.location = location
    profile_obj.account_privacy = privacy if privacy in valid_privacy else 'private'
    profile_obj.telegram_username = telegram_username
    profile_obj.contact_preference = (
        contact_preference if contact_preference in valid_contact else UserProfile.CONTACT_IN_APP
    )
    profile_obj.save()

    if email and email != request.user.email:
        request.user.email = email
        request.user.save(update_fields=['email'])
        profile_obj.email_verified = False
        profile_obj.save(update_fields=['email_verified'])
        if send_verification_email(request.user, request):
            messages.info(request, f'We sent a confirmation link to {email}.')
        else:
            messages.warning(request, 'We could not send the confirmation email right now.')


def _signed_up(request, user, email_sent):
    """Finish a signup: a member should never have to log in twice."""
    UserProfile.objects.get_or_create(user=user, defaults={'name': user.username})
    login(request, user, backend='django.contrib.auth.backends.ModelBackend')

    greeting = f'Welcome to BookBridge, {user.username}! Your account is ready.'
    if email_sent:
        messages.success(request, f'{greeting} We sent a confirmation link to {user.email}.')
    elif user.email:
        messages.success(
            request,
            f'{greeting} You can confirm {user.email} later from your profile page.',
        )
    else:
        messages.success(request, greeting)
    return redirect('core:home')


def signup(request):
    form = SignUpForm(request.POST or None)

    if request.method == 'POST':
        # Validate first: that is what fills in ``existing_user`` when the
        # username is already taken.
        form_valid = form.is_valid()

        # A double tap, or a page that finally loaded after a slow cold start,
        # sends the same form twice. If the username already belongs to
        # somebody and the password matches, that is the same person — sign
        # them in instead of shouting "already exists".
        existing = getattr(form, 'existing_user', None)
        if existing is not None:
            password = request.POST.get('password1') or ''
            if password:
                person = authenticate(
                    request, username=existing.username, password=password
                )
                if person is not None:
                    UserProfile.objects.get_or_create(
                        user=person, defaults={'name': person.username}
                    )
                    login(request, person, backend='django.contrib.auth.backends.ModelBackend')
                    messages.info(
                        request,
                        f'You already had a BookBridge account as “{person.username}”, '
                        'so we signed you in.',
                    )
                    return redirect('core:home')

        if form_valid:
            try:
                user = form.save()
            except IntegrityError:
                # Two people picked the same username at the same moment.
                form.add_error(
                    'username',
                    'Somebody just took that username. Please choose another one.',
                )
            else:
                return _signed_up(
                    request, user, send_verification_email(user, request) if user.email else False
                )

    return render(request, 'accounts/signup.html', {
        'form': form,
        'existing_user': getattr(form, 'existing_user', None),
        'email_delivery_enabled': email_delivery_configured(),
    })


def user_login(request):
    if request.method == 'POST':
        form = SignInForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            UserProfile.objects.get_or_create(user=user, defaults={'name': user.username})
            next_url = request.POST.get('next') or request.GET.get('next')
            if next_url and url_has_allowed_host_and_scheme(
                next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
            ):
                return redirect(next_url)
            return redirect('core:home')
    else:
        form = SignInForm(request)
    return render(request, 'accounts/login.html', {'form': form})


def user_logout(request):
    logout(request)
    return redirect('core:home')


class BookBridgePasswordResetView(auth_views.PasswordResetView):
    """Django's reset form, plus an honest note when mail cannot be sent."""

    def get_initial(self):
        initial = super().get_initial()
        # The "Forgot password?" link carries the email we already know about.
        email = (self.request.GET.get('email') or '').strip()
        if email:
            initial['email'] = email
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['email_delivery_enabled'] = email_delivery_configured()
        return context


class BookBridgePasswordResetDoneView(auth_views.PasswordResetDoneView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['email_delivery_enabled'] = email_delivery_configured()
        return context


@login_required
def profile(request):
    profile_obj = get_profile(request.user)

    if request.method == 'POST':
        save_profile_from_post(request, profile_obj)
        messages.success(request, 'Profile saved successfully!')
        return redirect('accounts:profile')

    my_requests = BookRequest.objects.filter(user=request.user)[:5]
    my_books = Book.objects.filter(seller=request.user, is_sold=False).order_by('-created_at')[:6]
    my_rating = SellerReview.summary_for(request.user)
    rounded = int(round(my_rating['average']))
    return render(request, 'accounts/profile.html', {
        'profile': profile_obj,
        'my_rating': my_rating,
        'my_stars': {'full': range(rounded), 'empty': range(5 - rounded)},
        'user_books': my_books,
        'book_requests': my_requests,
        'contact_choices': UserProfile.CONTACT_CHOICES,
    })


@login_required
def profile_edit(request):
    profile_obj = get_profile(request.user)

    if request.method == 'POST':
        save_profile_from_post(request, profile_obj)
        messages.success(request, 'Profile saved successfully!')
        return redirect('accounts:profile')

    return render(request, 'accounts/profile_edit.html', {
        'profile': profile_obj,
        'contact_choices': UserProfile.CONTACT_CHOICES,
    })


def _build_conversations(user):
    """Group the user's messages into conversations (other user + book)."""
    chat_messages = (
        ChatMessage.objects
        .filter(Q(sender=user) | Q(receiver=user))
        .select_related('sender', 'receiver', 'book')
        .order_by('-created_at')
    )

    conversations = {}
    for message in chat_messages:
        other = message.receiver if message.sender_id == user.id else message.sender
        key = (other.id, message.book_id)
        if key not in conversations:
            conversations[key] = {
                'other': other,
                'other_profile': get_profile(other),
                'book': message.book,
                'last_message': message,
                'unread': 0,
            }
        if message.receiver_id == user.id and not message.is_read:
            conversations[key]['unread'] += 1

    return list(conversations.values())


@login_required
def messages_view(request):
    conversations = _build_conversations(request.user)
    return render(request, 'accounts/messages.html', {
        'conversations': conversations,
    })


@login_required
def start_chat(request, book_id):
    """Buyer taps “In-App Chat” on a listing → open the room with that seller."""
    book = get_object_or_404(Book, pk=book_id)

    if book.seller_id == request.user.id:
        messages.info(request, 'This is your own listing. Buyer chats will appear in Messages.')
        return redirect('accounts:messages')

    return redirect(f"{reverse('accounts:chat_detail', args=[book.seller_id])}?book={book.pk}")


@login_required
def chat_detail(request, user_id):
    """Conversation between the signed-in user and ``user_id`` (optionally about a book)."""
    other_user = get_object_or_404(User, pk=user_id)

    if other_user.id == request.user.id:
        messages.info(request, 'You cannot start a chat with yourself.')
        return redirect('accounts:messages')

    if UserBlock.exists_between(request.user, other_user):
        messages.error(
            request,
            'This conversation is unavailable because one of you blocked the other. '
            'Unblock from your profile to start chatting again.',
        )
        return redirect('accounts:messages')

    book_id = request.POST.get('book') or request.GET.get('book')
    book = None
    if book_id:
        book = Book.objects.filter(pk=book_id).first()

    if request.method == 'POST':
        text = (request.POST.get('text') or '').strip()
        limit_message = throttled(request, 'chat')
        if limit_message:
            messages.error(request, limit_message)
            return redirect(f"{reverse('accounts:chat_detail', args=[other_user.id])}"
                            + (f"?book={book.pk}" if book else ''))
        if text:
            ChatMessage.objects.create(
                sender=request.user,
                receiver=other_user,
                book=book,
                text=text,
            )
            notify_new_message(other_user, request.user, book, text)
            return redirect(f"{reverse('accounts:chat_detail', args=[other_user.id])}"
                            + (f"?book={book.pk}" if book else ''))
        messages.error(request, 'Please type a message before sending.')
        return redirect(f"{reverse('accounts:chat_detail', args=[other_user.id])}"
                        + (f"?book={book.pk}" if book else ''))

    conversation_qs = ChatMessage.objects.filter(
        Q(sender=request.user, receiver=other_user) |
        Q(sender=other_user, receiver=request.user)
    )
    if book:
        conversation_qs = conversation_qs.filter(book=book)

    conversation = list(conversation_qs.select_related('sender').order_by('created_at'))

    # Mark the other person's messages for this conversation as read.
    unread_messages = ChatMessage.objects.filter(
        sender=other_user, receiver=request.user, is_read=False
    )
    if book:
        unread_messages = unread_messages.filter(book=book)
    unread_messages.update(is_read=True)

    # Other listings this pair is talking about (quick switcher).
    related_books = (
        Book.objects
        .filter(chat_messages__in=ChatMessage.objects.filter(
            Q(sender=request.user, receiver=other_user) |
            Q(sender=other_user, receiver=request.user)
        ))
        .distinct()
    )

    other_profile = get_profile(other_user)
    seller_rating = SellerReview.summary_for(other_user)
    rounded = int(round(seller_rating['average']))

    return render(request, 'accounts/chat_detail.html', {
        'other_user': other_user,
        'other_profile': other_profile,
        'seller_rating': seller_rating,
        'seller_stars': {'full': range(rounded), 'empty': range(5 - rounded)},
        'can_review': _can_review(request.user, other_user),
        'my_review': SellerReview.objects.filter(reviewer=request.user, seller=other_user).first(),
        'is_blocked': UserBlock.is_blocked_by_me(request.user, other_user),
        'book': book,
        'conversation': conversation,
        'related_books': related_books,
    })


@login_required
def request_book(request):
    """Students ask BookBridge sellers for a book they need."""
    if request.method == 'POST':
        book_title = (request.POST.get('book_title') or '').strip()
        category = (request.POST.get('category') or '').strip()
        location = (request.POST.get('location') or '').strip()
        notes = (request.POST.get('notes') or '').strip()

        for value, limit, label in (
            (book_title, 200, 'Book title'),
            (category, 100, 'Category'),
            (location, 255, 'Location'),
        ):
            problem = length_error(value, limit, label)
            if problem:
                messages.error(request, problem)
                return redirect('accounts:request_book')

        limit_message = throttled(request, 'request')
        if limit_message:
            messages.error(request, limit_message)
            return redirect('accounts:request_book')

        if not book_title:
            messages.error(request, 'Please tell us which book you need.')
        else:
            BookRequest.objects.create(
                user=request.user,
                book_title=book_title,
                category=category,
                location=location or get_profile(request.user).location,
                notes=notes,
            )
            messages.success(
                request,
                f'Request for “{book_title}” submitted! Nearby students who have it will be notified.',
            )
            return redirect('accounts:request_book')

    my_requests = BookRequest.objects.filter(user=request.user)
    categories = Category.objects.all()
    return render(request, 'accounts/request_book.html', {
        'book_requests': my_requests,
        'categories': categories,
        'profile': get_profile(request.user),
    })


@login_required
def delete_book_request(request, pk):
    book_request = get_object_or_404(BookRequest, pk=pk, user=request.user)
    if request.method == 'POST':
        book_request.delete()
        messages.success(request, 'Book request removed.')
    return redirect('accounts:request_book')


@login_required
def verify_email(request, token):
    """Confirm an email address from the signed link sent at signup."""
    user_id = read_verification_token(token)

    if user_id is None:
        messages.error(request, 'This confirmation link is invalid or has expired. Please request a new one.')
        return redirect('accounts:profile')

    from django.contrib.auth import get_user_model

    user = get_user_model().objects.filter(pk=user_id).first()
    if user is None:
        messages.error(request, 'That account no longer exists.')
        return redirect('accounts:profile')

    mark_verified(user)
    messages.success(request, 'Your email address is confirmed. Thank you!')
    return redirect('accounts:profile')


@login_required
def resend_verification(request):
    """Re-send the confirmation email on request."""
    if request.method != 'POST':
        return redirect('accounts:profile')

    profile = get_profile(request.user)
    if profile.email_verified:
        messages.info(request, 'Your email is already confirmed.')
    elif not request.user.email:
        messages.error(request, 'Add an email address first.')
    elif send_verification_email(request.user, request):
        messages.success(request, f'Confirmation link sent to {request.user.email}.')
    else:
        messages.error(request, 'We could not send the email. Please try again later.')
    return redirect('accounts:profile')


# ---------------------------------------------------------------------------
# Phase 2 — trust & safety: seller profiles, ratings, blocking
# ---------------------------------------------------------------------------

def _can_review(reviewer, seller):
    """Only someone who actually chatted with the seller may rate them."""
    if not reviewer or not getattr(reviewer, 'is_authenticated', False):
        return False
    if reviewer.id == seller.id:
        return False
    if UserBlock.exists_between(reviewer, seller):
        return False
    return SellerReview.has_chatted_with(reviewer, seller)


def _conversation_book(me, other):
    """The book the two people last talked about (used to attach a review)."""
    last_message = (
        ChatMessage.objects
        .filter(Q(sender=me, receiver=other) | Q(sender=other, receiver=me))
        .exclude(book__isnull=True)
        .select_related('book')
        .order_by('-created_at')
        .first()
    )
    return last_message.book if last_message else None


def seller_profile(request, user_id):
    """Public seller page: trust badges, ratings and their live listings."""
    seller = get_object_or_404(User.objects.select_related('profile'), pk=user_id)
    profile_obj = get_profile(seller)

    is_me = request.user.is_authenticated and request.user.id == seller.id

    reviews = (
        SellerReview.objects
        .filter(seller=seller, is_hidden=False)
        .select_related('reviewer', 'book', 'reviewer__profile')
    )
    rating = SellerReview.summary_for(seller)
    rounded = int(round(rating['average']))
    rating_stars = {
        'full': range(rounded),
        'empty': range(5 - rounded),
    }

    listings = (
        Book.objects
        .filter(seller=seller, is_sold=False, is_hidden=False)
        .select_related('category')
        .order_by('-created_at')
    )
    if not is_me:
        blocked = UserBlock.blocked_ids_for(request.user)
        if blocked:
            listings = listings.exclude(seller_id__in=blocked)

    my_review = None
    if request.user.is_authenticated and not is_me:
        my_review = SellerReview.objects.filter(reviewer=request.user, seller=seller).first()

    blocked_me = False
    if request.user.is_authenticated and not is_me:
        blocked_me = UserBlock.objects.filter(blocker=seller, blocked=request.user).exists()

    wishlist_ids = []
    if request.user.is_authenticated:
        from books.models import Wishlist
        wishlist_ids = list(
            Wishlist.objects.filter(user=request.user).values_list('book_id', flat=True)
        )

    # Public visitors only ever see the privacy-safe name.
    display_name = profile_obj.name if is_me else profile_obj.public_name

    return render(request, 'accounts/seller_profile.html', {
        'seller': seller,
        'seller_profile': profile_obj,
        'display_name': display_name,
        'rating': rating,
        'rating_stars': rating_stars,
        'reviews': reviews[:20],
        'listings': listings[:12],
        'listing_total': listings.count(),
        'is_me': is_me,
        'can_review': _can_review(request.user, seller),
        'my_review': my_review,
        'blocked_me': blocked_me,
        'is_blocked': (request.user.is_authenticated and not is_me
                       and UserBlock.is_blocked_by_me(request.user, seller)),
        'wishlist_ids': wishlist_ids,
    })


@login_required
def review_seller(request, user_id):
    """Rate a seller after chatting with them. One review per buyer-seller pair."""
    seller = get_object_or_404(User, pk=user_id)

    if seller.id == request.user.id:
        messages.info(request, 'You cannot review yourself.')
        return redirect('accounts:seller_profile', user_id=seller.pk)

    if not _can_review(request.user, seller):
        messages.error(
            request,
            'You can rate a seller once you have chatted with them about a book.',
        )
        return redirect('accounts:seller_profile', user_id=seller.pk)

    existing = SellerReview.objects.filter(reviewer=request.user, seller=seller).first()

    if request.method == 'POST':
        limit_message = throttled(request, 'review')
        if limit_message:
            messages.error(request, limit_message)
            return redirect('accounts:review_seller', user_id=seller.pk)

        try:
            rating_value = int(request.POST.get('rating', '5'))
        except (TypeError, ValueError):
            rating_value = 5
        rating_value = max(1, min(5, rating_value))
        comment = (request.POST.get('comment') or '').strip()[:1200]

        if existing:
            existing.rating = rating_value
            existing.comment = comment
            existing.save(update_fields=['rating', 'comment'])
            message_text = 'Your rating was updated. Thank you!'
            review = existing
        else:
            review = SellerReview.objects.create(
                reviewer=request.user,
                seller=seller,
                book=_conversation_book(request.user, seller),
                rating=rating_value,
                comment=comment,
            )
            message_text = f'Thanks! You rated {get_profile(seller).name or seller.username}.'

        notify_service.notify_new_review(review)

        SellerReview.invalidate_summary(seller.pk)
        messages.success(request, message_text)
        return redirect('accounts:seller_profile', user_id=seller.pk)

    return render(request, 'accounts/review_seller.html', {
        'seller': seller,
        'seller_profile': get_profile(seller),
        'existing': existing,
        'rating_choices': range(1, 6),
    })


@login_required
@require_POST
def toggle_block(request, user_id):
    """Block or unblock another member (POST only)."""
    other = get_object_or_404(User, pk=user_id)

    if other.id == request.user.id:
        messages.info(request, 'You cannot block yourself.')
        return redirect('accounts:profile')

    block = UserBlock.objects.filter(blocker=request.user, blocked=other).first()
    if block:
        block.delete()
        messages.success(
            request,
            f'You unblocked {get_profile(other).name or other.username}.',
        )
    else:
        UserBlock.objects.create(blocker=request.user, blocked=other)
        messages.success(
            request,
            f'{get_profile(other).name or other.username} is blocked. '
            'Their listings and chats are now hidden from you.',
        )

    next_url = request.POST.get('next') or reverse('accounts:seller_profile', args=[other.pk])
    if not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        next_url = reverse('accounts:seller_profile', args=[other.pk])
    return redirect(next_url)


@login_required
def blocked_users(request):
    """Everything the member has blocked, with a one-tap unblock."""
    blocks = (
        UserBlock.objects
        .filter(blocker=request.user)
        .select_related('blocked', 'blocked__profile')
        .order_by('-created_at')
    )
    return render(request, 'accounts/blocked_users.html', {
        'blocks': blocks,
        'profile': get_profile(request.user),
    })


# ---------------------------------------------------------------------------
# Phase 3 — notification centre + seller analytics
# ---------------------------------------------------------------------------

@login_required
def notifications_list(request):
    """The bell menu: everything that happened around the member's books."""
    tab = request.GET.get('tab', 'all')
    queryset = Notification.objects.filter(recipient=request.user).select_related('actor', 'book')
    if tab == 'unread':
        queryset = queryset.filter(is_read=False)

    unread = Notification.objects.filter(recipient=request.user, is_read=False).count()
    return render(request, 'accounts/notifications.html', {
        'notifications': queryset[:60],
        'tab': tab,
        'unread_count': unread,
        'profile': get_profile(request.user),
    })


@login_required
def notification_open(request, pk):
    """Mark one notification as read and follow its link."""
    note = get_object_or_404(Notification, pk=pk, recipient=request.user)
    if not note.is_read:
        note.is_read = True
        note.save(update_fields=['is_read'])

    if note.url and url_has_allowed_host_and_scheme(
        note.url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return redirect(note.url)
    return redirect('accounts:notifications')


@login_required
@require_POST
def notifications_read_all(request):
    updated = Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    if updated:
        messages.success(request, f'Marked {updated} notification(s) as read.')
    return redirect('accounts:notifications')


@login_required
def seller_analytics(request):
    """Numbers sellers care about: views, saves, chats and conversion."""
    from django.db.models import Count

    books = (
        Book.objects
        .filter(seller=request.user)
        .select_related('category')
        .annotate(saves=Count('wishlist', distinct=True))
        .order_by('-created_at')
    )

    active = [book for book in books if not book.is_sold and not book.is_hidden]
    sold = [book for book in books if book.is_sold]

    total_views = sum(book.views_count for book in books)
    total_saves = sum(book.saves for book in books)

    chat_count = ChatMessage.objects.filter(
        Q(sender=request.user) | Q(receiver=request.user)
    ).values('sender_id', 'receiver_id', 'book_id').distinct().count()

    wishlisted_by_others = (
        Book.objects.filter(seller=request.user)
        .annotate(saves=Count('wishlist', distinct=True))
        .filter(saves__gt=0)
        .count()
    )

    top_books = sorted(books, key=lambda item: (item.views_count, item.saves), reverse=True)[:5]

    return render(request, 'accounts/seller_analytics.html', {
        'books': books[:20],
        'active_count': len(active),
        'sold_count': len(sold),
        'total_views': total_views,
        'total_saves': total_saves,
        'chat_count': chat_count,
        'wishlisted_by_others': wishlisted_by_others,
        'top_books': top_books,
        'profile': get_profile(request.user),
    })
