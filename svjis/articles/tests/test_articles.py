import tempfile
from datetime import date

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from articles import models
from .factories import PermissionFactory
from .testdata import ArticleDataMixin


class ArticleListTest(ArticleDataMixin, TestCase):
    def do_user_test(self, username, password, for_all, for_owners, for_board, article_list):
        # Login user
        if username == 'anonymous':
            self.client.logout()
        else:
            logged_in = self.client.login(username=username, password=password)
            self.assertTrue(logged_in)

        # Article for all
        response = self.client.get(reverse('article', kwargs={'slug': self.article_for_all.slug}))
        self.assertEqual(response.status_code, for_all)

        # Article for Owners
        response = self.client.get(reverse('article', kwargs={'slug': self.article_for_owners.slug}))
        self.assertEqual(response.status_code, for_owners)

        # Article for Board
        response = self.client.get(reverse('article', kwargs={'slug': self.article_for_board.slug}))
        self.assertEqual(response.status_code, for_board)

        # Main page
        response = self.client.get(reverse('main'))
        self.assertEqual(response.status_code, 200)

        # List of Articles
        res_articles = response.context['article_list']
        self.assertEqual([a.header for a in res_articles], article_list)

    def test_admin_user(self):
        self.do_user_test(
            'jarda',
            self.u_jarda_password,
            200,
            200,
            200,
            ['For Board', 'For Owners and Board', 'For Owners', 'For All'],
        )

    def test_board_user(self):
        self.do_user_test(
            'jiri',
            self.u_jiri_password,
            200,
            200,
            200,
            ['For Board', 'For Owners and Board', 'For Owners', 'For All'],
        )

    def test_owner_user(self):
        self.do_user_test(
            'peter',
            self.u_peter_password,
            200,
            200,
            404,
            ['For Owners and Board', 'For Owners', 'For All'],
        )

    def test_vendor_user(self):
        self.do_user_test(
            'karel',
            self.u_karel_password,
            200,
            404,
            404,
            ['For All'],
        )

    def test_anonymous_user(self):
        self.do_user_test('anonymous', '', 200, 302, 302, ['For All'])

    def test_top_articles(self):
        # Login board user
        logged_in = self.client.login(username='jiri', password=self.u_jiri_password)
        self.assertTrue(logged_in)

        # Article for all
        response = self.client.get(reverse('article', kwargs={'slug': self.article_for_all.slug}))
        self.assertEqual(response.status_code, 200)

        # Article for Board
        response = self.client.get(reverse('article', kwargs={'slug': self.article_for_board.slug}))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('article', kwargs={'slug': self.article_for_board.slug}))
        self.assertEqual(response.status_code, 200)

        # Main page
        response = self.client.get(reverse('main'))
        self.assertEqual(response.status_code, 200)

        # Top Articles
        res_top = response.context['top_articles']
        self.assertEqual(len(res_top), 2)
        self.assertEqual(res_top[0]['article_id'], self.article_for_board.pk)
        self.assertEqual(res_top[0]['total'], 2)
        self.assertEqual(res_top[1]['article_id'], self.article_for_all.pk)
        self.assertEqual(res_top[1]['total'], 1)

        # Login owner user
        logged_in = self.client.login(username='peter', password=self.u_peter_password)
        self.assertTrue(logged_in)

        # Main page
        response = self.client.get(reverse('main'))
        self.assertEqual(response.status_code, 200)

        # Top Articles
        res_top = response.context['top_articles']
        self.assertEqual(len(res_top), 1)
        self.assertEqual(res_top[0]['article_id'], self.article_for_all.pk)
        self.assertEqual(res_top[0]['total'], 1)

        # Logout user
        self.client.logout()

        # Main page
        response = self.client.get(reverse('main'))
        self.assertEqual(response.status_code, 200)

        # Top Articles
        res_top = response.context['top_articles']
        self.assertEqual(len(res_top), 1)
        self.assertEqual(res_top[0]['article_id'], self.article_for_all.pk)
        self.assertEqual(res_top[0]['total'], 1)

    def test_send_article_notifications(self):
        # Login board user
        logged_in = self.client.login(username='jiri', password=self.u_jiri_password)
        self.assertTrue(logged_in)

        # Send notifications for article not published
        response = self.client.get(
            reverse('redaction_article_notifications', kwargs={'pk': self.article_not_published.pk})
        )
        self.assertEqual(response.status_code, 200)
        res_recipients = response.context['object_list']
        self.assertEqual(len(res_recipients), 0)

        # Send notifications for no one
        response = self.client.get(
            reverse('redaction_article_notifications', kwargs={'pk': self.article_for_no_one.pk})
        )
        self.assertEqual(response.status_code, 200)
        res_recipients = response.context['object_list']
        self.assertEqual(len(res_recipients), 0)

        # Send notifications for all
        response = self.client.get(reverse('redaction_article_notifications', kwargs={'pk': self.article_for_all.pk}))
        self.assertEqual(response.status_code, 200)
        res_recipients = response.context['object_list']
        self.assertEqual(len(res_recipients), 4)
        self.assertEqual(res_recipients[0].last_name, 'Beran')
        self.assertEqual(res_recipients[1].last_name, 'Brambůrek')
        self.assertEqual(res_recipients[2].last_name, 'Lukáš')
        self.assertEqual(res_recipients[3].last_name, 'Nebus')

        # Send notifications for owners
        response = self.client.get(
            reverse('redaction_article_notifications', kwargs={'pk': self.article_for_owners.pk})
        )
        self.assertEqual(response.status_code, 200)
        res_recipients = response.context['object_list']
        self.assertEqual(len(res_recipients), 3)
        self.assertEqual(res_recipients[0].last_name, 'Beran')
        self.assertEqual(res_recipients[1].last_name, 'Brambůrek')
        self.assertEqual(res_recipients[2].last_name, 'Nebus')

        # Send notifications for board
        response = self.client.get(
            reverse('redaction_article_notifications', kwargs={'pk': self.article_for_board.pk})
        )
        self.assertEqual(response.status_code, 200)
        res_recipients = response.context['object_list']
        self.assertEqual(len(res_recipients), 2)
        self.assertEqual(res_recipients[0].last_name, 'Beran')
        self.assertEqual(res_recipients[1].last_name, 'Brambůrek')

        # Send notifications for board
        response = self.client.get(
            reverse('redaction_article_notifications', kwargs={'pk': self.article_for_owners_and_board.pk})
        )
        self.assertEqual(response.status_code, 200)
        res_recipients = response.context['object_list']
        self.assertEqual(len(res_recipients), 3)
        self.assertEqual(res_recipients[0].last_name, 'Beran')
        self.assertEqual(res_recipients[1].last_name, 'Brambůrek')
        self.assertEqual(res_recipients[2].last_name, 'Nebus')


