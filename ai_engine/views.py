from django.http import JsonResponse
from .utils import suggest_price


def suggest_price_api(request):
    category_id = request.GET.get('category')
    condition = request.GET.get('condition')
    price = suggest_price(category_id, condition)
    return JsonResponse({'suggested_price': price})
