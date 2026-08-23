import factory

from .user import UserFactory
from ...models import News


class NewsFactory(factory.django.DjangoModelFactory):
    author = factory.SubFactory(UserFactory)
    published = factory.Faker('boolean')
    body = factory.Faker('text')

    class Meta:
        model = News
