import factory
from django.core.files.base import ContentFile

from .user import UserFactory
from .project import ProjectFactory
from ...models import ProjectAsset


class ProjectAssetFactory(factory.django.DjangoModelFactory):
    description = factory.Faker('sentence', nb_words=3)
    file = factory.LazyFunction(lambda: ContentFile(b'test', name='test.txt'))
    project = factory.SubFactory(ProjectFactory)
    created_by_user = factory.SubFactory(UserFactory)

    class Meta:
        model = ProjectAsset
