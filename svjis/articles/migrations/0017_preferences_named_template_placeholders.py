# Generated manually - convert positional {} placeholders in mail template
# preferences to named placeholders so admins can see what each variable means.

import re

from django.db import migrations


TEMPLATE_VAR_ORDER = {
    'mail.template.lost.password': ['message'],
    'mail.template.article.notification': ['link'],
    'mail.template.comment.notification': ['author', 'link', 'comment'],
    'mail.template.fault.notification': ['author', 'link', 'description'],
    'mail.template.fault.comment.notification': ['author', 'link', 'comment'],
    'mail.template.fault.assigned': ['assignor', 'link', 'description'],
    'mail.template.fault.closed': ['user', 'link', 'description'],
    'mail.template.fault.reopened': ['user', 'link', 'description'],
}


def convert_to_named(value, names):
    names = list(names)

    def repl(_match):
        if names:
            return '{' + names.pop(0) + '}'
        return _match.group(0)

    return re.sub(r'\{\}', repl, value)


def convert_back_to_positional(value, names):
    for name in names:
        value = value.replace('{' + name + '}', '{}', 1)
    return value


def migrate_forward(apps, schema_editor):
    Preferences = apps.get_model('articles', 'Preferences')
    for key, names in TEMPLATE_VAR_ORDER.items():
        for pref in Preferences.objects.filter(key=key):
            if '{}' in pref.value:
                pref.value = convert_to_named(pref.value, names)
                pref.save()


def migrate_backward(apps, schema_editor):
    Preferences = apps.get_model('articles', 'Preferences')
    for key, names in TEMPLATE_VAR_ORDER.items():
        for pref in Preferences.objects.filter(key=key):
            new_value = convert_back_to_positional(pref.value, names)
            if new_value != pref.value:
                pref.value = new_value
                pref.save()


class Migration(migrations.Migration):

    dependencies = [
        ('articles', '0016_remove_buildingunit_owners_buildingunituser_and_more'),
    ]

    operations = [
        migrations.RunPython(migrate_forward, migrate_backward),
    ]