import factory
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType

from ...models import CustomFieldDefinition, CustomFieldValue


class CustomFieldDefinitionFactory(factory.django.DjangoModelFactory):
    content_type = factory.LazyFunction(lambda: ContentType.objects.get_for_model(User))
    name = factory.Faker("word")
    field_type = CustomFieldDefinition.TYPE_TEXT

    class Meta:
        model = CustomFieldDefinition


class CustomFieldValueFactory(factory.django.DjangoModelFactory):
    field_definition = factory.SubFactory(CustomFieldDefinitionFactory)
    content_type = factory.LazyAttribute(lambda o: o.field_definition.content_type)
    object_id = factory.Faker("random_int", min=1, max=1000)
    value = factory.Faker("word")

    class Meta:
        model = CustomFieldValue
