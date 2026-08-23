from datetime import date, timedelta

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from articles import models

from .factories import (
    ArticleMenuFactory,
    NewsFactory,
    SurveyAnswerLogFactory,
    SurveyFactory,
    SurveyOptionFactory,
    UsefulLinkFactory,
)
from .testdata import ArticleDataMixin


class ArticleApiListTest(ArticleDataMixin, APITestCase):
    def test_admin_user_sees_everything(self):
        self.client.login(username='jarda', password=self.u_jarda_password)
        response = self.client.get(reverse('api_article_list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        headers = [a['header'] for a in response.data['results']]
        self.assertEqual(headers, ['For Board', 'For Owners and Board', 'For Owners', 'For All'])

    def test_owner_user(self):
        self.client.login(username='peter', password=self.u_peter_password)
        response = self.client.get(reverse('api_article_list'))
        headers = [a['header'] for a in response.data['results']]
        self.assertEqual(headers, ['For Owners and Board', 'For Owners', 'For All'])

    def test_vendor_user(self):
        self.client.login(username='karel', password=self.u_karel_password)
        response = self.client.get(reverse('api_article_list'))
        headers = [a['header'] for a in response.data['results']]
        self.assertEqual(headers, ['For All'])

    def test_anonymous_user(self):
        response = self.client.get(reverse('api_article_list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        headers = [a['header'] for a in response.data['results']]
        self.assertEqual(headers, ['For All'])

    def test_menu_filter(self):
        other_menu = ArticleMenuFactory(description="Other", parent=None)
        response = self.client.get(reverse('api_article_list'), {'menu': other_menu.pk})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['results'], [])

    def test_menu_filter_unknown_menu_is_404(self):
        response = self.client.get(reverse('api_article_list'), {'menu': 999999})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_search_too_short_is_400(self):
        response = self.client.get(reverse('api_article_list'), {'search': 'ab'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_search_too_long_is_400(self):
        response = self.client.get(reverse('api_article_list'), {'search': 'a' * 101})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_search_matches(self):
        response = self.client.get(reverse('api_article_list'), {'search': 'For All'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        headers = [a['header'] for a in response.data['results']]
        self.assertEqual(headers, ['For All'])

    def test_pagination_invalid_page_is_404(self):
        response = self.client.get(reverse('api_article_list'), {'page': 999})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class TopArticlesApiTest(ArticleDataMixin, APITestCase):
    def test_top_articles_ranked_by_visible_views(self):
        self.client.login(username='jiri', password=self.u_jiri_password)
        self.client.get(reverse('article', kwargs={'slug': self.article_for_all.slug}))
        self.client.get(reverse('article', kwargs={'slug': self.article_for_board.slug}))
        self.client.get(reverse('article', kwargs={'slug': self.article_for_board.slug}))

        response = self.client.get(reverse('api_article_top'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0]['article']['id'], self.article_for_board.pk)
        self.assertEqual(response.data[0]['total'], 2)
        self.assertEqual(response.data[1]['article']['id'], self.article_for_all.pk)
        self.assertEqual(response.data[1]['total'], 1)


class NewsApiListTest(APITestCase):
    def test_only_published_returned(self):
        published = NewsFactory(published=True)
        NewsFactory(published=False)
        response = self.client.get(reverse('api_news_list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([n['id'] for n in response.data], [published.id])


class UsefulLinkApiListTest(APITestCase):
    def test_only_published_returned_and_ordered(self):
        link2 = UsefulLinkFactory(published=True, order=2)
        link1 = UsefulLinkFactory(published=True, order=1)
        UsefulLinkFactory(published=False, order=0)
        response = self.client.get(reverse('api_useful_link_list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([link['id'] for link in response.data], [link1.id, link2.id])


class ArticleMenuApiTreeTest(APITestCase):
    def test_hidden_excluded_and_children_nested(self):
        root = ArticleMenuFactory(description="Root", parent=None, hide=False)
        child = ArticleMenuFactory(description="Child", parent=root, hide=False)
        ArticleMenuFactory(description="Hidden root", parent=None, hide=True)

        response = self.client.get(reverse('api_article_menu_tree'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        descriptions = [m['description'] for m in response.data]
        self.assertIn('Root', descriptions)
        self.assertNotIn('Hidden root', descriptions)

        root_node = next(m for m in response.data if m['id'] == root.pk)
        self.assertEqual([c['id'] for c in root_node['children']], [child.pk])


class SurveyApiListTest(ArticleDataMixin, APITestCase):
    def test_published_only_and_vote_stats(self):
        survey = SurveyFactory(published=True)
        option_a = SurveyOptionFactory(survey=survey, description='A')
        option_b = SurveyOptionFactory(survey=survey, description='B')
        SurveyFactory(published=False)

        SurveyAnswerLogFactory(survey=survey, option=option_a, user=self.u_peter)
        SurveyAnswerLogFactory(survey=survey, option=option_a, user=self.u_karel)
        SurveyAnswerLogFactory(survey=survey, option=option_b, user=self.u_jarda)

        self.client.login(username='jiri', password=self.u_jiri_password)
        response = self.client.get(reverse('api_survey_list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        data = response.data[0]
        self.assertEqual(data['total_votes'], 3)
        options_by_id = {o['id']: o for o in data['options']}
        self.assertAlmostEqual(options_by_id[option_a.pk]['pct'], 200 / 3)
        self.assertTrue(options_by_id[option_a.pk]['is_winning'])
        self.assertFalse(options_by_id[option_b.pk]['is_winning'])
        # jiri belongs to g_owner (has svjis_answer_survey) and hasn't voted yet
        self.assertTrue(data['user_can_vote'])

    def test_user_can_vote_false_when_already_voted(self):
        survey = SurveyFactory(published=True)
        option = SurveyOptionFactory(survey=survey)
        SurveyAnswerLogFactory(survey=survey, option=option, user=self.u_peter)

        self.client.login(username='peter', password=self.u_peter_password)
        response = self.client.get(reverse('api_survey_list'))
        self.assertFalse(response.data[0]['user_can_vote'])

    def test_user_can_vote_false_for_anonymous(self):
        SurveyFactory(published=True)
        response = self.client.get(reverse('api_survey_list'))
        self.assertFalse(response.data[0]['user_can_vote'])

    def test_user_can_vote_false_without_permission(self):
        SurveyFactory(published=True)
        self.client.login(username='karel', password=self.u_karel_password)
        response = self.client.get(reverse('api_survey_list'))
        self.assertFalse(response.data[0]['user_can_vote'])


class SurveyVoteApiTest(ArticleDataMixin, APITestCase):
    def setUp(self):
        self.survey = SurveyFactory(published=True)
        self.option = SurveyOptionFactory(survey=self.survey)
        self.other_survey = SurveyFactory(published=True)
        self.other_option = SurveyOptionFactory(survey=self.other_survey)

    def vote_url(self, survey=None):
        return reverse('api_survey_vote', kwargs={'survey_id': (survey or self.survey).pk})

    def test_successful_vote(self):
        self.client.login(username='peter', password=self.u_peter_password)
        response = self.client.post(self.vote_url(), {'option': self.option.pk}, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            models.SurveyAnswerLog.objects.filter(survey=self.survey, option=self.option, user=self.u_peter).exists()
        )
        self.assertFalse(response.data['user_can_vote'])

    def test_anonymous_is_forbidden(self):
        response = self.client.post(self.vote_url(), {'option': self.option.pk}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_without_permission_is_forbidden(self):
        self.client.login(username='karel', password=self.u_karel_password)
        response = self.client.post(self.vote_url(), {'option': self.option.pk}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_voting_window_not_yet_started(self):
        survey = SurveyFactory(
            published=True,
            starting_date=date.today() + timedelta(days=1),
            ending_date=date.today() + timedelta(days=5),
        )
        option = SurveyOptionFactory(survey=survey)
        self.client.login(username='peter', password=self.u_peter_password)
        response = self.client.post(self.vote_url(survey), {'option': option.pk}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_voting_window_already_ended(self):
        survey = SurveyFactory(
            published=True,
            starting_date=date.today() - timedelta(days=10),
            ending_date=date.today() - timedelta(days=1),
        )
        option = SurveyOptionFactory(survey=survey)
        self.client.login(username='peter', password=self.u_peter_password)
        response = self.client.post(self.vote_url(survey), {'option': option.pk}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_already_voted_is_forbidden(self):
        SurveyAnswerLogFactory(survey=self.survey, option=self.option, user=self.u_peter)
        self.client.login(username='peter', password=self.u_peter_password)
        response = self.client.post(self.vote_url(), {'option': self.option.pk}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_option_not_belonging_to_survey_is_400(self):
        self.client.login(username='peter', password=self.u_peter_password)
        response = self.client.post(self.vote_url(), {'option': self.other_option.pk}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unknown_option_is_400(self):
        self.client.login(username='peter', password=self.u_peter_password)
        response = self.client.post(self.vote_url(), {'option': 999999}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unknown_survey_is_404(self):
        self.client.login(username='peter', password=self.u_peter_password)
        response = self.client.post(
            reverse('api_survey_vote', kwargs={'survey_id': 999999}), {'option': self.option.pk}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_csrf_is_enforced(self):
        client = APIClient(enforce_csrf_checks=True)
        client.login(username='peter', password=self.u_peter_password)
        response = client.post(self.vote_url(), {'option': self.option.pk}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
