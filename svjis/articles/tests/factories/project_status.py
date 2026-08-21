import factory

from ...models import ProjectStatus


class ProjectStatusFactory(factory.django.DjangoModelFactory):
    name = factory.Faker('word')
    order = factory.Sequence(lambda n: n)
    is_closed = False
    color = 'slate'

    class Meta:
        model = ProjectStatus
