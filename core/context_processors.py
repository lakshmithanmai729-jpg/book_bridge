def unread_messages(request):
    """Expose the number of unread in-app messages to every template."""
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return {'unread_message_count': 0}

    try:
        from accounts.models import ChatMessage
        unread = ChatMessage.objects.filter(receiver=user, is_read=False).count()
    except Exception:  # database not migrated yet / during startup checks
        unread = 0
    return {'unread_message_count': unread}


def active_chats(request):
    """Expose how many distinct conversations the signed-in user has."""
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return {'active_chat_count': 0}

    try:
        from django.db.models import Q
        from accounts.models import ChatMessage
        rows = (
            ChatMessage.objects
            .filter(Q(sender=user) | Q(receiver=user))
            .values_list('sender_id', 'receiver_id', 'book_id')
            .distinct()
        )
        conversations = set()
        for sender_id, receiver_id, book_id in rows:
            other_id = receiver_id if sender_id == user.id else sender_id
            conversations.add((other_id, book_id))
        active = len(conversations)
    except Exception:
        active = 0
    return {'active_chat_count': active}
