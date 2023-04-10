from django.core.paginator import Paginator
from django.conf import settings


def paginate(request, obj):
    paginator = Paginator(obj, settings.POSTS_SHOW_AMOUNT)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return page_obj
