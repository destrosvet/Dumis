from django.test import TestCase
from django.urls import reverse

from .. import models
from .factories.project_status import ProjectStatusFactory
from .factories.project import ProjectFactory
from .testdata import UserDataMixin


class ProjectStatusAdminTest(UserDataMixin, TestCase):
    def setUp(self):
        self.client.login(username='jarda', password=self.u_jarda_password)

    def test_list_requires_permission(self):
        self.client.logout()
        self.client.login(username='jiri', password=self.u_jiri_password)
        response = self.client.get(reverse('admin_project_status'))
        self.assertEqual(response.status_code, 302)

    def test_create_status(self):
        response = self.client.post(
            reverse('admin_project_status_save'),
            {'pk': 0, 'name': 'V realizaci', 'order': 2, 'color': 'brand', 'is_closed': ''},
        )
        self.assertRedirects(response, reverse('admin_project_status'))
        status = models.ProjectStatus.objects.get(name='V realizaci')
        self.assertEqual(status.order, 2)
        self.assertEqual(status.color, 'brand')
        self.assertFalse(status.is_closed)

    def test_edit_status(self):
        status = ProjectStatusFactory(name='Nový', order=1, is_closed=False)
        response = self.client.post(
            reverse('admin_project_status_save'),
            {'pk': status.pk, 'name': 'Nový', 'order': 1, 'color': 'green', 'is_closed': 'on'},
        )
        self.assertRedirects(response, reverse('admin_project_status'))
        status.refresh_from_db()
        self.assertTrue(status.is_closed)
        self.assertEqual(status.color, 'green')

    def test_delete_unused_status(self):
        status = ProjectStatusFactory()
        self.client.get(reverse('admin_project_status_delete', kwargs={'pk': status.pk}))
        self.assertFalse(models.ProjectStatus.objects.filter(pk=status.pk).exists())

    def test_delete_status_in_use_is_protected(self):
        status = ProjectStatusFactory()
        ProjectFactory(status=status)
        response = self.client.get(reverse('admin_project_status_delete', kwargs={'pk': status.pk}), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(models.ProjectStatus.objects.filter(pk=status.pk).exists())
