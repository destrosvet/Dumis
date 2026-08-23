from django.conf import settings
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .. import models
from ..permissions import svjis_answer_survey
from ..views import get_article_filter, get_top_articles
from . import serializers
from .pagination import ArticlePagination
from .permissions import HasPermission


class ArticleListAPIView(generics.ListAPIView):
    serializer_class = serializers.ArticleListSerializer
    pagination_class = ArticlePagination

    def get_queryset(self):
        q = get_article_filter(self.request.user)
        queryset = models.Article.objects.select_related('author', 'menu').filter(q).distinct()

        menu_id = self.request.query_params.get('menu')
        if menu_id is not None:
            if not menu_id.isdigit():
                raise Http404
            menu = get_object_or_404(models.ArticleMenu, pk=menu_id)
            queryset = queryset.filter(menu=menu)

        search = self.request.query_params.get('search')
        if search:
            if not (3 <= len(search) <= 100):
                raise ValidationError({'search': _("Search keyword must be between 3 and 100 characters.")})
            queryset = queryset.filter(
                Q(header__icontains=search) | Q(perex__icontains=search) | Q(body__icontains=search)
            )

        return queryset


class TopArticlesAPIView(generics.ListAPIView):
    serializer_class = serializers.TopArticleSerializer
    pagination_class = None

    def get_queryset(self):
        q = get_article_filter(self.request.user)
        visible_ids = list(models.Article.objects.filter(q).values_list('id', flat=True))
        limit = getattr(settings, 'SVJIS_TOP_ARTICLES_LIST_SIZE', 5)
        return get_top_articles(visible_ids, limit)


class NewsListAPIView(generics.ListAPIView):
    serializer_class = serializers.NewsSerializer
    pagination_class = None
    queryset = models.News.objects.filter(published=True)


class UsefulLinkListAPIView(generics.ListAPIView):
    serializer_class = serializers.UsefulLinkSerializer
    pagination_class = None
    queryset = models.UsefulLink.objects.filter(published=True)


class SurveyListAPIView(generics.ListAPIView):
    serializer_class = serializers.SurveySerializer
    pagination_class = None
    queryset = models.Survey.objects.filter(published=True)


class SurveyVoteAPIView(APIView):
    permission_classes = [HasPermission]
    required_permission = svjis_answer_survey

    def post(self, request, survey_id):
        survey = get_object_or_404(models.Survey, pk=survey_id)

        if not survey.is_open_for_voting:
            return Response(
                {'detail': _("Voting for this survey is currently closed.")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        vote_serializer = serializers.SurveyVoteSerializer(data=request.data, context={'survey': survey})
        vote_serializer.is_valid(raise_exception=True)

        if not survey.is_user_open_for_voting(request.user):
            return Response(
                {'detail': _("You have already voted in this survey.")},
                status=status.HTTP_403_FORBIDDEN,
            )

        models.SurveyAnswerLog.objects.create(
            survey=survey, option=vote_serializer.validated_data['option'], user=request.user
        )

        response_serializer = serializers.SurveySerializer(survey, context={'request': request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class ArticleMenuTreeAPIView(APIView):
    def get(self, request):
        menu_items = list(models.ArticleMenu.objects.filter(hide=False))

        def build(node):
            data = serializers.ArticleMenuSlimSerializer(node).data
            children = [build(child) for child in menu_items if child.parent_id == node.id]
            if children:
                data['children'] = children
            return data

        roots = [m for m in menu_items if m.parent_id is None]
        return Response([build(root) for root in roots])
