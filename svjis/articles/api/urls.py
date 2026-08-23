from django.urls import path

from . import views

urlpatterns = [
    path('articles/', views.ArticleListAPIView.as_view(), name='api_article_list'),
    path('articles/top/', views.TopArticlesAPIView.as_view(), name='api_article_top'),
    path('news/', views.NewsListAPIView.as_view(), name='api_news_list'),
    path('surveys/', views.SurveyListAPIView.as_view(), name='api_survey_list'),
    path('surveys/<int:survey_id>/vote/', views.SurveyVoteAPIView.as_view(), name='api_survey_vote'),
    path('useful-links/', views.UsefulLinkListAPIView.as_view(), name='api_useful_link_list'),
    path('article-menus/', views.ArticleMenuTreeAPIView.as_view(), name='api_article_menu_tree'),
]
