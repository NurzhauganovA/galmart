from rest_framework.pagination import PageNumberPagination, LimitOffsetPagination
from rest_framework.response import Response
from collections import OrderedDict


class StandardResultsSetPagination(PageNumberPagination):
    """Стандартная пагинация с расширенной информацией"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response(OrderedDict([
            ('links', OrderedDict([
                ('next', self.get_next_link()),
                ('previous', self.get_previous_link()),
                ('first', self.get_first_link()),
                ('last', self.get_last_link()),
            ])),
            ('pagination', OrderedDict([
                ('count', self.page.paginator.count),
                ('total_pages', self.page.paginator.num_pages),
                ('current_page', self.page.number),
                ('page_size', self.get_page_size(self.request)),
                ('has_next', self.page.has_next()),
                ('has_previous', self.page.has_previous()),
            ])),
            ('results', data)
        ]))

    def get_first_link(self):
        if not self.page.has_previous():
            return None
        url = self.request.build_absolute_uri()
        return self.replace_query_param(url, self.page_query_param, 1)

    def get_last_link(self):
        if not self.page.has_next():
            return None
        url = self.request.build_absolute_uri()
        return self.replace_query_param(
            url,
            self.page_query_param,
            self.page.paginator.num_pages
        )


class LargeResultsSetPagination(PageNumberPagination):
    """Пагинация для больших наборов данных"""
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 200


class SmallResultsSetPagination(PageNumberPagination):
    """Пагинация для маленьких наборов данных"""
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50