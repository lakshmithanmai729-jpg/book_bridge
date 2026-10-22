from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

from books.models import Book, Category

from .forms import SignUpForm
from .models import BookRequest, ChatMessage, UserProfile


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
    return handle


def save_profile_from_post(request, profile_obj):
    """Shared handler for the profile / profile-edit forms."""
    name = request.POST.get('name', '').strip()
    phone_number = request.POST.get('phone_number', '').strip()
    email = request.POST.get('email', '').strip()
    location = request.POST.get('location', '').strip()
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

    if email:
        request.user.email = email
        request.user.save(update_fields=['email'])


def signup(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            UserProfile.objects.get_or_create(user=user, defaults={'name': user.username})
            messages.success(request, 'Welcome to BookBridge! Please sign in to continue.')
            return redirect('accounts:login')
    else:
        form = SignUpForm()
    return render(request, 'accounts/signup.html', {'form': form})


def user_login(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
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
        form = AuthenticationForm()
    return render(request, 'accounts/login.html', {'form': form})


def user_logout(request):
    logout(request)
    return redirect('core:home')


@login_required
def profile(request):
    profile_obj = get_profile(request.user)

    if request.method == 'POST':
        save_profile_from_post(request, profile_obj)
        messages.success(request, 'Profile saved successfully!')
        return redirect('accounts:profile')

    my_requests = BookRequest.objects.filter(user=request.user)[:5]
    my_books = Book.objects.filter(seller=request.user, is_sold=False).order_by('-created_at')[:6]
    return render(request, 'accounts/profile.html', {
        'profile': profile_obj,
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

    book_id = request.POST.get('book') or request.GET.get('book')
    book = None
    if book_id:
        book = Book.objects.filter(pk=book_id).first()

    if request.method == 'POST':
        text = (request.POST.get('text') or '').strip()
        if text:
            ChatMessage.objects.create(
                sender=request.user,
                receiver=other_user,
                book=book,
                text=text,
            )
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

    return render(request, 'accounts/chat_detail.html', {
        'other_user': other_user,
        'other_profile': get_profile(other_user),
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
