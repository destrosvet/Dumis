from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType

from ..models import (
    Advert,
    Board,
    BuildingEntrance,
    BuildingUnit,
    CustomFieldDefinition,
    CustomFieldValue,
    FaultReport,
    UserProfile,
)
from .factories.fault_report import FaultReportFactory
from .testdata import UserDataMixin
from .test_admin_units import BuildingUnitDataMixin


class CustomFieldDefinitionAdminTest(UserDataMixin, TestCase):
    def setUp(self):
        self.client.login(username="jarda", password=self.u_jarda_password)
        self.user_ct = ContentType.objects.get_for_model(User)

    def test_list_requires_permission(self):
        self.client.logout()
        self.client.login(username="jiri", password=self.u_jiri_password)
        response = self.client.get(reverse("admin_custom_field"))
        self.assertEqual(response.status_code, 302)

    def test_create_definition(self):
        response = self.client.post(
            reverse("admin_custom_field_save"),
            {
                "pk": 0,
                "content_type": self.user_ct.pk,
                "name": "Čip",
                "field_type": CustomFieldDefinition.TYPE_NUMBER,
                "enum_options": "",
            },
        )
        self.assertRedirects(response, reverse("admin_custom_field"))
        d = CustomFieldDefinition.objects.get(name="Čip")
        self.assertEqual(d.content_type, self.user_ct)
        self.assertEqual(d.field_type, CustomFieldDefinition.TYPE_NUMBER)

    def test_delete_definition_cascades_values(self):
        d = CustomFieldDefinition.objects.create(
            content_type=self.user_ct, name="Čip", field_type=CustomFieldDefinition.TYPE_NUMBER
        )
        CustomFieldValue.objects.create(
            field_definition=d, content_type=self.user_ct, object_id=self.u_peter.pk, value="2"
        )
        self.client.get(reverse("admin_custom_field_delete", kwargs={"pk": d.pk}))
        self.assertFalse(CustomFieldDefinition.objects.filter(pk=d.pk).exists())
        self.assertFalse(CustomFieldValue.objects.exists())


