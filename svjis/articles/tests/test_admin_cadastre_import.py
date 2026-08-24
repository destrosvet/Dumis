from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from ..cadastre_import import ParsedCadastreExtract, ParsedOwner, ParsedUnit
from ..models import Building, BuildingUnit, BuildingUnitUser
from .testdata import UserDataMixin


def _sample_extract():
    ok_unit = ParsedUnit(
        unit_no='2919/17',
        usage='byt',
        unit_lv='5422',
        building_share_numerator=75,
        building_share_denominator=5593,
        owner_line_count=2,
        owners=[
            ParsedOwner('701215/3984', 'Joanidis Tomáš', 'Tomáš', 'Joanidis', 1, 2),
            ParsedOwner('695406/3974', 'Lacinová Lenka', 'Lenka', 'Lacinová', 1, 2),
        ],
    )
    bad_unit = ParsedUnit(
        unit_no='2919/1',
        usage='jiný nebytový prostor',
        unit_lv='5413',
        building_share_numerator=2475,
        building_share_denominator=5593,
        owner_line_count=2,
        owners=[
            ParsedOwner('47114983', 'Česká pošta, s.p.', '', 'Česká pošta, s.p.'),
            ParsedOwner('00000001-001', 'Česká republika', '', 'Česká republika'),
        ],
    )
    return ParsedCadastreExtract(
        lv_number='4219', cadastral_area='Královo Pole', building_label='č.p. 2919', units=[ok_unit, bad_unit]
    )


class CadastreImportUploadViewTest(UserDataMixin, TestCase):
    def setUp(self):
        self.client.login(username="jarda", password=self.u_jarda_password)

    def test_get_renders_upload_form(self):
        response = self.client.get(reverse('admin_building_unit_import'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'enctype="multipart/form-data"', response.content)

    def test_requires_admin_permission(self):
        self.client.logout()
        self.client.login(username="jiri", password=self.u_jiri_password)
        response = self.client.get(reverse('admin_building_unit_import'))
        self.assertEqual(response.status_code, 302)

    def test_post_without_file_shows_error(self):
        response = self.client.post(reverse('admin_building_unit_import'), {}, follow=True)
        self.assertContains(response, 'Please choose a PDF file')

    @patch('articles.views_admin.cadastre_import.parse_cadastre_pdf')
    def test_post_with_file_shows_preview_and_stores_session(self, mock_parse):
        mock_parse.return_value = _sample_extract()
        pdf = SimpleUploadedFile('vypis.pdf', b'%PDF-1.4 fake', content_type='application/pdf')

        response = self.client.post(reverse('admin_building_unit_import'), {'pdf_file': pdf})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '2919/17')
        self.assertContains(response, '2919/1')
        self.assertContains(response, 'do not add up to 1/1')
        session_data = self.client.session['cadastre_import_pending']
        self.assertEqual(len(session_data['units']), 2)


class CadastreImportSaveViewTest(UserDataMixin, TestCase):
    def setUp(self):
        self.client.login(username="jarda", password=self.u_jarda_password)

    def _prime_session(self):
        session = self.client.session
        session['cadastre_import_pending'] = {
            'units': [
                {
                    'unit_no': '2919/17',
                    'usage': 'byt',
                    'building_share_numerator': 75,
                    'building_share_denominator': 5593,
                    'owners': [
                        {'share_numerator': 1, 'share_denominator': 2},
                        {'share_numerator': 1, 'share_denominator': 2},
                    ],
                },
                {
                    'unit_no': '2919/1',
                    'usage': 'jiný nebytový prostor',
                    'building_share_numerator': 2475,
                    'building_share_denominator': 5593,
                    'owners': [{'share_numerator': None, 'share_denominator': None}],
                },
            ]
        }
        session.save()

    def test_creates_unit_and_new_users_for_included_unit_only(self):
        self._prime_session()

        response = self.client.post(
            reverse('admin_building_unit_import_save'),
            {
                'unit_0_include': 'on',
                'unit_0_registration_id': '2919/17',
                'unit_0_description': '2919/17',
                'unit_0_numerator': '75',
                'unit_0_denominator': '5593',
                'unit_0_owner_0_first_name': 'Tomáš',
                'unit_0_owner_0_last_name': 'Joanidis',
                'unit_0_owner_0_existing_user': '0',
                'unit_0_owner_1_first_name': 'Lenka',
                'unit_0_owner_1_last_name': 'Lacinová',
                'unit_0_owner_1_existing_user': '0',
                # unit_1 (2919/1) intentionally left unchecked - not included
                'unit_1_registration_id': '2919/1',
                'unit_1_description': '2919/1',
            },
        )

        self.assertRedirects(response, reverse('admin_building_unit'))
        self.assertEqual(BuildingUnit.objects.count(), 1)
        unit = BuildingUnit.objects.get()
        self.assertEqual(unit.registration_id, '2919/17')
        self.assertEqual(unit.building, Building.objects.get(pk=1))

        joanidis = User.objects.get(first_name='Tomáš', last_name='Joanidis')
        lacinova = User.objects.get(first_name='Lenka', last_name='Lacinová')
        membership = BuildingUnitUser.objects.get(building_unit=unit, user=joanidis)
        self.assertEqual((membership.share_numerator, membership.share_denominator), (1, 2))
        self.assertEqual(BuildingUnitUser.objects.filter(building_unit=unit).count(), 2)
        self.assertIn(lacinova, unit.owners)

        self.assertFalse('cadastre_import_pending' in self.client.session)

    def test_links_to_existing_user_instead_of_creating_new_one(self):
        self._prime_session()

        response = self.client.post(
            reverse('admin_building_unit_import_save'),
            {
                'unit_0_include': 'on',
                'unit_0_registration_id': '2919/17',
                'unit_0_description': '2919/17',
                'unit_0_numerator': '75',
                'unit_0_denominator': '5593',
                'unit_0_owner_0_existing_user': str(self.u_peter.pk),
                'unit_0_owner_1_first_name': 'Lenka',
                'unit_0_owner_1_last_name': 'Lacinová',
                'unit_0_owner_1_existing_user': '0',
            },
        )

        self.assertEqual(response.status_code, 302)
        unit = BuildingUnit.objects.get(registration_id='2919/17')
        self.assertIn(self.u_peter, unit.owners)
        # existing user re-linked, not duplicated
        self.assertEqual(User.objects.filter(pk=self.u_peter.pk).count(), 1)

    def test_expired_session_redirects_with_error(self):
        response = self.client.post(reverse('admin_building_unit_import_save'), {}, follow=True)
        self.assertContains(response, 'import session has expired')