class ArticleImageUploadTest(ArticleDataMixin, TestCase):
    def setUp(self):
        self._media_dir = tempfile.TemporaryDirectory()
        self._media_override = override_settings(MEDIA_ROOT=self._media_dir.name)
        self._media_override.enable()
        self.addCleanup(self._media_override.disable)
        self.addCleanup(self._media_dir.cleanup)

    def upload(self, article_pk, filename, content=b'fake-image-data'):
        file = SimpleUploadedFile(filename, content)
        return self.client.post(
            reverse('redaction_article_image_upload'),
            {'article_pk': article_pk, 'file': file},
        )

    def test_redactor_can_upload_image(self):
        logged_in = self.client.login(username='jarda', password=self.u_jarda_password)
        self.assertTrue(logged_in)

        response = self.upload(self.article_for_all.pk, 'picture.png')
        self.assertEqual(response.status_code, 200)

        asset = models.ArticleAsset.objects.get(article=self.article_for_all)
        self.assertEqual(response.json()['location'], f'/media/{asset.file}')
        self.assertEqual(asset.description, 'picture.png')

    def test_upload_rejects_non_image(self):
        self.client.login(username='jarda', password=self.u_jarda_password)

        response = self.upload(self.article_for_all.pk, 'document.pdf')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(models.ArticleAsset.objects.count(), 0)

    def test_upload_rejects_unknown_article(self):
        self.client.login(username='jarda', password=self.u_jarda_password)

        response = self.upload(9999, 'picture.png')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(models.ArticleAsset.objects.count(), 0)

    def test_upload_requires_permission(self):
        self.client.login(username='peter', password=self.u_peter_password)

        response = self.upload(self.article_for_all.pk, 'picture.png')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(models.ArticleAsset.objects.count(), 0)