class CustomFieldValueOnUserEditTest(UserDataMixin, TestCase):
    def setUp(self):
        self.client.login(username="jarda", password=self.u_jarda_password)
        UserProfile.objects.get_or_create(user=self.u_peter)
        self.user_ct = ContentType.objects.get_for_model(User)
        self.d_number = CustomFieldDefinition.objects.create(
            content_type=self.user_ct, name="Čip", field_type=CustomFieldDefinition.TYPE_NUMBER
        )
        self.d_bool = CustomFieldDefinition.objects.create(
            content_type=self.user_ct, name="Aktivní čip", field_type=CustomFieldDefinition.TYPE_BOOLEAN
        )
        self.d_enum = CustomFieldDefinition.objects.create(
            content_type=self.user_ct,
            name="Velikost",
            field_type=CustomFieldDefinition.TYPE_ENUM,
            enum_options="S,M,L",
        )

    def _post_user_save(self, **custom_field_values):
        data = {
            "pk": self.u_peter.pk,
            "first_name": self.u_peter.first_name,
            "last_name": self.u_peter.last_name,
            "email": self.u_peter.email,
            "username": self.u_peter.username,
            "is_active": "on",
        }
        data.update(custom_field_values)
        return self.client.post(reverse("admin_user_save"), data)

    def test_save_number_field(self):
        self._post_user_save(**{f"customfield_{self.d_number.pk}": "3"})
        value = CustomFieldValue.objects.get(field_definition=self.d_number, object_id=self.u_peter.pk)
        self.assertEqual(value.value, "3")

    def test_reject_non_numeric_value(self):
        self._post_user_save(**{f"customfield_{self.d_number.pk}": "abc"})
        self.assertFalse(CustomFieldValue.objects.filter(field_definition=self.d_number).exists())

    def test_boolean_checkbox_round_trip(self):
        self._post_user_save(**{f"customfield_{self.d_bool.pk}": "on"})
        self.assertEqual(CustomFieldValue.objects.get(field_definition=self.d_bool).value, "1")

        # Unchecked boxes are simply absent from POST data - this must clear the stored value.
        self._post_user_save()
        self.assertFalse(CustomFieldValue.objects.filter(field_definition=self.d_bool).exists())

    def test_enum_field_rejects_invalid_option(self):
        self._post_user_save(**{f"customfield_{self.d_enum.pk}": "XL"})
        self.assertFalse(CustomFieldValue.objects.filter(field_definition=self.d_enum).exists())

        self._post_user_save(**{f"customfield_{self.d_enum.pk}": "M"})
        self.assertEqual(CustomFieldValue.objects.get(field_definition=self.d_enum).value, "M")

    def test_edit_page_shows_existing_value(self):
        CustomFieldValue.objects.create(
            field_definition=self.d_number, content_type=self.user_ct, object_id=self.u_peter.pk, value="5"
        )
        response = self.client.get(reverse("admin_user_edit", kwargs={"pk": self.u_peter.pk}))
        content = response.content.decode()
        self.assertIn(f'name="customfield_{self.d_number.pk}"', content)
        self.assertIn('value="5"', content)

    def test_detail_page_shows_custom_fields_card(self):
        CustomFieldValue.objects.create(
            field_definition=self.d_number, content_type=self.user_ct, object_id=self.u_peter.pk, value="5"
        )
        response = self.client.get(reverse("admin_user_detail", kwargs={"pk": self.u_peter.pk}))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn("Čip", content)
        self.assertIn("5", content)

    def test_detail_page_hides_card_when_no_definitions_for_another_user(self):
        CustomFieldDefinition.objects.all().delete()
        response = self.client.get(reverse("admin_user_detail", kwargs={"pk": self.u_peter.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("customfield_", response.content.decode())


class CustomFieldValueOnAdvertEditTest(UserDataMixin, TestCase):
    def setUp(self):
        UserProfile.objects.get_or_create(user=self.u_peter)
        self.advert_ct = ContentType.objects.get_for_model(Advert)
        self.d_price = CustomFieldDefinition.objects.create(
            content_type=self.advert_ct, name="Cena", field_type=CustomFieldDefinition.TYPE_NUMBER
        )
        self.client.login(username="peter", password=self.u_peter_password)

    def test_save_custom_field_on_own_advert(self):
        response = self.client.post(
            reverse("adverts_save"),
            {
                "pk": 0,
                "type": self.advert_types[0].pk,
                "header": "testing advert",
                "body": "testing advert body",
                "phone": "123",
                "email": "test@test.com",
                "published": True,
                f"customfield_{self.d_price.pk}": "1500",
            },
        )
        self.assertEqual(response.status_code, 302)
        advert = Advert.objects.get(header="testing advert")
        value = CustomFieldValue.objects.get(field_definition=self.d_price, object_id=advert.pk)
        self.assertEqual(value.value, "1500")

    def test_edit_page_renders_in_create_and_edit_mode(self):
        response = self.client.get(reverse("adverts_edit", kwargs={"pk": 0}))
        self.assertEqual(response.status_code, 200)

        advert = Advert.objects.create(
            type=self.advert_types[0],
            header="existing advert",
            body="body",
            created_by_user=self.u_peter,
        )
        CustomFieldValue.objects.create(
            field_definition=self.d_price, content_type=self.advert_ct, object_id=advert.pk, value="900"
        )
        response = self.client.get(reverse("adverts_edit", kwargs={"pk": advert.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertIn('value="900"', response.content.decode())

    def test_detail_page_shows_only_filled_in_custom_fields(self):
        advert = Advert.objects.create(
            type=self.advert_types[0],
            header="published advert",
            body="body",
            published=True,
            created_by_user=self.u_peter,
        )
        response = self.client.get(reverse("adverts_detail", kwargs={"pk": advert.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("Cena", response.content.decode())

        CustomFieldValue.objects.create(
            field_definition=self.d_price, content_type=self.advert_ct, object_id=advert.pk, value="900"
        )
        response = self.client.get(reverse("adverts_detail", kwargs={"pk": advert.pk}))
        content = response.content.decode()
        self.assertIn("Cena", content)
        self.assertIn("900", content)


class CustomFieldValueOnFaultEditTest(UserDataMixin, TestCase):
    def setUp(self):
        self.fault_ct = ContentType.objects.get_for_model(FaultReport)
        self.d_severity = CustomFieldDefinition.objects.create(
            content_type=self.fault_ct,
            name="Priorita",
            field_type=CustomFieldDefinition.TYPE_ENUM,
            enum_options="Nízká,Střední,Vysoká",
        )
        self.fault = FaultReportFactory(created_by_user=self.u_jiri, closed=False)
        self.client.login(username="jiri", password=self.u_jiri_password)

    def test_edit_page_renders_with_custom_field(self):
        response = self.client.get(reverse("faults_fault_edit", kwargs={"pk": self.fault.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertIn(f'name="customfield_{self.d_severity.pk}"', response.content.decode())

    def test_save_custom_field_on_fault(self):
        response = self.client.post(
            reverse("faults_fault_update"),
            {
                "pk": self.fault.pk,
                "subject": self.fault.subject,
                "description": self.fault.description,
                "created_by_user": self.fault.created_by_user.pk,
                f"customfield_{self.d_severity.pk}": "Vysoká",
            },
        )
        self.assertEqual(response.status_code, 302)
        value = CustomFieldValue.objects.get(field_definition=self.d_severity, object_id=self.fault.pk)
        self.assertEqual(value.value, "Vysoká")


class CustomFieldFormRenderingSmokeTest(BuildingUnitDataMixin, TestCase):
    """Every edit page wired for custom fields must render (create and edit mode) without a template error."""

    def setUp(self):
        self.client.login(username="jarda", password=self.u_jarda_password)

    def test_custom_field_create_form_renders(self):
        response = self.client.get(reverse("admin_custom_field_edit", kwargs={"pk": 0}))
        self.assertEqual(response.status_code, 200)

    def test_board_edit_renders_with_and_without_custom_field(self):
        board = Board.objects.create(company=self.company, order=1, member=self.u_jarda, position="Chairman")
        CustomFieldDefinition.objects.create(
            content_type=ContentType.objects.get_for_model(Board),
            name="Volební období",
            field_type=CustomFieldDefinition.TYPE_TEXT,
        )
        response = self.client.get(reverse("admin_board_edit", kwargs={"pk": 0}))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse("admin_board_edit", kwargs={"pk": board.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertIn("Volební období", response.content.decode())

    def test_entrance_edit_renders_with_and_without_custom_field(self):
        CustomFieldDefinition.objects.create(
            content_type=ContentType.objects.get_for_model(BuildingEntrance),
            name="Počet klíčů",
            field_type=CustomFieldDefinition.TYPE_NUMBER,
        )
        response = self.client.get(reverse("admin_entrance_edit", kwargs={"pk": 0}))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse("admin_entrance_edit", kwargs={"pk": self.entrance.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertIn("Počet klíčů", response.content.decode())

    def test_building_unit_edit_renders_with_and_without_custom_field(self):
        CustomFieldDefinition.objects.create(
            content_type=ContentType.objects.get_for_model(BuildingUnit),
            name="Sklep",
            field_type=CustomFieldDefinition.TYPE_BOOLEAN,
        )
        response = self.client.get(reverse("admin_building_unit_edit", kwargs={"pk": 0}))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse("admin_building_unit_edit", kwargs={"pk": self.unit.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertIn("Sklep", response.content.decode())
