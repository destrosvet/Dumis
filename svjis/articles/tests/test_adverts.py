import io
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from .. import models
from .testdata import UserDataMixin


def make_image_bytes(width, height, format='PNG'):
    buffer = io.BytesIO()
    Image.new('RGB', (width, height), color=(120, 140, 160)).save(buffer, format=format)
    return buffer.getvalue()


class AdvertsTest(UserDataMixin, TestCase):
    def create_advert(self, username, password, advert_form, expected_status):
        logged_in = self.client.login(username=username, password=password)
        self.assertTrue(logged_in)
        response = self.client.post(
            reverse('adverts_save'),
            advert_form,
            follow=False,
        )
        if expected_status == 302:
            self.assertEqual(response.status_code, expected_status)
            self.assertEqual(response.url, '/adverts_edit/1/')
            response = self.client.get(reverse('adverts_list'), follow=True)
            self.assertEqual(response.status_code, 200)

            adverts = response.context['object_list']
            self.assertEqual(len(adverts), 1)
            return adverts[0]
        else:
            self.assertEqual(response.status_code, expected_status)
            return None

    def test_hide_adverts_of_deactivated_user(self):
        # create advert
        self.create_advert(
            "peter",
            self.u_peter_password,
            {
                'pk': 0,
                'type': 1,
                'header': 'testing advert',
                'body': 'testing advert body',
                'phone': '123',
                'email': 'test@test.com',
                'published': True,
            },
            302,
        )

        # advert is visible for other users
        logged_in = self.client.login(username='jiri', password=self.u_jiri_password)
        self.assertTrue(logged_in)

        response = self.client.get(reverse('adverts_list'), follow=True)
        self.assertEqual(response.status_code, 200)

        adverts = response.context['object_list']
        self.assertEqual(len(adverts), 1)

        advert = adverts[0]
        self.assertEqual(advert.created_by_user, self.u_peter)

        # disable advert owner
        self.u_peter.is_active = False
        self.u_peter.save()

        # advert is not visible for other users
        response = self.client.get(reverse('adverts_list'), follow=True)
        self.assertEqual(response.status_code, 200)

        adverts = response.context['object_list']
        self.assertEqual(len(adverts), 0)

    def test_advert_update(self):
        advert = self.create_advert(
            "peter",
            self.u_peter_password,
            {
                'pk': 0,
                'type': 1,
                'header': 'testing advert',
                'body': 'testing advert body',
                'phone': '123',
                'email': 'test@test.com',
                'published': True,
            },
            302,
        )
        self.assertEqual(advert.header, 'testing advert')

        advert = self.create_advert(
            "peter",
            self.u_peter_password,
            {
                'pk': advert.pk,
                'type': 1,
                'header': 'testing advert 2',
                'body': 'testing advert body',
                'phone': '123',
                'email': 'test@test.com',
                'published': True,
            },
            302,
        )
        self.assertEqual(advert.header, 'testing advert 2')

    def test_advert_update_by_another_user(self):
        advert = self.create_advert(
            "peter",
            self.u_peter_password,
            {
                'pk': 0,
                'type': 1,
                'header': 'testing advert',
                'body': 'testing advert body',
                'phone': '123',
                'email': 'test@test.com',
                'published': True,
            },
            302,
        )
        self.assertEqual(advert.header, 'testing advert')

        advert = self.create_advert(
            "jiri",
            self.u_jiri_password,
            {
                'pk': advert.pk,
                'type': 1,
                'header': 'testing advert 2',
                'body': 'testing advert body',
                'phone': '123',
                'email': 'test@test.com',
                'published': True,
            },
            404,
        )


class AdvertImageResizeTest(UserDataMixin, TestCase):
    def setUp(self):
        self._media_dir = tempfile.TemporaryDirectory()
        self._media_override = override_settings(MEDIA_ROOT=self._media_dir.name)
        self._media_override.enable()
        self.addCleanup(self._media_override.disable)
        self.addCleanup(self._media_dir.cleanup)
        self.client.login(username='peter', password=self.u_peter_password)

    def test_oversized_cover_image_and_gallery_photo_are_resized(self):
        cover = SimpleUploadedFile('cover.jpg', make_image_bytes(4928, 3264, format='JPEG'), content_type='image/jpeg')
        gallery_photo = SimpleUploadedFile(
            'gallery.jpg', make_image_bytes(4000, 3000, format='JPEG'), content_type='image/jpeg'
        )
        response = self.client.post(
            reverse('adverts_save'),
            {
                'pk': 0,
                'type': self.advert_types[0].pk,
                'header': 'photo advert',
                'body': 'body',
                'phone': '123',
                'email': 'test@test.com',
                'published': True,
                'cover_image': cover,
                'gallery': gallery_photo,
            },
        )
        self.assertEqual(response.status_code, 302)

        advert = models.Advert.objects.get(header='photo advert')
        with Image.open(advert.cover_image.path) as saved_cover:
            self.assertLessEqual(max(saved_cover.size), 1920)

        asset = models.AdvertAsset.objects.get(advert=advert)
        with Image.open(asset.file.path) as saved_gallery:
            self.assertLessEqual(max(saved_gallery.size), 1920)

    def test_oversized_image_attachment_is_resized_pdf_attachment_untouched(self):
        advert = models.Advert.objects.create(
            type=self.advert_types[0], header='attach test', body='body', created_by_user=self.u_peter
        )

        image_attachment = SimpleUploadedFile(
            'plan.png', make_image_bytes(3000, 2500, format='PNG'), content_type='image/png'
        )
        response = self.client.post(
            reverse('adverts_asset_save'),
            {'advert_pk': advert.pk, 'description': 'plan', 'file': image_attachment},
        )
        self.assertEqual(response.status_code, 302)
        asset = models.AdvertAsset.objects.get(advert=advert, description='plan')
        with Image.open(asset.file.path) as saved:
            self.assertLessEqual(max(saved.size), 1920)

        pdf_bytes = b'%PDF-1.4 not a real pdf but has the right extension'
        pdf_attachment = SimpleUploadedFile('doc.pdf', pdf_bytes, content_type='application/pdf')
        response = self.client.post(
            reverse('adverts_asset_save'),
            {'advert_pk': advert.pk, 'description': 'doc', 'file': pdf_attachment},
        )
        self.assertEqual(response.status_code, 302)
        pdf_asset = models.AdvertAsset.objects.get(advert=advert, description='doc')
        with pdf_asset.file.open('rb') as f:
            self.assertEqual(f.read(), pdf_bytes)
