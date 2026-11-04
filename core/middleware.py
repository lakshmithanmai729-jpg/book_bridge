"""Project-wide middleware."""


class NoStoreHTMLMiddleware:
    """Stop browsers and preview proxies from caching rendered HTML pages.

    BookBridge is a marketplace: after a seller saves a listing, marks a book
    sold or edits a profile, the very next page must show the new data.  HTML
    responses therefore always carry ``no-store``; static and media files keep
    their normal, cacheable headers.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        content_type = response.get('Content-Type', '')
        if content_type.startswith('text/html') and not response.has_header('Cache-Control'):
            response['Cache-Control'] = 'no-store, max-age=0, must-revalidate'
            response['Pragma'] = 'no-cache'
        return response


class AppHeaderMiddleware:
    """Stamp our own responses with ``X-BB-App: 1``.

    The service worker only stores HTML that carries this header.  Without it,
    a Render free instance that is still booting answers with *its* "spinning
    up" page — a real HTTP response — and the worker would happily cache that
    page and show it to the user again later.  With the header the worker can
    tell our app apart from the hosting layer's placeholder.

    It sits near the top of ``MIDDLEWARE``, so its response phase runs *last* —
    after ``NoStoreHTMLMiddleware`` — which means the header lands on every
    response, including the ``no-store`` HTML pages.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        try:
            response['X-BB-App'] = '1'
        except Exception:  # pragma: no cover - streaming edge cases
            pass
        return response
