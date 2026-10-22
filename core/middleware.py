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
