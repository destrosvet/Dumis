from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from .. import models


class AuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name']


class ArticleMenuSlimSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.ArticleMenu
        fields = ['id', 'description']


class ArticleSlimSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Article
        fields = ['id', 'slug', 'header']


class ArticleListSerializer(serializers.ModelSerializer):
    menu = ArticleMenuSlimSerializer(read_only=True)
    author = AuthorSerializer(read_only=True)
    cover_image = serializers.SerializerMethodField()
    comments_count = serializers.SerializerMethodField()

    class Meta:
        model = models.Article
        fields = [
            'id',
            'slug',
            'header',
            'perex',
            'published_date',
            'menu',
            'author',
            'cover_image',
            'comments_count',
        ]

    def get_cover_image(self, obj):
        return obj.cover_image.url if obj.cover_image else None

    def get_comments_count(self, obj):
        return obj.comments.count()


class TopArticleSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    article = ArticleSlimSerializer()


class NewsSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.News
        fields = ['id', 'created_date', 'body']


class UsefulLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.UsefulLink
        fields = ['id', 'header', 'link', 'order']


class SurveyOptionSerializer(serializers.ModelSerializer):
    pct = serializers.FloatField(read_only=True)
    total = serializers.IntegerField(read_only=True)
    is_winning = serializers.BooleanField(read_only=True)

    class Meta:
        model = models.SurveyOption
        fields = ['id', 'description', 'pct', 'total', 'is_winning']


class SurveySerializer(serializers.ModelSerializer):
    options = SurveyOptionSerializer(many=True, read_only=True)
    is_open_for_voting = serializers.BooleanField(read_only=True)
    total_votes = serializers.SerializerMethodField()
    user_can_vote = serializers.SerializerMethodField()

    class Meta:
        model = models.Survey
        fields = [
            'id',
            'description',
            'starting_date',
            'ending_date',
            'is_open_for_voting',
            'options',
            'total_votes',
            'user_can_vote',
        ]

    def get_total_votes(self, obj):
        return obj.answers.count()

    def get_user_can_vote(self, obj):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if user is None or user.is_anonymous:
            return False
        return obj.is_user_open_for_voting(user)


class SurveyVoteSerializer(serializers.Serializer):
    option = serializers.PrimaryKeyRelatedField(queryset=models.SurveyOption.objects.all())

    def validate(self, attrs):
        survey = self.context['survey']
        if attrs['option'].survey_id != survey.id:
            raise serializers.ValidationError({'option': _("This option does not belong to the given survey.")})
        return attrs
