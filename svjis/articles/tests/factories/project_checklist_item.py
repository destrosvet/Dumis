import factory

from .project import ProjectFactory
from ...models import ProjectChecklistItem


class ProjectChecklistItemFactory(factory.django.DjangoModelFactory):
    project = factory.SubFactory(ProjectFactory)
    text = factory.Faker('sentence', nb_words=3)
    is_checked = False

    class Meta:
        model = ProjectChecklistItem
