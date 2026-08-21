from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.urls import reverse

from .. import models
from .factories.tag import TagFactory
from .factories.project import ProjectFactory
from .testdata import UserDataMixin


class TagAdminTest(UserDataMixin, TestCase):
    def setUp(self):
        self.client.login(username='jarda', password=self.u_jarda_password)

    def test_list_requires_permission(self):
        self.client.logout()
        self.client.login(username='jiri', password=self.u_jiri_password)
        response = self.client.get(reverse('admin_tag'))
        self.assertEqual(response.status_code, 302)

    def test_create_tag(self):
        response = self.client.post(reverse('admin_tag_save'), {'pk': 0, 'name': 'ASAP', 'color': 'red'})
        self.assertRedirects(response, reverse('admin_tag'))
        tag = models.Tag.objects.get(name='ASAP')
        self.assertEqual(tag.color, 'red')

    def test_edit_tag(self):
        tag = TagFactory(name='Návrh', color='amber')
        response = self.client.post(reverse('admin_tag_save'), {'pk': tag.pk, 'name': 'Návrh', 'color': 'green'})
        self.assertRedirects(response, reverse('admin_tag'))
        tag.refresh_from_db()
        self.assertEqual(tag.color, 'green')

    def test_delete_tag_removes_tagged_item_but_not_project(self):
        tag = TagFactory()
        project = ProjectFactory()
        ct = ContentType.objects.get_for_model(models.Project)
        models.TaggedItem.objects.create(tag=tag, content_type=ct, object_id=project.pk)

        self.client.get(reverse('admin_tag_delete', kwargs={'pk': tag.pk}))

        self.assertFalse(models.Tag.objects.filter(pk=tag.pk).exists())
        self.assertFalse(models.TaggedItem.objects.exists())
        self.assertTrue(models.Project.objects.filter(pk=project.pk).exists())