class RedactionArticleListTest(ArticleDataMixin, TestCase):
    def setUp(self):
        self.client.login(username='jiri', password=self.u_jiri_password)

    def test_list_uses_dropdown_with_all_actions(self):
        response = self.client.get(reverse('redaction_article'))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('action-menu', content)
        self.assertIn('sortable', content)
        for article in models.Article.objects.all():
            self.assertIn(f'redaction_article_edit/{article.pk}/', content)
            self.assertIn(f'redaction_article_notifications/{article.pk}/', content)
            self.assertIn(f'redaction_article_hide/{article.pk}/', content)
            self.assertIn(f'redaction_article_delete/{article.pk}/', content)
            self.assertIn(article.header, content)

    def test_hide_article(self):
        article = self.article_for_all
        self.assertTrue(article.published)
        response = self.client.get(reverse('redaction_article_hide', kwargs={'pk': article.pk}))
        self.assertEqual(response.status_code, 302)
        article.refresh_from_db()
        self.assertFalse(article.published)

    def test_delete_article(self):
        article = self.article_for_no_one
        response = self.client.get(reverse('redaction_article_delete', kwargs={'pk': article.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(models.Article.objects.filter(pk=article.pk).exists())

    def test_hide_and_delete_require_permission(self):
        self.client.login(username='peter', password=self.u_peter_password)
        self.assertEqual(
            self.client.get(reverse('redaction_article')).status_code, 302
        )
        self.assertEqual(
            self.client.get(reverse('redaction_article_hide', kwargs={'pk': self.article_for_all.pk})).status_code,
            302,
        )
        self.assertEqual(
            self.client.get(reverse('redaction_article_delete', kwargs={'pk': self.article_for_all.pk})).status_code,
            302,
        )


class RedactionListsTest(ArticleDataMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.news = models.News.objects.create(author=cls.u_jiri, published=True, body="News body")
        cls.link = models.UsefulLink.objects.create(
            header="Help", link="https://example.com/help", order=1, published=True
        )
        cls.survey = models.Survey.objects.create(
            author=cls.u_jiri,
            description="Survey desc",
            starting_date=date(2026, 1, 1),
            ending_date=date(2026, 2, 1),
            published=True,
        )
        cls.menu_child = models.ArticleMenu.objects.create(
            description="Child menu", hide=False, parent=cls.menu_docs
        )
        cls.menu_grandchild = models.ArticleMenu.objects.create(
            description="Grandchild menu", hide=False, parent=cls.menu_child
        )
        cls.permission = PermissionFactory(codename="svjis_edit_useful_link")
        cls.u_jiri.user_permissions.add(cls.permission)

    def setUp(self):
        self.client.login(username='jiri', password=self.u_jiri_password)

    def assert_component(self, url, table_id):
        response = self.client.get(reverse(url))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('action-menu', content)
        self.assertIn('sortable', content)
        self.assertIn(f'id="{table_id}"', content)
        return content

    def test_news_list_uses_component(self):
        content = self.assert_component('redaction_news', 'news')
        self.assertIn(f'redaction_news_delete/{self.news.pk}/', content)
        self.assertIn('News body', content)

    def test_useful_link_list_uses_component(self):
        content = self.assert_component('redaction_useful_link', 'links')
        self.assertIn(f'redaction_useful_link_delete/{self.link.pk}/', content)
        self.assertIn('https://example.com/help', content)

    def test_survey_list_uses_component(self):
        content = self.assert_component('redaction_survey', 'survey')
        self.assertIn(f'redaction_survey_delete/{self.survey.pk}/', content)
        self.assertIn(f'redaction_survey_results/{self.survey.pk}/', content)
        self.assertIn(f'redaction_survey_results_export_to_excel/{self.survey.pk}/', content)
        self.assertIn('Survey desc', content)

    def test_menu_list_uses_component(self):
        content = self.assert_component('redaction_menu', 'menu')
        self.assertIn('Child menu', content)
        self.assertIn('Grandchild menu', content)
        self.assertIn(f'redaction_menu_delete/{self.menu_child.pk}/', content)
        self.assertIn(f'redaction_menu_delete/{self.menu_grandchild.pk}/', content)
        self.assertIn('f1948a', content)

    def test_menu_delete_hidden_when_articles_exist(self):
        content = self.client.get(reverse('redaction_menu')).content.decode()
        self.assertNotIn(f'redaction_menu_delete/{self.menu_docs.pk}/', content)

    def test_useful_link_requires_permission(self):
        self.client.login(username='peter', password=self.u_peter_password)
        self.assertEqual(self.client.get(reverse('redaction_useful_link')).status_code, 302)
