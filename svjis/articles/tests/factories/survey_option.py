import factory

from .survey import SurveyFactory
from ...models import SurveyOption


class SurveyOptionFactory(factory.django.DjangoModelFactory):
    survey = factory.SubFactory(SurveyFactory)
    description = factory.Faker('word')

    class Meta:
        model = SurveyOption
