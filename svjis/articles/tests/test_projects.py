import re

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models import ProtectedError
from django.test import TestCase
from django.urls import reverse

from .. import models
from .factories.project import ProjectFactory
from .factories.project_status import ProjectStatusFactory
from .factories.project_comment import ProjectCommentFactory
from .factories.tag import TagFactory
from .testdata import UserDataMixin


class ProjectsTest(UserDataMixin, TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.status_new = ProjectStatusFactory(name='Nový', order=1, is_closed=False)
        cls.status_done = ProjectStatusFactory(name='Hotovo', order=2, is_closed=True)

    def setUp(self):
        self.project = ProjectFactory(
            created_by_user=self.u_jiri, assigned_to_user=self.u_karel, status=self.status_new
        )
        self.create_url = reverse('projects_project_create_save')
        self.detail_url = reverse('project', kwargs={'slug': self.project.slug})
        self.update_url = reverse('projects_project_update')

    def create_project_and_get(self, username, password, project_form):
        logged_in = self.client.login(username=username, password=password)
        self.assertTrue(logged_in)
        response = self.client.post(self.create_url, project_form, follow=True)
        self.assertEqual(response.status_code, 200)
        return response.context['obj']

    def test_retrieve(self):
        self.client.login(username='jiri', password=self.u_jiri_password)
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['obj'], self.project)

    # created_by_user
    def test_owner_created_by_user(self):
        project = self.create_project_and_get(
            'peter', self.u_peter_password, {'pk': 0, 'subject': 'test', 'description': 'test', 'created_by_user': ''}
        )
        self.assertEqual(project.created_by_user, self.u_peter)

    def test_board_on_behalf_of(self):
        project = self.create_project_and_get(
            'jiri',
            self.u_jiri_password,
            {'pk': 0, 'subject': 'test', 'description': 'test', 'created_by_user': self.u_jarda.pk},
        )
        self.assertEqual(project.created_by_user, self.u_jarda)

    # Non-manager cannot assign or pick the status - privilege escalation guard
    def test_owner_cannot_assign_or_pick_status_on_create(self):
        project = self.create_project_and_get(
            'peter',
            self.u_peter_password,
            {
                'pk': 0,
                'subject': 'test',
                'description': 'test',
                'assigned_to_user': self.u_jarda.pk,
                'status': self.status_done.pk,
            },
        )
        self.assertIsNone(project.assigned_to_user)
        self.assertFalse(project.status.is_closed)

    def test_board_can_assign_and_pick_status_on_create(self):
        project = self.create_project_and_get(
            'jiri',
            self.u_jiri_password,
            {
                'pk': 0,
                'subject': 'test',
                'description': 'test',
                'assigned_to_user': self.u_jarda.pk,
                'status': self.status_done.pk,
            },
        )
        self.assertEqual(project.assigned_to_user, self.u_jarda)
        self.assertEqual(project.status, self.status_done)

    # Workflow: assignee can edit their own open project, but not reassign/change status via crafted POST
    def test_assignee_can_edit_own_open_project_but_not_reassign(self):
        self.client.login(username='karel', password=self.u_karel_password)
        response = self.client.post(
            self.update_url,
            {
                'pk': self.project.pk,
                'subject': 'updated subject',
                'description': self.project.description,
                'created_by_user': self.project.created_by_user.pk,
                'assigned_to_user': self.u_karel.pk,
                'status': self.status_done.pk,
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.project.refresh_from_db()
        self.assertEqual(self.project.subject, 'updated subject')
        self.assertEqual(self.project.assigned_to_user, self.u_karel)
        self.assertEqual(self.project.status, self.status_new)

    def test_non_creator_non_assignee_non_manager_cannot_edit(self):
        self.client.login(username='peter', password=self.u_peter_password)
        response = self.client.get(reverse('projects_project_edit', kwargs={'pk': self.project.pk}))
        self.assertEqual(response.status_code, 404)

        response = self.client.post(
            self.update_url,
            {
                'pk': self.project.pk,
                'subject': 'hacked',
                'description': self.project.description,
                'created_by_user': self.project.created_by_user.pk,
            },
        )
        self.assertEqual(response.status_code, 404)
        self.project.refresh_from_db()
        self.assertNotEqual(self.project.subject, 'hacked')

    def test_assignee_cannot_edit_once_closed(self):
        self.project.status = self.status_done
        self.project.save()
        self.client.login(username='karel', password=self.u_karel_password)
        response = self.client.get(reverse('projects_project_edit', kwargs={'pk': self.project.pk}))
        self.assertEqual(response.status_code, 404)

    # Status change endpoint
    def test_manager_can_change_status_and_it_is_logged(self):
        self.client.login(username='jiri', password=self.u_jiri_password)
        response = self.client.post(
            reverse('projects_project_change_status'),
            {'pk': self.project.pk, 'status_id': self.status_done.pk},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.project.refresh_from_db()
        self.assertEqual(self.project.status, self.status_done)
        log = self.project.logs.get(type=models.ProjectLog.TYPE_STATUS_CHANGED)
        self.assertEqual(log.from_status, self.status_new)
        self.assertEqual(log.to_status, self.status_done)

    def test_assignee_can_change_status_of_own_project(self):
        self.client.login(username='karel', password=self.u_karel_password)
        response = self.client.post(
            reverse('projects_project_change_status'),
            {'pk': self.project.pk, 'status_id': self.status_done.pk},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.project.refresh_from_db()
        self.assertEqual(self.project.status, self.status_done)

    def test_outsider_cannot_change_status(self):
        self.client.login(username='peter', password=self.u_peter_password)
        response = self.client.post(
            reverse('projects_project_change_status'),
            {'pk': self.project.pk, 'status_id': self.status_done.pk},
        )
        self.assertEqual(response.status_code, 404)
        self.project.refresh_from_db()
        self.assertEqual(self.project.status, self.status_new)

    # Gallery uploads
    def test_create_project_with_gallery(self):
        self.client.login(username='peter', password=self.u_peter_password)
        response = self.client.post(
            self.create_url,
            {
                'pk': 0,
                'subject': 'test',
                'description': 'test',
                'created_by_user': '',
                'gallery': SimpleUploadedFile('foto.jpg', b'fake-jpg', content_type='image/jpeg'),
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        project = response.context['obj']
        self.assertEqual(project.assets.count(), 1)
        self.assertTrue(project.image_assets[0].file.name.startswith(f'projects/{project.slug}/'))

    # Tags
    def test_tags_round_trip_on_edit(self):
        tag_asap = TagFactory(name='ASAP')
        tag_other = TagFactory(name='Other')
        self.client.login(username='jiri', password=self.u_jiri_password)
        response = self.client.post(
            self.update_url,
            {
                'pk': self.project.pk,
                'subject': self.project.subject,
                'description': self.project.description,
                'created_by_user': self.project.created_by_user.pk,
                'assigned_to_user': self.project.assigned_to_user.pk,
                'status': self.project.status.pk,
                'tags': [tag_asap.pk],
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('projects_project_edit', kwargs={'pk': self.project.pk}))
        content = response.content.decode()
        self.assertIn(f'value="{tag_asap.pk}" checked', content)
        self.assertNotIn(f'value="{tag_other.pk}" checked', content)

    # Comments
    def test_comment_editable_only_by_author(self):
        comment = ProjectCommentFactory(project=self.project, author=self.u_jiri)
        self.client.login(username='jarda', password=self.u_jarda_password)
        response = self.client.get(reverse('project_comment_edit', kwargs={'pk': comment.pk}), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('name="comment_pk"', response.content.decode())

    # Watching
    def test_watch_toggle(self):
        self.client.login(username='jarda', password=self.u_jarda_password)
        self.client.get(reverse('project_watch') + f'?id={self.project.pk}&watch=1')
        self.assertIn(self.u_jarda, self.project.watching_users.all())
        self.client.get(reverse('project_watch') + f'?id={self.project.pk}&watch=0')
        self.assertNotIn(self.u_jarda, self.project.watching_users.all())


class ProjectsListTest(UserDataMixin, TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.status_new = ProjectStatusFactory(name='Nový', order=1, is_closed=False)
        cls.status_done = ProjectStatusFactory(name='Hotovo', order=2, is_closed=True)

    def setUp(self):
        self.client.login(username='jiri', password=self.u_jiri_password)

    def test_editable_project_shows_edit_action_non_editable_does_not(self):
        self.client.login(username='peter', password=self.u_peter_password)
        editable = ProjectFactory(created_by_user=self.u_peter, assigned_to_user=None, status=self.status_new)
        not_editable = ProjectFactory(created_by_user=self.u_jarda, assigned_to_user=None, status=self.status_new)
        response = self.client.get(reverse('projects_list') + '?scope=all')
        content = response.content.decode()
        self.assertIn(reverse('projects_project_edit', args=[editable.pk]), content)
        self.assertNotIn(reverse('projects_project_edit', args=[not_editable.pk]), content)

    def test_closed_project_gets_closed_row_class(self):
        closed = ProjectFactory(created_by_user=self.u_jiri, assigned_to_user=None, status=self.status_done)
        open_project = ProjectFactory(created_by_user=self.u_jiri, assigned_to_user=None, status=self.status_new)
        response = self.client.get(reverse('projects_list') + '?scope=all')
        content = response.content.decode()

        rows_by_slug = {
            slug: classes
            for classes, slug in re.findall(
                r'<tr class="([^"]*)" onclick="location\.href=\'[^\']*/project/([^/]+)/', content
            )
        }
        self.assertIn('closed-ticket', rows_by_slug[closed.slug])
        self.assertNotIn('closed-ticket', rows_by_slug[open_project.slug])

    def test_active_scope_hides_closed_projects(self):
        ProjectFactory(created_by_user=self.u_jiri, status=self.status_done)
        open_project = ProjectFactory(created_by_user=self.u_jiri, status=self.status_new)
        response = self.client.get(reverse('projects_list') + '?scope=active')
        content = response.content.decode()
        self.assertIn(reverse('project', kwargs={'slug': open_project.slug}), content)

    def test_everyone_with_view_perm_sees_all_projects_in_all_scope(self):
        # peter did not create nor is assigned to this project, but the shared
        # visibility model still shows it to anyone with the base view permission.
        self.client.login(username='peter', password=self.u_peter_password)
        other = ProjectFactory(created_by_user=self.u_jiri, assigned_to_user=None, status=self.status_new)
        response = self.client.get(reverse('projects_list') + '?scope=all')
        self.assertEqual(response.status_code, 200)
        self.assertIn(reverse('project', kwargs={'slug': other.slug}), response.content.decode())


class ProjectsKanbanTest(UserDataMixin, TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.status_new = ProjectStatusFactory(name='Nový', order=1, is_closed=False)
        cls.status_done = ProjectStatusFactory(name='Hotovo', order=2, is_closed=True)

    def test_kanban_marks_only_editable_cards_draggable(self):
        self.client.login(username='peter', password=self.u_peter_password)
        mine = ProjectFactory(created_by_user=self.u_peter, assigned_to_user=None, status=self.status_new)
        others = ProjectFactory(created_by_user=self.u_jiri, assigned_to_user=None, status=self.status_new)
        response = self.client.get(reverse('projects_kanban'))
        self.assertEqual(response.status_code, 200)
        # Attributes are spread across multiple lines in the template - normalize whitespace
        # before doing substring checks so the assertions don't depend on exact line-wrapping.
        content = ' '.join(response.content.decode().split())
        self.assertIn(f'data-project-id="{mine.pk}" draggable="true"', content)
        self.assertNotIn(f'data-project-id="{others.pk}" draggable="true"', content)

    def test_closed_statuses_hidden_by_default(self):
        self.client.login(username='jiri', password=self.u_jiri_password)
        response = self.client.get(reverse('projects_kanban'))
        self.assertNotIn(self.status_done.name, response.content.decode())
        response = self.client.get(reverse('projects_kanban') + '?show_closed=1')
        self.assertIn(self.status_done.name, response.content.decode())


class ProjectStatusProtectionTest(UserDataMixin, TestCase):
    def test_status_in_use_cannot_be_deleted(self):
        status = ProjectStatusFactory()
        ProjectFactory(status=status)
        with self.assertRaises(ProtectedError):
            status.delete()

    def test_admin_view_catches_protected_error(self):
        status = ProjectStatusFactory()
        ProjectFactory(status=status)
        self.client.login(username='jarda', password=self.u_jarda_password)
        response = self.client.get(reverse('admin_project_status_delete', kwargs={'pk': status.pk}), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(models.ProjectStatus.objects.filter(pk=status.pk).exists())
