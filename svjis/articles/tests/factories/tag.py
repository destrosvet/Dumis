import factory

from ...models import Tag


class TagFactory(factory.django.DjangoModelFactory):
    name = factory.Sequence(lambda n: f'tag-{n}')
    color = 'slate'

    class Meta:
        model = Tag
