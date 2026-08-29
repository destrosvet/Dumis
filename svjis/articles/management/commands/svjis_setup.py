import getpass
import sys

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group, Permission
from django.db import transaction
from articles import models

from articles.models import ArticleMenu, Preferences, BuildingUnitType, AdvertType, ProjectStatus


def create_groups():
    names = [
        {
            'name': 'Administrátor',
            'perms': [
                # Articles
                'svjis_add_article_comment',
                'svjis_answer_survey',
                # Contact
                'svjis_view_phonelist',
                # Personal settings
                'svjis_view_personal_menu',
                # Redaction
                'svjis_view_redaction_menu',
                'svjis_edit_article',
                'svjis_edit_article_news',
                'svjis_edit_useful_link',
                'svjis_edit_survey',
                'svjis_edit_article_menu',
                # Administration
                'svjis_view_admin_menu',
                'svjis_edit_admin_company',
                'svjis_edit_admin_building',
                'svjis_edit_admin_users',
                'svjis_edit_admin_groups',
                'svjis_edit_admin_preferences',
                # Faults
                'svjis_view_fault_menu',
                'svjis_fault_reporter',
                'svjis_fault_resolver',
                'svjis_add_fault_comment',
                # Adverts
                'svjis_view_adverts_menu',
                'svjis_add_advert',
                # Projects
                'svjis_view_project_menu',
                'svjis_add_project',
                'svjis_manage_projects',
                'svjis_add_project_comment',
                # Administration
                'svjis_edit_admin_project_statuses',
                'svjis_edit_admin_tags',
            ],
        },
        {
            'name': 'Vlastník',
            'perms': [
                # Articles
                'svjis_add_article_comment',
                'svjis_answer_survey',
                # Contact
                'svjis_view_phonelist',
                # Personal settings
                'svjis_view_personal_menu',
                # Faults
                'svjis_view_fault_menu',
                'svjis_fault_reporter',
                'svjis_add_fault_comment',
                # Adverts
                'svjis_view_adverts_menu',
                'svjis_add_advert',
                # Projects
                'svjis_view_project_menu',
                'svjis_add_project',
                'svjis_add_project_comment',
            ],
        },
        {
            'name': 'Nájemník',
            'perms': [
                # Articles
                'svjis_add_article_comment',
                # Contact
                'svjis_view_phonelist',
                # Personal settings
                'svjis_view_personal_menu',
                # Faults
                'svjis_view_fault_menu',
                'svjis_fault_reporter',
                'svjis_add_fault_comment',
                # Adverts
                'svjis_view_adverts_menu',
                'svjis_add_advert',
                # Projects
                'svjis_view_project_menu',
                'svjis_add_project',
                'svjis_add_project_comment',
            ],
        },
        {
            'name': 'Člen výboru',
            'perms': [
                # Articles
                'svjis_add_article_comment',
                # Contact
                'svjis_view_phonelist',
                # Personal settings
                'svjis_view_personal_menu',
                # Projects
                'svjis_view_project_menu',
                'svjis_add_project',
                'svjis_manage_projects',
                'svjis_add_project_comment',
            ],
        },
        {
            'name': 'Dodavatel',
            'perms': [
                # Articles
                'svjis_add_article_comment',
                # Personal settings
                'svjis_view_personal_menu',
            ],
        },
        {
            'name': 'Redaktor',
            'perms': [
                # Articles
                'svjis_add_article_comment',
                # Personal settings
                'svjis_view_personal_menu',
                # Redaction
                'svjis_view_redaction_menu',
                'svjis_edit_article',
                'svjis_edit_article_news',
                'svjis_edit_useful_link',
                'svjis_edit_survey',
                'svjis_edit_article_menu',
            ],
        },
        {
            'name': 'Řešitel',
            'perms': [
                # Personal settings
                'svjis_view_personal_menu',
                # Faults
                'svjis_view_fault_menu',
                'svjis_fault_reporter',
                'svjis_fault_resolver',
                'svjis_add_fault_comment',
                # Projects
                'svjis_view_project_menu',
                'svjis_add_project_comment',
            ],
        },
    ]

    print("Creating groups...")
    for g in names:
        gobj = Group(name=g['name'])
        gobj.save()
        for p in g['perms']:
            try:
                pobj = Permission.objects.get(content_type__app_label='articles', codename=p)
                gobj.permissions.add(pobj)
            except Permission.DoesNotExist:
                print(f"Permission {p} doesnt exist")
    print("Done")


