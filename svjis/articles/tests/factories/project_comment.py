import factory

from .user import UserFactory
from .project import ProjectFactory
from ...models import ProjectComment


class ProjectCommentFactory(factory.django.DjangoModelFactory):
    project = factory.SubFactory(ProjectFactory)
    author = factory.SubFactory(UserFactory)
    body = factory.Faker('sentence')

    class Meta:
        model = ProjectComment
