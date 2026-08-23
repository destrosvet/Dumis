from datetime import date, timedelta

import factory

from .user import UserFactory
from ...models import Survey


class SurveyFactory(factory.django.DjangoModelFactory):
    author = factory.SubFactory(UserFactory)
    description = factory.Faker('text')
    starting_date = factory.LazyFunction(lambda: date.today() - timedelta(days=5))
    ending_date = factory.LazyFunction(lambda: date.today() + timedelta(days=5))
    published = True

    class Meta:
        model = Survey
