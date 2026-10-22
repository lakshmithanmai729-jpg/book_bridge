"""Middleware used only by ``scripts/preview_server.py``.

The Arena live preview loads the app in an embedded iframe from a different
origin, so the preview server has to:

* accept any ``Host`` header,
* skip the CSRF check (the iframe has no way to share our CSRF cookie),
* optionally sign every visitor in as the demo account.

None of this is safe in production, which is why it lives in a separate module
that is only imported when ``PREVIEW_MODE=1``.
"""


class PreviewMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.auto_login = None
        import os

        self.auto_login = os.environ.get('PREVIEW_AUTO_LOGIN') or None

    def __call__(self, request):
        request.csrf_processing_done = True

        if self.auto_login:
            user = getattr(request, 'user', None)
            if user is None or not user.is_authenticated:
                try:
                    from django.contrib.auth import login
                    from django.contrib.auth.models import User

                    demo = User.objects.filter(username=self.auto_login).first()
                    if demo is not None:
                        login(request, demo)
                        request.user = demo
                except Exception:      # database not ready yet — never break the page
                    pass

        return self.get_response(request)
