from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse

from .testdata import UserDataMixin


class FooterAttributionTest(UserDataMixin, TestCase):
    def test_footer_credits_base_project_and_author(self):
        response = self.client.get(reverse('main'))
        content = response.content.decode()
        self.assertIn('href="https://svjis.github.io/"', content)
        self.assertIn('href="https://uhlir.me"', content)
        self.assertIn('Filip Uhlíř', content)

    @override_settings(SVJIS_FORK_VERSION='3.1')
    def test_footer_shows_fork_version_when_configured(self):
        response = self.client.get(reverse('main'))
        self.assertIn('v3.1', response.content.decode())

    @override_settings(SVJIS_FORK_VERSION='')
    def test_footer_omits_version_badge_when_not_configured(self):
        response = self.client.get(reverse('main'))
        content = response.content.decode()
        self.assertNotIn('&middot; v<', content)


class AboutPageAttributionTest(UserDataMixin, TestCase):
    def setUp(self):
        self.client.login(username='jarda', password=self.u_jarda_password)

    @override_settings(SVJIS_FORK_VERSION='3.1')
    def test_about_page_shows_deployment_version_and_author(self):
        response = self.client.get(reverse('admin_about'))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('3.1', content)
        self.assertIn('href="https://uhlir.me"', content)
        self.assertIn('Filip Uhlíř', content)

    @override_settings(SVJIS_FORK_VERSION='')
    def test_about_page_hides_deployment_version_row_when_not_configured(self):
        response = self.client.get(reverse('admin_about'))
        self.assertNotIn('Deployment version', response.content.decode())
