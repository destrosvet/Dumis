import factory

from .user import UserFactory
from .project_status import ProjectStatusFactory
from ...models import Project


class ProjectFactory(factory.django.DjangoModelFactory):
    subject = factory.Faker('sentence', nb_words=3)
    slug = factory.Faker('slug')
    description = factory.Faker('text')
    created_date = factory.Faker('date_time')
    created_by_user = factory.SubFactory(UserFactory)
    assigned_to_user = factory.SubFactory(UserFactory)
    status = factory.SubFactory(ProjectStatusFactory)

    class Meta:
        model = Project
