import base64
from datetime import timedelta

from django.contrib.auth.models import Group, User
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from articles.models import (
    Advert,
    AdvertType,
    Article,
    ArticleComment,
    ArticleMenu,
    Board,
    Building,
    BuildingEntrance,
    BuildingUnit,
    BuildingUnitType,
    BuildingUnitUser,
    Company,
    FaultComment,
    FaultReport,
    FaultReportLog,
    News,
    Survey,
    SurveyAnswerLog,
    SurveyOption,
    UsefulLink,
    UserProfile,
)

OWNERS = [
    # username, first_name, last_name, email, phone
    ('novakova', 'Jana', 'Nováková', 'jana.novakova@example.com', '+420601111222'),
    ('svoboda', 'Petr', 'Svoboda', 'petr.svoboda@example.com', '+420601222333'),
    ('dvorak', 'Tomáš', 'Dvořák', 'tomas.dvorak@example.com', '+420601333444'),
    ('cerna', 'Lucie', 'Černá', 'lucie.cerna@example.com', '+420601444555'),
    ('prochazka', 'Martin', 'Procházka', 'martin.prochazka@example.com', '+420601555666'),
    ('kucerova', 'Eva', 'Kučerová', 'eva.kucerova@example.com', '+420601666777'),
]

DEMO_PASSWORD = 'owner123'


def placeholder_image(label, bg='#0f766e', fg='#f0fdfa'):
    """Self-contained SVG placeholder photo (data URI) - no external assets needed."""
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="800" height="450" viewBox="0 0 800 450">
<rect width="800" height="450" fill="{bg}"/>
<g fill="none" stroke="{fg}" stroke-width="10" stroke-linecap="round" stroke-linejoin="round" opacity="0.85">
<rect x="300" y="155" width="200" height="140" rx="12"/>
<circle cx="345" cy="200" r="16"/>
<path d="M300 265 L365 220 L410 250 L460 210 L500 240"/>
</g>
<text x="400" y="345" font-family="Arial, sans-serif" font-size="26" fill="{fg}" text-anchor="middle">{label}</text>
</svg>'''
    encoded = base64.b64encode(svg.encode('utf-8')).decode('ascii')
    return f'data:image/svg+xml;base64,{encoded}'


def placeholder_cover_svg(label, bg='#0f766e', fg='#f0fdfa'):
    """Self-contained square SVG placeholder cover photo - no external assets needed."""
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="400" height="400" viewBox="0 0 400 400">
<rect width="400" height="400" fill="{bg}"/>
<g fill="none" stroke="{fg}" stroke-width="8" stroke-linecap="round" stroke-linejoin="round" opacity="0.85">
<rect x="120" y="140" width="160" height="120" rx="10"/>
<circle cx="160" cy="180" r="14"/>
<path d="M120 245 L175 205 L215 230 L260 195 L280 220"/>
</g>
<text x="200" y="305" font-family="Arial, sans-serif" font-size="20" fill="{fg}" text-anchor="middle">{label}</text>
</svg>'''
    return svg.encode('utf-8')


