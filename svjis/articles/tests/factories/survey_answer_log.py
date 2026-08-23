import factory

from .survey import SurveyFactory
from .survey_option import SurveyOptionFactory
from .user import UserFactory
from ...models import SurveyAnswerLog


class SurveyAnswerLogFactory(factory.django.DjangoModelFactory):
    survey = factory.SubFactory(SurveyFactory)
    option = factory.SubFactory(SurveyOptionFactory)
    user = factory.SubFactory(UserFactory)

    class Meta:
        model = SurveyAnswerLog
