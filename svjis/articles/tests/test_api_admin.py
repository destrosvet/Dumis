from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from ..models import Building, BuildingUnit, BuildingUnitType, BuildingUnitUser
from .testdata import UserDataMixin


class AdminBuildingUnitCreateAPITest(UserDataMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.unit_type = BuildingUnitType.objects.create(description="Byt")

    def test_admin_can_create_building_unit(self):
        self.client.login(username="jarda", password=self.u_jarda_password)
        response = self.client.post(
            reverse('api_admin_building_unit_create'),
            {
                'type': self.unit_type.pk,
                'registration_id': '2919/1',
                'description': '2919/1',
                'numerator': 1,
                'denominator': 100,
            },
        )
        self.assertEqual(response.status_code, 201, response.content)
        unit = BuildingUnit.objects.get()
        self.assertEqual(unit.registration_id, '2919/1')
        self.assertEqual(unit.building, Building.objects.get(pk=1))

    def test_requires_building_permission(self):
        self.client.login(username="peter", password=self.u_peter_password)
        response = self.client.post(
            reverse('api_admin_building_unit_create'),
            {
                'type': self.unit_type.pk,
                'registration_id': '2919/1',
                'description': '2919/1',
                'numerator': 1,
                'denominator': 100,
            },
        )
        self.assertEqual(response.status_code, 403)

    def test_anonymous_is_rejected(self):
        response = self.client.post(
            reverse('api_admin_building_unit_create'),
            {
                'type': self.unit_type.pk,
                'registration_id': '2919/1',
                'description': '2919/1',
                'numerator': 1,
                'denominator': 100,
            },
        )
        self.assertEqual(response.status_code, 403)


class AdminUserCreateAPITest(UserDataMixin, TestCase):
    def test_admin_can_create_user(self):
        self.client.login(username="jarda", password=self.u_jarda_password)
        response = self.client.post(
            reverse('api_admin_user_create'),
            {'username': 'novy_vlastnik', 'first_name': 'Nový', 'last_name': 'Vlastník'},
        )
        self.assertEqual(response.status_code, 201, response.content)
        user = User.objects.get(username='novy_vlastnik')
        self.assertTrue(hasattr(user, 'userprofile'))

    def test_requires_users_permission(self):
        self.client.login(username="peter", password=self.u_peter_password)
        response = self.client.post(
            reverse('api_admin_user_create'), {'username': 'x', 'first_name': 'X', 'last_name': 'Y'}
        )
        self.assertEqual(response.status_code, 403)


class AdminBuildingUnitOwnerCreateAPITest(UserDataMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.building = Building.objects.create(address="Sluneční 1")
        cls.unit_type = BuildingUnitType.objects.create(description="Byt")
        cls.unit = BuildingUnit.objects.create(
            building=cls.building,
            type=cls.unit_type,
            registration_id='2919/1',
            description='2919/1',
            numerator=1,
            denominator=100,
        )

    def test_admin_can_assign_owner_with_share(self):
        self.client.login(username="jarda", password=self.u_jarda_password)
        response = self.client.post(
            reverse('api_admin_building_unit_owner_create', kwargs={'pk': self.unit.pk}),
            {
                'user': self.u_peter.pk,
                'role': BuildingUnitUser.ROLE_OWNER,
                'share_numerator': 1,
                'share_denominator': 2,
            },
        )
        self.assertEqual(response.status_code, 201, response.content)
        membership = BuildingUnitUser.objects.get(building_unit=self.unit, user=self.u_peter)
        self.assertEqual((membership.share_numerator, membership.share_denominator), (1, 2))

    def test_requires_building_permission(self):
        self.client.login(username="peter", password=self.u_peter_password)
        response = self.client.post(
            reverse('api_admin_building_unit_owner_create', kwargs={'pk': self.unit.pk}),
            {'user': self.u_peter.pk, 'role': BuildingUnitUser.ROLE_OWNER},
        )
        self.assertEqual(response.status_code, 403)
