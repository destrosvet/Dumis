from django.conf import settings
from rest_framework.pagination import PageNumberPagination


class ArticlePagination(PageNumberPagination):
    page_size = getattr(settings, 'SVJIS_ARTICLE_PAGE_SIZE', 10)
