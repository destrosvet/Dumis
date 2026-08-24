"""Shared creation logic for building units, owner users and unit-owner
assignments - used by both the cadastre PDF import (`views_admin.py`) and the
admin REST API (`api/views.py`), so the two surfaces stay in sync.
"""

from django.contrib.auth.models import Group, User
from django.db.models import QuerySet
from django.utils.text import slugify

from .. import models


def get_or_create_unit_type(description: str) -> models.BuildingUnitType:
    obj, _created = models.BuildingUnitType.objects.get_or_create(description=description)
    return obj


def create_or_update_building_unit(
    *,
    building: models.Building,
    type_description: str,
    registration_id: str,
    description: str,
    numerator: int,
    denominator: int,
    entrance: models.BuildingEntrance | None = None,
) -> tuple[models.BuildingUnit, bool]:
    unit_type = get_or_create_unit_type(type_description)
    return models.BuildingUnit.objects.update_or_create(
        building=building,
        registration_id=registration_id,
        defaults={
            'type': unit_type,
            'description': description,
            'numerator': numerator,
            'denominator': denominator,
            'entrance': entrance,
        },
    )


def find_matching_users(name_guess: str) -> QuerySet[User]:
    name_guess = name_guess.strip()
    if not name_guess:
        return User.objects.none()
    parts = name_guess.split()
    q = User.objects.filter(is_active=True)
    if len(parts) >= 2:
        return q.filter(first_name__iexact=parts[0], last_name__iexact=parts[-1]) | q.filter(
            first_name__iexact=parts[-1], last_name__iexact=parts[0]
        )
    return q.filter(last_name__iexact=name_guess) | q.filter(first_name__iexact=name_guess)


def _unique_username(first_name: str, last_name: str) -> str:
    base = slugify(f'{first_name}.{last_name}'.strip('.')) or 'user'
    username = base
    suffix = 1
    while User.objects.filter(username=username).exists():
        suffix += 1
        username = f'{base}{suffix}'
    return username


def create_owner_user(*, first_name: str, last_name: str, address_text: str = '') -> User:
    username = _unique_username(first_name, last_name)
    user = User.objects.create(username=username, first_name=first_name, last_name=last_name, is_active=True)
    models.UserProfile.objects.create(user=user, address=address_text[:50])

    owner_group = Group.objects.filter(name='Vlastník').first()
    if owner_group is not None:
        user.groups.add(owner_group)

    return user


def assign_owner(
    *,
    building_unit: models.BuildingUnit,
    user: User,
    role: str = models.BuildingUnitUser.ROLE_OWNER,
    share_numerator: int | None = None,
    share_denominator: int | None = None,
) -> models.BuildingUnitUser:
    obj, _created = models.BuildingUnitUser.objects.update_or_create(
        building_unit=building_unit,
        user=user,
        role=role,
        defaults={'share_numerator': share_numerator, 'share_denominator': share_denominator},
    )
    return obj
