import io
import re
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from .. import models
from .factories.fault_report import FaultReportFactory
from .testdata import UserDataMixin, PreferencesDataMixin


def make_image_bytes(width, height, format='PNG'):
    buffer = io.BytesIO()
    Image.new('RGB', (width, height), color=(120, 140, 160)).save(buffer, format=format)
    return buffer.getvalue()


class FaultsTest(UserDataMixin, PreferencesDataMixin, TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.fault = FaultReportFactory(created_by_user=cls.u_jiri, closed=False)

        cls.create_url = reverse('faults_fault_create_save')
        cls.detail_url = reverse('fault', kwargs={'slug': cls.fault.slug})
        cls.update_url = reverse('faults_fault_update')

    def create_fault_and_get_created_by(self, username, password, fault_form):
        logged_in = self.client.login(username=username, password=password)
        self.assertTrue(logged_in)
        response = self.client.post(
            self.create_url,
            fault_form,
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        return response.context['obj']

    def test_retrieve(self):
        logged_in = self.client.login(username='jiri', password=self.u_jiri_password)
        self.assertTrue(logged_in)
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 200)
        fault = response.context['obj']
        self.assertEqual(fault, self.fault)
        self.assertEqual(fault.logs.count(), 0)

    def test_close_fault_retrieve_logs(self):
        logged_in = self.client.login(username='jiri', password=self.u_jiri_password)
        self.assertTrue(logged_in)
        response = self.client.post(
            self.update_url,
            {
                'assigned_to_user': self.u_jarda.pk,
                'closed': True,
                'pk': self.fault.pk,
                'subject': self.fault.subject,
                'description': self.fault.description,
                'created_by_user': self.fault.created_by_user.pk,
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)

        self.fault.refresh_from_db()

        self.assertEqual(self.fault.closed, True)
        self.assertEqual(self.fault.logs.count(), 2)
        assigned, closed = self.fault.logs.all()
        self.assertEqual(assigned.type, assigned.TYPE_ASSIGNED)
        self.assertEqual(assigned.resolver, self.u_jarda)
        self.assertEqual(assigned.user, self.u_jiri)
        self.assertEqual(closed.type, closed.TYPE_CLOSED)
        self.assertEqual(closed.resolver, self.u_jarda)
        self.assertEqual(closed.user, self.u_jiri)

    # Created by user
    def test_owner_created_by_user(self):
        fault = self.create_fault_and_get_created_by(
            "peter", self.u_peter_password, {'pk': 0, 'subject': 'test', 'description': 'test', 'created_by_user': ''}
        )
        self.assertEqual(fault.created_by_user, self.u_peter)

    def test_owner_on_behalf_of(self):
        fault = self.create_fault_and_get_created_by(
            "peter",
            self.u_peter_password,
            {'pk': 0, 'subject': 'test', 'description': 'test', 'created_by_user': self.u_jarda.pk},
        )
        self.assertEqual(fault.created_by_user, self.u_peter)

    def test_board_on_behalf_of(self):
        fault = self.create_fault_and_get_created_by(
            "jiri",
            self.u_jiri_password,
            {'pk': 0, 'subject': 'test', 'description': 'test', 'created_by_user': self.u_jarda.pk},
        )
        self.assertEqual(fault.created_by_user, self.u_jarda)

    def test_board_created_by_user_missing(self):
        fault = self.create_fault_and_get_created_by(
            "jiri", self.u_jiri_password, {'pk': 0, 'subject': 'test', 'description': 'test'}
        )
        self.assertEqual(fault.created_by_user, self.u_jiri)

    # Assigned to user
    def test_owner_assigned_to_user_empty(self):
        fault = self.create_fault_and_get_created_by(
            "peter", self.u_peter_password, {'pk': 0, 'subject': 'test', 'description': 'test', 'assigned_to_user': ''}
        )
        self.assertEqual(fault.assigned_to_user, None)

    def test_owner_assigned_to_user(self):
        fault = self.create_fault_and_get_created_by(
            "peter",
            self.u_peter_password,
            {'pk': 0, 'subject': 'test', 'description': 'test', 'assigned_to_user': self.u_jarda.pk},
        )
        self.assertEqual(fault.assigned_to_user, None)

    def test_board_assigned_to_user(self):
        fault = self.create_fault_and_get_created_by(
            "jiri",
            self.u_jiri_password,
            {'pk': 0, 'subject': 'test', 'description': 'test', 'assigned_to_user': self.u_jarda.pk},
        )
        self.assertEqual(fault.assigned_to_user, self.u_jarda)

    # Closed
    def test_owner_closed(self):
        fault = self.create_fault_and_get_created_by(
            "peter", self.u_peter_password, {'pk': 0, 'subject': 'test', 'description': 'test', 'closed': True}
        )
        self.assertEqual(fault.closed, False)

    def test_board_closed(self):
        fault = self.create_fault_and_get_created_by(
            "jiri", self.u_jiri_password, {'pk': 0, 'subject': 'test', 'description': 'test', 'closed': True}
        )
        self.assertEqual(fault.closed, True)

    # Workflow: reporter can edit their own open ticket, but not its assignment/closed state
    def test_creator_can_edit_own_open_fault(self):
        fault = FaultReportFactory(created_by_user=self.u_peter, assigned_to_user=None, closed=False)
        self.client.login(username='peter', password=self.u_peter_password)
        response = self.client.post(
            reverse('faults_fault_update'),
            {
                'pk': fault.pk,
                'subject': 'updated subject',
                'description': fault.description,
                'created_by_user': self.u_jarda.pk,
                'assigned_to_user': self.u_jarda.pk,
                'closed': True,
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)

        fault.refresh_from_db()
        self.assertEqual(fault.subject, 'updated subject')
        self.assertEqual(fault.created_by_user, self.u_peter)
        self.assertIsNone(fault.assigned_to_user)
        self.assertEqual(fault.closed, False)

    def test_non_creator_non_resolver_cannot_edit_fault(self):
        fault = FaultReportFactory(created_by_user=self.u_jarda, assigned_to_user=None, closed=False)
        original_subject = fault.subject
        self.client.login(username='peter', password=self.u_peter_password)
        response = self.client.get(reverse('faults_fault_edit', kwargs={'pk': fault.pk}))
        self.assertEqual(response.status_code, 404)

        response = self.client.post(
            reverse('faults_fault_update'),
            {
                'pk': fault.pk,
                'subject': 'hacked',
                'description': fault.description,
                'created_by_user': fault.created_by_user.pk,
            },
        )
        self.assertEqual(response.status_code, 404)
        fault.refresh_from_db()
        self.assertEqual(fault.subject, original_subject)

    # Workflow: any resolver can close a ticket that has no resolver assigned yet
    def test_resolver_can_close_unassigned_ticket(self):
        fault = FaultReportFactory(created_by_user=self.u_peter, assigned_to_user=None, closed=False)
        self.client.login(username='karel', password=self.u_karel_password)
        response = self.client.get(
            reverse('faults_fault_close_ticket', kwargs={'pk': fault.pk}),
            follow=True,
        )
        self.assertEqual(response.status_code, 200)

        fault.refresh_from_db()
        self.assertEqual(fault.closed, True)
        self.assertEqual(fault.assigned_to_user, self.u_karel)
        self.assertEqual(fault.logs.count(), 2)
        assigned, closed = fault.logs.all()
        self.assertEqual(assigned.type, assigned.TYPE_ASSIGNED)
        self.assertEqual(closed.type, closed.TYPE_CLOSED)

    def test_resolver_can_reopen_closed_ticket(self):
        fault = FaultReportFactory(created_by_user=self.u_peter, assigned_to_user=self.u_karel, closed=True)
        self.client.login(username='karel', password=self.u_karel_password)
        response = self.client.get(
            reverse('faults_fault_reopen_ticket', kwargs={'pk': fault.pk}),
            follow=True,
        )
        self.assertEqual(response.status_code, 200)

        fault.refresh_from_db()
        self.assertEqual(fault.closed, False)

    # Gallery: images can be uploaded when creating a fault
    def test_create_fault_with_gallery(self):
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
        fault = response.context['obj']
        self.assertEqual(fault.assets.count(), 1)
        self.assertTrue(fault.image_assets[0].file.name.startswith(f'faults/{fault.slug}/'))

    def test_create_fault_without_gallery(self):
        self.client.login(username='peter', password=self.u_peter_password)
        fault = self.create_fault_and_get_created_by(
            "peter", self.u_peter_password, {'pk': 0, 'subject': 'test', 'description': 'test'}
        )
        self.assertEqual(fault.assets.count(), 0)

    # Gallery: images can be uploaded when updating a fault
    def test_update_fault_with_gallery(self):
        self.client.login(username='jiri', password=self.u_jiri_password)
        response = self.client.post(
            self.update_url,
            {
                'pk': self.fault.pk,
                'subject': self.fault.subject,
                'description': self.fault.description,
                'created_by_user': self.fault.created_by_user.pk,
                'gallery': SimpleUploadedFile('foto.jpg', b'fake-jpg', content_type='image/jpeg'),
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.fault.refresh_from_db()
        self.assertEqual(self.fault.assets.count(), 1)
        self.assertTrue(self.fault.image_assets[0].file.name.startswith(f'faults/{self.fault.slug}/'))


class FaultsListTest(UserDataMixin, PreferencesDataMixin, TestCase):
    def setUp(self):
        self.client.login(username='jiri', password=self.u_jiri_password)

    def test_list_uses_dropdown_with_all_actions(self):
        FaultReportFactory(created_by_user=self.u_jiri, assigned_to_user=None, closed=False)
        response = self.client.get(reverse('faults_list'))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('action-menu', content)
        self.assertIn('sortable', content)

    def test_editable_fault_shows_edit_action_non_editable_does_not(self):
        # peter is a reporter only (not a resolver), so he can edit his own open fault but not someone else's.
        self.client.login(username='peter', password=self.u_peter_password)
        editable = FaultReportFactory(created_by_user=self.u_peter, assigned_to_user=None, closed=False)
        not_editable = FaultReportFactory(created_by_user=self.u_jarda, assigned_to_user=None, closed=False)
        response = self.client.get(reverse('faults_list'))
        content = response.content.decode()
        self.assertIn(reverse('faults_fault_edit', args=[editable.pk]), content)
        self.assertNotIn(reverse('faults_fault_edit', args=[not_editable.pk]), content)

    def test_closed_ticket_gets_closed_row_class(self):
        closed = FaultReportFactory(created_by_user=self.u_jiri, assigned_to_user=None, closed=True)
        open_fault = FaultReportFactory(created_by_user=self.u_jiri, assigned_to_user=None, closed=False)
        response = self.client.get(reverse('faults_list'))
        content = response.content.decode()

        rows_by_slug = {
            slug: classes
            for classes, slug in re.findall(
                r'<tr class="([^"]*)" onclick="location\.href=\'[^\']*/fault/([^/]+)/', content
            )
        }
        self.assertIn('closed-ticket', rows_by_slug[closed.slug])
        self.assertNotIn('closed-ticket', rows_by_slug[open_fault.slug])

    def test_edit_is_the_primary_action_when_editable(self):
        # Clicking the row already opens the detail page - the dropdown's primary (visible) icon
        # must be Edit, not another link to the same detail page.
        fault = FaultReportFactory(created_by_user=self.u_jiri, assigned_to_user=None, closed=False)
        response = self.client.get(reverse('faults_list'))
        content = response.content.decode()
        trigger = re.search(r'<a class="action-menu__trigger" href="([^"]+)"', content)
        self.assertIsNotNone(trigger)
        self.assertEqual(trigger.group(1), reverse('faults_fault_edit', args=[fault.pk]))

    def test_resolver_sees_close_ticket_action_with_confirm(self):
        fault = FaultReportFactory(created_by_user=self.u_jiri, assigned_to_user=None, closed=False)
        response = self.client.get(reverse('faults_list'))
        content = response.content.decode()
        close_url = reverse('faults_fault_close_ticket', args=[fault.pk])
        self.assertIn(close_url, content)
        # The close action must be guarded by a JS confirm() dialog, same as other destructive/state-changing actions.
        pattern = rf'onclick="if \(!confirm\(\'[^\']*\'\)\) return false;" href="{re.escape(close_url)}"'
        self.assertRegex(content, pattern)

    def test_close_ticket_action_hidden_for_already_closed_fault(self):
        fault = FaultReportFactory(created_by_user=self.u_jiri, assigned_to_user=None, closed=True)
        response = self.client.get(reverse('faults_list'))
        content = response.content.decode()
        self.assertNotIn(reverse('faults_fault_close_ticket', args=[fault.pk]), content)

    def test_close_ticket_action_hidden_for_non_resolver(self):
        self.client.login(username='peter', password=self.u_peter_password)
        fault = FaultReportFactory(created_by_user=self.u_peter, assigned_to_user=None, closed=False)
        response = self.client.get(reverse('faults_list'))
        content = response.content.decode()
        self.assertNotIn(reverse('faults_fault_close_ticket', args=[fault.pk]), content)


class FaultImageResizeTest(UserDataMixin, PreferencesDataMixin, TestCase):
    def setUp(self):
        self._media_dir = tempfile.TemporaryDirectory()
        self._media_override = override_settings(MEDIA_ROOT=self._media_dir.name)
        self._media_override.enable()
        self.addCleanup(self._media_override.disable)
        self.addCleanup(self._media_dir.cleanup)

    def test_oversized_gallery_photo_is_resized_on_create(self):
        self.client.login(username='peter', password=self.u_peter_password)
        photo = SimpleUploadedFile('big.jpg', make_image_bytes(4928, 3264, format='JPEG'), content_type='image/jpeg')
        response = self.client.post(
            reverse('faults_fault_create_save'),
            {'pk': 0, 'subject': 'test', 'description': 'test', 'created_by_user': '', 'gallery': photo},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        fault = response.context['obj']
        with Image.open(fault.image_assets[0].file.path) as saved:
            self.assertLessEqual(max(saved.size), 1920)

    def test_oversized_gallery_photo_is_resized_on_update(self):
        fault = FaultReportFactory(created_by_user=self.u_jiri, closed=False)
        self.client.login(username='jiri', password=self.u_jiri_password)
        photo = SimpleUploadedFile('big.jpg', make_image_bytes(4928, 3264, format='JPEG'), content_type='image/jpeg')
        response = self.client.post(
            reverse('faults_fault_update'),
            {
                'pk': fault.pk,
                'subject': fault.subject,
                'description': fault.description,
                'created_by_user': fault.created_by_user.pk,
                'gallery': photo,
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        fault.refresh_from_db()
        with Image.open(fault.image_assets[0].file.path) as saved:
            self.assertLessEqual(max(saved.size), 1920)

    def test_image_attachment_resized_pdf_attachment_untouched(self):
        fault = FaultReportFactory(created_by_user=self.u_jiri, closed=False)
        self.client.login(username='jiri', password=self.u_jiri_password)

        image_attachment = SimpleUploadedFile(
            'plan.png', make_image_bytes(3000, 2500, format='PNG'), content_type='image/png'
        )
        self.client.post(
            reverse('faults_fault_asset_save'),
            {'fault_pk': fault.pk, 'description': 'plan', 'file': image_attachment},
        )
        image_asset = models.FaultAsset.objects.get(fault_report=fault, description='plan')
        with Image.open(image_asset.file.path) as saved:
            self.assertLessEqual(max(saved.size), 1920)

        pdf_bytes = b'%PDF-1.4 not a real pdf but has the right extension'
        pdf_attachment = SimpleUploadedFile('doc.pdf', pdf_bytes, content_type='application/pdf')
        self.client.post(
            reverse('faults_fault_asset_save'),
            {'fault_pk': fault.pk, 'description': 'doc', 'file': pdf_attachment},
        )
        pdf_asset = models.FaultAsset.objects.get(fault_report=fault, description='doc')
        with pdf_asset.file.open('rb') as f:
            self.assertEqual(f.read(), pdf_bytes)