def create_admin_user(password: str):
    print("Creating admin user...")
    u = User.objects.create_superuser(username='admin', email='admin@test.cz', password=password, last_name='admin')
    models.UserProfile.objects.create(user=u)
    g = Group.objects.get(name='Administrátor')
    u.groups.add(g)
    print("Done")


def create_article_menu():
    print("Creating article menu...")
    menu = ['Vývěska', 'Dotazy a návody', 'Smlouvy', 'Zápisy']
    for m in menu:
        ArticleMenu.objects.create(description=m)
    print("Done")


def create_preferences():
    print("Creating preferences...")
    preferences = [
        {
            'key': 'mail.template.lost.password',
            'value': '<html><body>Dobrý den,<br>Vaše přihlašovací údaje jsou:<br><br>{message}<br>\
            Heslo si můžete změnit v menu <b>Osobní nastavení - Změna hesla</b><br><br>Web SVJ</body></html>',
        },
        {
            'key': 'mail.template.article.notification',
            'value': 'Dobrý den,<br><br>rádi bychom Vás upozornili na následující článek na stránkách SVJ.<br>\
            <br>{link}<br><br>S pozdravem,<br>Výbor SVJ',
        },
        {
            'key': 'mail.template.comment.notification',
            'value': 'Uživatel {author} přidal nový komentář k článku {link}: <br><br><br>{comment}',
        },
        {
            'key': 'mail.template.fault.notification',
            'value': 'Uživatel {author} vložil novou závadu {link}: <br><br><br>{description}',
        },
        {
            'key': 'mail.template.fault.comment.notification',
            'value': 'Uživatel {author} přidal nový komentář k závadě {link}: <br><br><br>{comment}',
        },
        {'key': 'mail.template.fault.assigned', 'value': 'Uživatel {assignor} vám přiřadil tiket {link}: <br><br><br>{description}'},
        {'key': 'mail.template.fault.closed', 'value': 'Uživatel {user} uzavřel tiket {link}: <br><br><br>{description}'},
        {'key': 'mail.template.fault.reopened', 'value': 'Uživatel {user} znovu otevřel tiket {link}: <br><br><br>{description}'},
        {
            'key': 'mail.template.project.notification',
            'value': 'Uživatel {author} založil nový projekt {link}: <br><br><br>{description}',
        },
        {
            'key': 'mail.template.project.comment.notification',
            'value': 'Uživatel {author} přidal nový komentář k projektu {link}: <br><br><br>{comment}',
        },
        {
            'key': 'mail.template.project.assigned',
            'value': 'Uživatel {assignor} vám přiřadil projekt {link}: <br><br><br>{description}',
        },
        {
            'key': 'mail.template.project.status.changed',
            'value': 'Uživatel {user} změnil stav projektu {link} z "{old_status}" na "{new_status}".',
        },
    ]
    for p in preferences:
        Preferences.objects.create(key=p['key'], value=p['value'])
    print("Done")


def create_building_unit_types():
    print("Creating building unit types...")
    types = ['Byt', 'Sklep', 'Komerční prostor', 'Garáž']
    for t in types:
        BuildingUnitType.objects.create(description=t)
    print("Done")


def create_advert_types():
    print("Creating advert types...")
    types = ['Koupím', 'Prodám', 'Ostatní']
    for t in types:
        AdvertType.objects.create(description=t)
    print("Done")


def create_project_statuses():
    print("Creating project statuses...")
    statuses = [
        ('Nový', 'slate', False),
        ('V realizaci', 'brand', False),
        ('Čeká na schválení', 'amber', False),
        ('Dokončeno', 'green', True),
        ('Zrušeno', 'red', True),
        ('Archiv', 'slate', True),
    ]
    for order, (name, color, is_closed) in enumerate(statuses, start=1):
        ProjectStatus.objects.create(name=name, order=order, color=color, is_closed=is_closed)
    print("Done")


class Command(BaseCommand):
    help = "Populate database with initial data"

    def add_arguments(self, parser):
        parser.add_argument("--password", type=str, help="Password for admin user")

    def handle(self, *args, **options):
        password = options["password"]
        if password is None and sys.stdin.isatty():
            while True:
                password = getpass.getpass("Enter password for admin user: ")
                password2 = getpass.getpass("Enter password again: ")
                if password == password2 and password != "":
                    break
                print("Passwords don't match.")

        with transaction.atomic():
            create_article_menu()
            create_advert_types()
            create_building_unit_types()
            create_project_statuses()
            create_groups()
            create_preferences()
            create_admin_user(password=password)