class Command(BaseCommand):
    help = 'Populate the database with sample content for local development (owners, articles, faults, adverts, ...)'

    def handle(self, *args, **options):
        if User.objects.filter(username=OWNERS[0][0]).exists():
            self.stdout.write('Demo data already exists, skipping...')
            return

        with transaction.atomic():
            owners = self._create_owners()
            company = self._create_company()
            building = self._create_building()
            entrances = self._create_entrances(building)
            self._create_units(building, entrances, owners)
            self._create_board(company, owners)
            self._create_articles(owners)
            self._create_news()
            self._create_useful_links()
            self._create_survey(owners)
            self._create_faults(owners, entrances)
            self._create_adverts(owners)

        self.stdout.write(self.style.SUCCESS('Demo data created.'))

    def _create_owners(self):
        owner_group = Group.objects.get(name='Vlastník')
        users = []
        for username, first_name, last_name, email, phone in OWNERS:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=DEMO_PASSWORD,
                first_name=first_name,
                last_name=last_name,
            )
            user.groups.add(owner_group)
            UserProfile.objects.create(
                user=user,
                address='Sluneční 1234/5',
                city='Praha 4',
                post_code='140 00',
                country='Česká republika',
                phone=phone,
                show_in_phonelist=True,
            )
            users.append(user)
        return users

    def _create_company(self):
        # Company is a pk=1 singleton, other views use get_or_create(pk=1) and may have
        # already created a blank row - fill it in rather than creating a second one.
        company, _created = Company.objects.update_or_create(
            pk=1,
            defaults=dict(
                name='SVJ Sluneční 1234',
                address='Sluneční 1234/5',
                city='Praha 4',
                post_code='140 00',
                phone='+420601000111',
                email='vybor@svj-slunecni.cz',
                registration_no='12345678',
                internet_domain='svj-slunecni.cz',
            ),
        )
        return company

    def _create_building(self):
        return Building.objects.create(
            address='Sluneční 1234/5',
            city='Praha 4',
            post_code='140 00',
            land_registry_no='1234',
        )

    def _create_entrances(self, building):
        return [
            BuildingEntrance.objects.create(building=building, description='Vchod A', address='Sluneční 1234'),
            BuildingEntrance.objects.create(building=building, description='Vchod B', address='Sluneční 1235'),
        ]

    def _create_units(self, building, entrances, owners):
        flat_type = BuildingUnitType.objects.get(description='Byt')
        cellar_type = BuildingUnitType.objects.get(description='Sklep')
        garage_type = BuildingUnitType.objects.get(description='Garáž')

        units = [
            ('1234/1', 'Byt 1.1', flat_type, entrances[0], 520, [owners[0]]),
            ('1234/2', 'Byt 1.2', flat_type, entrances[0], 480, [owners[1]]),
            ('1234/3', 'Byt 2.1', flat_type, entrances[0], 610, [owners[2]]),
            ('1235/1', 'Byt 1.3', flat_type, entrances[1], 495, [owners[3]]),
            ('1235/2', 'Byt 2.2', flat_type, entrances[1], 530, [owners[4], owners[5]]),
            ('1234/S1', 'Sklep 1', cellar_type, entrances[0], 15, [owners[0]]),
            ('1234/G1', 'Garáž 1', garage_type, entrances[0], 40, [owners[2]]),
        ]
        for registration_id, description, unit_type, entrance, numerator, unit_owners in units:
            unit = BuildingUnit.objects.create(
                building=building,
                type=unit_type,
                entrance=entrance,
                registration_id=registration_id,
                description=description,
                numerator=numerator,
                denominator=10000,
            )
            for owner in unit_owners:
                BuildingUnitUser.objects.create(building_unit=unit, user=owner, role=BuildingUnitUser.ROLE_OWNER)

        # Demonstrate tenants: the first flat is rented out by its owner
        rented_flat = BuildingUnit.objects.get(registration_id='1234/1')
        BuildingUnitUser.objects.create(
            building_unit=rented_flat, user=owners[5], role=BuildingUnitUser.ROLE_TENANT
        )

    def _create_board(self, company, owners):
        admin = User.objects.get(username='admin')
        Board.objects.create(company=company, order=1, member=admin, position='Předseda výboru')
        Board.objects.create(company=company, order=2, member=owners[1], position='Místopředseda')
        Board.objects.create(company=company, order=3, member=owners[2], position='Člen výboru')

    def _create_articles(self, owners):
        admin = User.objects.get(username='admin')
        menus = {menu.description: menu for menu in ArticleMenu.objects.all()}
        now = timezone.now()

        articles_data = [
            (
                'Vývěska',
                'Odstávka vody 15. 7. 2026',
                'Ve dnech 15. 7. 2026 od 8:00 do 14:00 proběhne plánovaná odstávka vody kvůli opravě stoupačky.',
                'Vážení vlastníci,\n\ndne 15. 7. 2026 bude v celém domě přerušena dodávka vody z důvodu opravy '
                'stoupačky ve vchodu A. Odstávka potrvá přibližně od 8:00 do 14:00.\n\nDěkujeme za pochopení.\nVýbor SVJ',
                True,
            ),
            (
                'Vývěska',
                'Přivítání nových sousedů',
                'Rádi bychom přivítali nové vlastníky bytu 2.2, kteří se k nám nedávno přistěhovali.',
                'Vítáme nové sousedy v bytě 2.2 a přejeme jim, ať se jim u nás dobře bydlí!\n\n'
                f'<img class="article-img" src="{placeholder_image("Vchod B")}" alt="Vchod B">',
                True,
            ),
            (
                'Dotazy a návody',
                'Jak nahlásit závadu',
                'Stručný návod, jak nahlásit závadu ve společných prostorách přes tento web.',
                'Závadu nahlásíte v sekci "Závady" tlačítkem "Nahlásit závadu". Vyplňte předmět, popis a případně '
                'přiložte fotografii. O průběhu řešení budete informováni e-mailem.',
                False,
            ),
            (
                'Dotazy a návody',
                'Návod na třídění odpadu',
                'Kde najdete kontejnery na tříděný odpad a jak s nimi zacházet.',
                'Kontejnery na papír, plast a sklo najdete na dvoře u vchodu B. Bioodpad patří do hnědého '
                'kontejneru u vchodu A.',
                False,
            ),
            (
                'Smlouvy',
                'Smlouva o dodávce elektřiny',
                'Informace o nově uzavřené smlouvě na dodávku elektřiny pro společné prostory.',
                'Výbor uzavřel novou smlouvu o dodávce elektřiny pro společné prostory domu. Smlouva je k '
                'nahlédnutí u předsedy výboru.',
                False,
            ),
            (
                'Zápisy',
                'Zápis ze shromáždění vlastníků 1. 3. 2026',
                'Zápis z pravidelného jarního shromáždění vlastníků jednotek.',
                'Shromáždění schválilo roční vyúčtování za rok 2025 a rozpočet na rok 2026. Dále byla '
                'projednána oprava fasády plánovaná na podzim 2026.\n\n'
                f'<img class="article-img" src="{placeholder_image("Shromáždění vlastníků")}" alt="Shromáždění vlastníků">',
                True,
            ),
        ]

        cover_palette = ['#0f766e', '#0d9488', '#115e59', '#0891b2', '#134e4a', '#0e7490']

        created_articles = []
        for i, (menu_name, header, perex, body, allow_comments) in enumerate(articles_data):
            article = Article.objects.create(
                header=header,
                author=admin,
                created_date=now,
                published=True,
                perex=perex,
                body=body,
                menu=menus[menu_name],
                allow_comments=allow_comments,
                visible_for_all=True,
            )
            article.cover_image.save(
                f'{article.slug}-cover.svg',
                ContentFile(placeholder_cover_svg(menu_name, bg=cover_palette[i % len(cover_palette)])),
                save=True,
            )
            created_articles.append(article)

        ArticleComment.objects.create(
            article=created_articles[0], author=owners[0], body='Díky za informaci, budeme počítat s omezením.'
        )
        ArticleComment.objects.create(
            article=created_articles[0], author=owners[1], body='Bude voda alespoň v přízemí?'
        )

    def _create_news(self):
        admin = User.objects.get(username='admin')
        now = timezone.now()
        News.objects.create(
            author=admin,
            created_date=now,
            published=True,
            body='Byl schválen rozpočet SVJ na rok 2026.',
        )
        News.objects.create(
            author=admin,
            created_date=now - timedelta(days=3),
            published=True,
            body='Na jarním shromáždění byli zvoleni noví členové výboru.',
        )

    def _create_useful_links(self):
        UsefulLink.objects.create(header='Katastr nemovitostí', link='https://nahlizenidokn.cuzk.cz', order=1, published=True)
        UsefulLink.objects.create(header='Czech POINT', link='https://www.czechpoint.cz', order=2, published=True)

    def _create_survey(self, owners):
        admin = User.objects.get(username='admin')
        today = timezone.now().date()
        survey = Survey.objects.create(
            author=admin,
            description='Souhlasíte s instalací nabíjecích stanic pro elektromobily na parkovišti?',
            starting_date=today - timedelta(days=10),
            ending_date=today + timedelta(days=20),
            published=True,
        )
        opt_yes = SurveyOption.objects.create(survey=survey, description='Ano')
        opt_no = SurveyOption.objects.create(survey=survey, description='Ne')
        SurveyOption.objects.create(survey=survey, description='Je mi to jedno')

        SurveyAnswerLog.objects.create(survey=survey, option=opt_yes, user=owners[0])
        SurveyAnswerLog.objects.create(survey=survey, option=opt_yes, user=owners[1])
        SurveyAnswerLog.objects.create(survey=survey, option=opt_no, user=owners[2])

    def _create_faults(self, owners, entrances):
        admin = User.objects.get(username='admin')
        now = timezone.now()

        faults_data = [
            ('Nefunguje osvětlení ve sklepě', 'Osvětlení ve sklepním prostoru u vchodu A nesvítí.', entrances[0], owners[0], None, False),
            ('Prasklé potrubí v suterénu', 'V suterénu vchodu A praskla voda, je potřeba urychleně opravit.', entrances[0], owners[2], admin, True),
            ('Rozbité zvonění u vchodu B', 'Zvonek u vchodu B nefunguje, je potřeba vyměnit tlačítko.', entrances[1], owners[3], None, False),
            ('Nefunguje výtah', 'Výtah ve vchodu B hlásí poruchu a nejezdí.', entrances[1], owners[4], admin, True),
            ('Poškozená fasáda po bouřce', 'Po bouřce odpadl kus omítky z fasády u vchodu A.', entrances[0], owners[1], None, False),
        ]

        for subject, description, entrance, reporter, resolver, closed in faults_data:
            fault = FaultReport.objects.create(
                subject=subject,
                description=description,
                created_date=now,
                created_by_user=reporter,
                assigned_to_user=resolver,
                closed=closed,
                entrance=entrance,
            )
            FaultReportLog.objects.create(
                fault_report=fault, user=reporter, resolver=resolver, type=FaultReportLog.TYPE_CREATED
            )
            if resolver is not None:
                FaultReportLog.objects.create(
                    fault_report=fault, user=admin, resolver=resolver, type=FaultReportLog.TYPE_ASSIGNED
                )
                FaultComment.objects.create(
                    fault_report=fault, author=resolver, body='Beru na vědomí, řeším.'
                )
            if closed:
                FaultReportLog.objects.create(
                    fault_report=fault, user=resolver, resolver=resolver, type=FaultReportLog.TYPE_CLOSED
                )
                FaultComment.objects.create(
                    fault_report=fault, author=resolver, body='Vyřešeno, opraveno.'
                )

    def _create_adverts(self, owners):
        prodam = AdvertType.objects.get(description='Prodám')
        koupim = AdvertType.objects.get(description='Koupím')
        ostatni = AdvertType.objects.get(description='Ostatní')

        Advert.objects.create(
            type=prodam,
            header='Prodám dětské kolo 16"',
            body='Prodám zachovalé dětské kolo, vhodné pro věk 4-6 let. Cena 800 Kč.',
            created_by_user=owners[0],
            phone=owners[0].userprofile.phone,
            email=owners[0].email,
        )
        Advert.objects.create(
            type=koupim,
            header='Hledám hlídání psa o víkendech',
            body='Hledám souseda, který by o víkendech pohlídal našeho psa. Odměna zajištěna.',
            created_by_user=owners[3],
            phone=owners[3].userprofile.phone,
            email=owners[3].email,
        )
        Advert.objects.create(
            type=ostatni,
            header='Nabízím hlídání dětí',
            body='Nabízím příležitostné hlídání dětí v odpoledních hodinách, mám pedagogické vzdělání.',
            created_by_user=owners[5],
            phone=owners[5].userprofile.phone,
            email=owners[5].email,
        )
