from django.test import TestCase
from django.urls import reverse

from .testdata import UserDataMixin


class LoginPageErrorTest(UserDataMixin, TestCase):
    def test_wrong_password_shows_single_error_inside_the_card_not_in_the_page_wide_banner(self):
        response = self.client.post(
            reverse('user_login'),
            {'username': 'jarda', 'password': 'not-the-password'},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()

        # Only the one error - the old "use Lost Password" hint is redundant and was dropped.
        self.assertEqual(content.count('alert-error'), 1)
        self.assertNotIn('alert-info', content)
        self.assertIn('Wrong username or password', content)

        # The message must render inside the login card's own reserved slot, not the
        # page-wide banner (which would shift the centered card down the page).
        self.assertIn('login-card__messages', content)
        messages_pos = content.index('login-card__messages')
        error_pos = content.index('Wrong username or password')
        card_pos = content.index('login-card')
        self.assertTrue(card_pos < messages_pos < error_pos)
        self.assertNotIn('messages-wrapper', content)

    def test_correct_password_shows_no_error(self):
        response = self.client.post(
            reverse('user_login'),
            {'username': 'jarda', 'password': self.u_jarda_password},
        )
        self.assertEqual(response.status_code, 302)
