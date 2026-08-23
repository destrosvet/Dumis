import factory

from ...models import UsefulLink


class UsefulLinkFactory(factory.django.DjangoModelFactory):
    header = factory.Faker('sentence', nb_words=3)
    link = factory.Faker('url')
    order = factory.Sequence(lambda n: n)
    published = factory.Faker('boolean')

    class Meta:
        model = UsefulLink
