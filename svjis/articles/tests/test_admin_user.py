from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from ..models import BuildingUnitUser, UserProfile
from ..utils import merge_users
from .factories.fault_report import FaultReportFactory
from .test_admin_units import BuildingUnitDataMixin


class AdminUserDeleteTest(BuildingUnitDataMixin, TestCase):
    def setUp(self):
        self.client.login(username="jarda", password=self.u_jarda_password)

    def test_delete_removes_user(self):
        response = self.client.get(reverse("admin_user_delete", kwargs={"pk": self.u_karel.pk}))
        self.assertRedirects(response, reverse("admin_user"))
        self.assertFalse(User.objects.filter(pk=self.u_karel.pk).exists())

    def test_cannot_delete_own_account(self):
        response = self.client.get(reverse("admin_user_delete", kwargs={"pk": self.u_jarda.pk}))
        self.assertRedirects(response, reverse("admin_user"))
        self.assertTrue(User.objects.filter(pk=self.u_jarda.pk).exists())

    def test_list_offers_delete_for_others_but_not_self(self):
        response = self.client.get(reverse("admin_user"))
        content = response.content.decode()
        self.assertIn(reverse("admin_user_delete", kwargs={"pk": self.u_karel.pk}), content)
        self.assertNotIn(reverse("admin_user_delete", kwargs={"pk": self.u_jarda.pk}), content)

    def test_delete_requires_admin_permission(self):
        self.client.logout()
        self.client.login(username="jiri", password=self.u_jiri_password)
        response = self.client.get(reverse("admin_user_delete", kwargs={"pk": self.u_karel.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(pk=self.u_karel.pk).exists())


class MergeUsersUtilTest(BuildingUnitDataMixin, TestCase):
    def test_merge_reassigns_building_units_and_dedupes_duplicates(self):
        BuildingUnitUser.objects.create(building_unit=self.unit, user=self.u_peter, role=BuildingUnitUser.ROLE_OWNER)
        BuildingUnitUser.objects.create(
            building_unit=self.other_unit, user=self.u_karel, role=BuildingUnitUser.ROLE_OWNER
        )
        # Duplicate: both peter and karel already own `unit` as owner.
        BuildingUnitUser.objects.create(building_unit=self.unit, user=self.u_karel, role=BuildingUnitUser.ROLE_OWNER)

        merge_users(self.u_peter, [self.u_karel])

        self.assertFalse(User.objects.filter(pk=self.u_karel.pk).exists())
        memberships = BuildingUnitUser.objects.filter(user=self.u_peter)
        self.assertEqual(
            set(memberships.values_list("building_unit_id", "role")),
            {(self.unit.pk, BuildingUnitUser.ROLE_OWNER), (self.other_unit.pk, BuildingUnitUser.ROLE_OWNER)},
        )

    def test_merge_reassigns_authored_content_and_groups(self):
        fault = FaultReportFactory(created_by_user=self.u_karel)
        self.u_karel.groups.add(self.g_vendor)

        merge_users(self.u_peter, [self.u_karel])

        fault.refresh_from_db()
        self.assertEqual(fault.created_by_user_id, self.u_peter.pk)
        self.assertIn(self.g_vendor, self.u_peter.groups.all())
        self.assertFalse(User.objects.filter(pk=self.u_karel.pk).exists())

    def test_merge_keeps_targets_own_profile(self):
        profile = UserProfile.objects.create(user=self.u_peter, city="Brno")

        merge_users(self.u_peter, [self.u_karel])

        profile.refresh_from_db()
        self.assertEqual(profile.city, "Brno")


class AdminUserMergeSaveViewTest(BuildingUnitDataMixin, TestCase):
    def setUp(self):
        self.client.login(username="jarda", password=self.u_jarda_password)

    def test_merge_save_reassigns_and_deletes_sources(self):
        BuildingUnitUser.objects.create(building_unit=self.unit, user=self.u_karel, role=BuildingUnitUser.ROLE_OWNER)

        response = self.client.post(
            reverse("admin_user_merge_save"),
            {"target": self.u_peter.pk, "sources": [self.u_peter.pk, self.u_karel.pk]},
        )

        self.assertRedirects(response, reverse("admin_user_detail", kwargs={"pk": self.u_peter.pk}))
        self.assertFalse(User.objects.filter(pk=self.u_karel.pk).exists())
        self.assertEqual(list(self.unit.owners), [self.u_peter])

    def test_cannot_merge_own_account_as_a_source(self):
        response = self.client.post(
            reverse("admin_user_merge_save"),
            {"target": self.u_karel.pk, "sources": [self.u_karel.pk, self.u_jarda.pk]},
        )

        self.assertRedirects(response, reverse("admin_user"))
        self.assertTrue(User.objects.filter(pk=self.u_jarda.pk).exists())

    def test_requires_at_least_one_other_selected_user(self):
        response = self.client.post(
            reverse("admin_user_merge_save"), {"target": self.u_peter.pk, "sources": [self.u_peter.pk]}
        )

        self.assertRedirects(response, reverse("admin_user"))

    def test_merge_requires_admin_permission(self):
        self.client.logout()
        self.client.login(username="jiri", password=self.u_jiri_password)

        response = self.client.post(
            reverse("admin_user_merge_save"),
            {"target": self.u_peter.pk, "sources": [self.u_peter.pk, self.u_karel.pk]},
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(pk=self.u_karel.pk).exists())
