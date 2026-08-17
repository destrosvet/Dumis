from django.test import TestCase
from django.urls import reverse

from ..models import Building, BuildingEntrance, BuildingUnit, BuildingUnitType, BuildingUnitUser
from .testdata import UserDataMixin


class BuildingUnitDataMixin(UserDataMixin):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.building = Building.objects.create(address="Sluneční 1", city="Praha", post_code="140 00")
        cls.entrance = BuildingEntrance.objects.create(building=cls.building, description="Vchod A", address="Sluneční 1")
        cls.flat_type = BuildingUnitType.objects.create(description="Byt")
        cls.unit = BuildingUnit.objects.create(
            building=cls.building,
            type=cls.flat_type,
            entrance=cls.entrance,
            registration_id="1/1",
            description="Byt 1.1",
            numerator=1,
            denominator=100,
        )
        cls.other_unit = BuildingUnit.objects.create(
            building=cls.building,
            type=cls.flat_type,
            entrance=cls.entrance,
            registration_id="1/2",
            description="Byt 1.2",
            numerator=1,
            denominator=100,
        )


class BuildingUnitOwnersAdminTest(BuildingUnitDataMixin, TestCase):
    def setUp(self):
        self.client.login(username="jarda", password=self.u_jarda_password)

    def test_owners_view_shows_owners_and_tenants(self):
        BuildingUnitUser.objects.create(building_unit=self.unit, user=self.u_peter, role=BuildingUnitUser.ROLE_OWNER)
        BuildingUnitUser.objects.create(building_unit=self.unit, user=self.u_jiri, role=BuildingUnitUser.ROLE_TENANT)

        response = self.client.get(reverse("admin_building_unit_owners", kwargs={"pk": self.unit.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["owner_list"]), [self.u_peter])
        self.assertEqual(list(response.context["tenant_list"]), [self.u_jiri])

    def test_save_assigns_owner_and_tenant(self):
        response = self.client.post(
            reverse("admin_building_unit_owners_save"),
            {"pk": self.unit.pk, "owner_id": self.u_peter.pk, "role": BuildingUnitUser.ROLE_OWNER},
        )
        self.assertRedirects(response, reverse("admin_building_unit_owners", kwargs={"pk": self.unit.pk}))
        self.assertEqual(list(self.unit.owners), [self.u_peter])

        self.client.post(
            reverse("admin_building_unit_owners_save"),
            {"pk": self.unit.pk, "owner_id": self.u_jiri.pk, "role": BuildingUnitUser.ROLE_TENANT},
        )
        self.assertEqual(list(self.unit.owners), [self.u_peter])
        self.assertEqual(list(self.unit.tenants), [self.u_jiri])

    def test_same_user_can_be_owner_and_tenant(self):
        self.client.post(
            reverse("admin_building_unit_owners_save"),
            {"pk": self.unit.pk, "owner_id": self.u_peter.pk, "role": BuildingUnitUser.ROLE_OWNER},
        )
        self.client.post(
            reverse("admin_building_unit_owners_save"),
            {"pk": self.unit.pk, "owner_id": self.u_peter.pk, "role": BuildingUnitUser.ROLE_TENANT},
        )
        self.assertEqual(list(self.unit.owners), [self.u_peter])
        self.assertEqual(list(self.unit.tenants), [self.u_peter])

    def test_delete_by_role_keeps_other_role(self):
        BuildingUnitUser.objects.create(building_unit=self.unit, user=self.u_peter, role=BuildingUnitUser.ROLE_OWNER)
        BuildingUnitUser.objects.create(building_unit=self.unit, user=self.u_peter, role=BuildingUnitUser.ROLE_TENANT)

        self.client.get(
            reverse(
                "admin_building_unit_owners_delete",
                kwargs={"pk": self.unit.pk, "role": BuildingUnitUser.ROLE_OWNER, "user": self.u_peter.pk},
            )
        )
        self.assertEqual(list(self.unit.owners), [])
        self.assertEqual(list(self.unit.tenants), [self.u_peter])

    def test_owner_page_requires_admin_permission(self):
        self.client.logout()
        self.client.login(username="jiri", password=self.u_jiri_password)
        response = self.client.get(reverse("admin_building_unit_owners", kwargs={"pk": self.unit.pk}))
        self.assertEqual(response.status_code, 302)


class UserOwnsAdminTest(BuildingUnitDataMixin, TestCase):
    def setUp(self):
        self.client.login(username="jarda", password=self.u_jarda_password)

    def test_user_owns_view_shows_memberships_with_roles(self):
        BuildingUnitUser.objects.create(building_unit=self.unit, user=self.u_peter, role=BuildingUnitUser.ROLE_OWNER)
        BuildingUnitUser.objects.create(
            building_unit=self.other_unit, user=self.u_peter, role=BuildingUnitUser.ROLE_TENANT
        )

        response = self.client.get(reverse("admin_user_owns", kwargs={"pk": self.u_peter.pk}))
        self.assertEqual(response.status_code, 200)
        memberships = list(response.context["membership_list"])
        self.assertEqual(len(memberships), 2)
        roles = {m.role for m in memberships}
        self.assertEqual(roles, {BuildingUnitUser.ROLE_OWNER, BuildingUnitUser.ROLE_TENANT})
        units = {m.building_unit.pk for m in memberships}
        self.assertEqual(units, {self.unit.pk, self.other_unit.pk})
        self.assertEqual(
            [m for m in memberships if m.role == BuildingUnitUser.ROLE_OWNER],
            list(response.context["owner_list"]),
        )
        self.assertEqual(len(response.context["tenant_list"]), 1)
        content = response.content.decode()
        self.assertIn("member-grid", content)

    def test_user_owns_assign_form_has_styled_select_and_button(self):
        response = self.client.get(reverse("admin_user_owns", kwargs={"pk": self.u_peter.pk}))
        content = response.content.decode()
        self.assertIn('class="common-input" name="unit_id"', content)
        self.assertIn('class="btn--primary" type="submit" value="Add"', content)

    def test_user_detail_shows_units_in_sidebar(self):
        BuildingUnitUser.objects.create(building_unit=self.unit, user=self.u_peter, role=BuildingUnitUser.ROLE_OWNER)
        response = self.client.get(reverse("admin_user_detail", kwargs={"pk": self.u_peter.pk}))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn("edit-layout", content)
        self.assertIn("edit-sidebar", content)
        self.assertIn("Byt - 1/1 - Byt 1.1", content)
        self.assertIn(f"/admin_building_unit_owners/{self.unit.pk}/", content)
        self.assertIn("admin_user_owns", content)

    def test_save_assigns_unit_with_role(self):
        response = self.client.post(
            reverse("admin_user_owns_save"),
            {"pk": self.u_peter.pk, "unit_id": self.unit.pk, "role": BuildingUnitUser.ROLE_TENANT},
        )
        self.assertRedirects(response, reverse("admin_user_owns", kwargs={"pk": self.u_peter.pk}))
        memberships = self.u_peter.unit_memberships.all()
        self.assertEqual(memberships.count(), 1)
        self.assertEqual(memberships.first().building_unit, self.unit)
        self.assertEqual(memberships.first().role, BuildingUnitUser.ROLE_TENANT)

    def test_delete_membership(self):
        BuildingUnitUser.objects.create(building_unit=self.unit, user=self.u_peter, role=BuildingUnitUser.ROLE_OWNER)
        self.client.get(
            reverse(
                "admin_user_owns_delete",
                kwargs={"pk": self.u_peter.pk, "unit": self.unit.pk, "role": BuildingUnitUser.ROLE_OWNER},
            )
        )
        self.assertEqual(self.u_peter.unit_memberships.count(), 0)

    def test_user_owns_page_requires_admin_permission(self):
        self.client.logout()
        self.client.login(username="jiri", password=self.u_jiri_password)
        response = self.client.get(reverse("admin_user_owns", kwargs={"pk": self.u_peter.pk}))
        self.assertEqual(response.status_code, 302)


class MyUnitsTest(BuildingUnitDataMixin, TestCase):
    def test_my_units_shows_role(self):
        BuildingUnitUser.objects.create(building_unit=self.unit, user=self.u_peter, role=BuildingUnitUser.ROLE_OWNER)
        BuildingUnitUser.objects.create(
            building_unit=self.other_unit, user=self.u_peter, role=BuildingUnitUser.ROLE_TENANT
        )
        self.client.login(username="peter", password=self.u_peter_password)

        response = self.client.get(reverse("personal_my_units"))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn("Byt 1.1", content)
        self.assertIn("Byt 1.2", content)
        self.assertIn("Owner", content)
        self.assertIn("Tenant", content)

    def test_model_owners_and_tenants_properties(self):
        BuildingUnitUser.objects.create(building_unit=self.unit, user=self.u_peter, role=BuildingUnitUser.ROLE_OWNER)
        BuildingUnitUser.objects.create(building_unit=self.unit, user=self.u_jiri, role=BuildingUnitUser.ROLE_TENANT)
        self.assertEqual(list(self.unit.owners), [self.u_peter])
        self.assertEqual(list(self.unit.tenants), [self.u_jiri])
        self.assertEqual(list(self.u_peter.building_units.all()), [self.unit])