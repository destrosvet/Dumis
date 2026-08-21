import os

from . import managers
from .model_utils import unique_slugify, get_asset_icon, get_age_in_minutes
from datetime import date
from django.db import models
from django.conf import settings
from django.contrib.auth.models import User, Group
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db.models import Count
from django.utils.translation import gettext_lazy as _
from .permissions import (
    svjis_answer_survey,
    svjis_fault_reporter,
    svjis_fault_resolver,
    svjis_view_project_menu,
    svjis_manage_projects,
)


COMMENT_IS_EDITABLE_MINUTES = getattr(settings, "SVJIS_COMMENT_IS_EDITABLE_MINUTES", 10)
MEDIA_ADVERT_ASSETS_DIR = 'inzerce'  # not "adverts"/"ads" - that gets blocked by ad blockers
MEDIA_ARTICLE_ASSETS_DIR = 'articles'
MEDIA_COMPANY_ASSETS_DIR = 'company'
MEDIA_FAULT_ASSETS_DIR = 'faults'
MEDIA_PROJECT_ASSETS_DIR = 'projects'

# Shared badge color palette (project statuses, tags) - maps 1:1 to the
# .badge--* CSS classes already defined in styles_v3.css.
BADGE_COLOR_CHOICES = (
    ('slate', _("Grey")),
    ('brand', _("Teal")),
    ('green', _("Green")),
    ('amber', _("Amber")),
    ('red', _("Red")),
)


# Article / Redaction
#####################


def article_cover_directory_path(instance, filename):
    # Lives under a separate "cover/" segment so it doesn't collide with the
    # access-controlled ArticleAsset route (media/articles/<slug>/<filename>).
    return f'{MEDIA_ARTICLE_ASSETS_DIR}/{instance.slug}/cover/{filename}'


class Article(models.Model):
    header = models.CharField(_("Header"), max_length=255)
    slug = models.CharField(max_length=50, unique=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    created_date = models.DateTimeField(auto_now_add=True)
    published_date = models.DateField(_("Publish date"), default=date.today)
    published = models.BooleanField(_("Published"), default=False)
    perex = models.TextField(_("Perex"))
    body = models.TextField(_("Body"), blank=True)
    cover_image = models.FileField(_("Cover image"), upload_to=article_cover_directory_path, null=True, blank=True)
    menu = models.ForeignKey("ArticleMenu", on_delete=models.CASCADE, null=False, blank=False)
    allow_comments = models.BooleanField(_("Allow comments"), default=False)
    watching_users = models.ManyToManyField(User, related_name='watching_article_set')
    visible_for_all = models.BooleanField(_("Visible for all"), default=False)
    visible_for_group = models.ManyToManyField(Group)

    def __str__(self):
        return f"Article: {self.header}"

    @property
    def assets(self):
        return self.articleasset_set.all()

    @property
    def comments(self):
        return self.articlecomment_set.all()

    class Meta:
        ordering = ['-published_date', '-id']
        permissions = (
            ("svjis_view_redaction_menu", _("Can view Redaction menu")),
            ("svjis_edit_article", _("Can edit Article")),
        )

    def save(self, **kwargs):
        if not self.slug:
            unique_slugify(self, self.header)
        super().save(**kwargs)

    def get_absolute_url(self):
        return f'/article/{self.slug}/'


class ArticleLog(models.Model):
    entry_time = models.DateTimeField(auto_now_add=True)
    article = models.ForeignKey(Article, on_delete=models.CASCADE, null=False, blank=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    user_agent = models.CharField(_("UserAgent"), max_length=1000, blank=True)

    def save(self, *args, **kwargs):
        if self.user_agent:
            self.user_agent = self.user_agent.strip()[:1000]
        super().save(*args, **kwargs)

    def __str__(self):
        return f"ArticleLog: {self.article} - {self.user}"


def article_directory_path(instance, filename):
    return f'{MEDIA_ARTICLE_ASSETS_DIR}/{instance.article.slug}/{filename}'


class ArticleAsset(models.Model):
    description = models.CharField(_("Description"), max_length=100)
    file = models.FileField(_("File"), upload_to=article_directory_path)
    article = models.ForeignKey(Article, on_delete=models.CASCADE, verbose_name=_("Article"))
    created_date = models.DateTimeField(auto_now_add=True)

    def delete(self, *args, **kwargs):
        if os.path.isfile(self.file.path):
            os.remove(self.file.path)
        super().delete(*args, **kwargs)

    def __str__(self):
        return f"ArticleAsset: {self.description}"

    @property
    def basename(self):
        return os.path.basename(self.file.path)

    @property
    def icon(self):
        return get_asset_icon(self.basename)

    class Meta:
        ordering = ['id']


class ArticleComment(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE, verbose_name=_("Article"))
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    created_date = models.DateTimeField(auto_now_add=True)
    body = models.TextField(_("Body"))

    def __str__(self):
        return f"ArticleComment: {self.article} - {self.body}"

    @property
    def is_editable(self) -> bool:
        age = get_age_in_minutes(self.created_date)
        if age is not None:
            return age <= COMMENT_IS_EDITABLE_MINUTES
        else:
            return False

    class Meta:
        ordering = ['id']
        permissions = (("svjis_add_article_comment", _("Can add Article comment")),)


class ArticleMenu(models.Model):
    description = models.CharField(_("Description"), max_length=100)
    hide = models.BooleanField(_("Hide"), default=False)
    parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return self.description

    @property
    def articles(self):
        return self.article_set.all()

    class Meta:
        ordering = ['description']
        permissions = (("svjis_edit_article_menu", _("Can edit Menu")),)


class News(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    created_date = models.DateTimeField(auto_now_add=True)
    published = models.BooleanField(_("Published"), default=False)
    body = models.TextField(_("Body"))

    def __str__(self):
        return f"News: {self.body}"

    class Meta:
        ordering = ['-id']
        permissions = (("svjis_edit_article_news", _("Can edit News")),)


class UsefulLink(models.Model):
    header = models.CharField(_("Header"), max_length=100)
    link = models.CharField(_("Link"), max_length=100)
    order = models.IntegerField(_("Order"))
    published = models.BooleanField(_("Published"), default=False)

    def __str__(self):
        return f"UsefulLink: {self.header}"

    class Meta:
        ordering = ['order']
        permissions = (("svjis_edit_useful_link", _("Can edit Useful Links")),)


class Survey(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    description = models.TextField(_("Description"))
    starting_date = models.DateField(_("Starting day"))
    ending_date = models.DateField(_("Ending day"))
    published = models.BooleanField(_("Published"), default=False)

    def __str__(self):
        return f"Survey: {self.description}"

    @property
    def options(self):
        return self.surveyoption_set.all()

    @property
    def is_open_for_voting(self):
        now = date.today()
        return self.published and self.starting_date <= now and self.ending_date >= now

    def is_user_open_for_voting(self, user):
        return self.answers.filter(user=user).count() == 0 and user.has_perm(svjis_answer_survey)

    @property
    def answers(self):
        return self.surveyanswerlog_set.order_by('time')

    class Meta:
        ordering = ['-id']
        permissions = (
            ("svjis_answer_survey", _("Can answer Survey")),
            ("svjis_edit_survey", _("Can edit Survey")),
        )


class SurveyOption(models.Model):
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE)
    description = models.CharField(_("Description"), max_length=250)

    def __str__(self):
        return f"SurveyOption: {self.description}"

    @property
    def is_winning(self):
        winning = self.survey.answers.values('option_id').annotate(total=Count('id')).order_by('-total').first()
        opt_total = self.total
        return False if winning is None else winning['total'] == opt_total

    @property
    def pct(self):
        total = self.survey.answers.count()
        opt_total = self.total
        return opt_total / total * 100 if total != 0 else 0

    @property
    def total(self):
        return self.survey.answers.filter(option=self).count()

    class Meta:
        ordering = ['id']


class SurveyAnswerLog(models.Model):
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE)
    option = models.ForeignKey(SurveyOption, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    time = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"SurveyAnswerLog: {self.option}"

    class Meta:
        ordering = ['id']


# Administration
#####################


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    salutation = models.CharField(_("Salutation"), max_length=30, blank=True)
    address = models.CharField(_("Address"), max_length=50, blank=True)
    city = models.CharField(_("City"), max_length=50, blank=True)
    post_code = models.CharField(_("Post code"), max_length=10, blank=True)
    country = models.CharField(_("Country"), max_length=50, blank=True)
    phone = models.CharField(_("Phone"), max_length=30, blank=True)
    show_in_phonelist = models.BooleanField(_("Show in phonelist"), default=False)
    internal_note = models.CharField(_("Internal note"), max_length=250, blank=True)

    def __str__(self):
        return f"UserProfile: {self.user.username}"

    class Meta:
        permissions = (
            ("svjis_view_admin_menu", _("Can view Administration menu")),
            ("svjis_edit_admin_users", _("Can edit Users")),
            ("svjis_edit_admin_groups", _("Can edit Groups")),
            ("svjis_view_personal_menu", _("Can view Personal settings menu")),
            ("svjis_view_phonelist", _("Can view Phonelist")),
        )


class MessageQueue(models.Model):
    email = models.CharField(_("E-Mail"), max_length=50, blank=False)
    subject = models.CharField(_("Subject"), max_length=150, blank=False)
    body = models.TextField(_("Body"))
    creation_time = models.DateTimeField(auto_now_add=True)
    sending_time = models.DateTimeField(null=True)
    status = models.SmallIntegerField(null=False)

    def __str__(self):
        return f"MessageQueue: {self.email} - {self.subject}"


class Preferences(models.Model):
    key = models.CharField(_("Key"), max_length=50, blank=False, null=False)
    value = models.CharField(_("Value"), max_length=1000, null=False)

    def __str__(self):
        return f"Preferences: {self.key}"

    class Meta:
        permissions = (("svjis_edit_admin_preferences", _("Can edit Preferences")),)


def company_directory_path(instance, filename):
    return f'{MEDIA_COMPANY_ASSETS_DIR}/{filename}'


class Company(models.Model):
    name = models.CharField(_("Name"), max_length=100, blank=True)
    address = models.CharField(_("Address"), max_length=50, blank=True)
    city = models.CharField(_("City"), max_length=50, blank=True)
    post_code = models.CharField(_("Post code"), max_length=10, blank=True)
    phone = models.CharField(_("Phone"), max_length=30, blank=True)
    email = models.CharField(_("E-Mail"), max_length=50, blank=True)
    registration_no = models.CharField(_("Registration No."), max_length=20, blank=True)
    vat_registration_no = models.CharField(_("VAT Registration No."), max_length=20, blank=True)
    internet_domain = models.CharField(_("Internet domain"), max_length=50, blank=True)
    header_picture = models.FileField(_("Header picture"), upload_to=company_directory_path, null=True, blank=True)

    @property
    def board(self):
        return self.board_set.all()

    def __str__(self):
        return f"Company: {self.name}"

    class Meta:
        permissions = (("svjis_edit_admin_company", _("Can edit Company")),)


class Building(models.Model):
    address = models.CharField(_("Address"), max_length=50, blank=True)
    city = models.CharField(_("City"), max_length=50, blank=True)
    post_code = models.CharField(_("Post code"), max_length=10, blank=True)
    land_registry_no = models.CharField(_("Land Registration No."), max_length=50, blank=True)

    def __str__(self):
        return f"Building: {self.address}"

    class Meta:
        permissions = (("svjis_edit_admin_building", _("Can edit Building")),)


class Board(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, verbose_name=_("Company"), null=False, blank=False)
    order = models.SmallIntegerField(_("Order"), blank=False)
    member = models.ForeignKey(User, on_delete=models.CASCADE, blank=False)
    position = models.CharField(_("Position"), max_length=30, blank=False)

    def __str__(self):
        return f"Board: {self.member.username} - {self.position}"

    class Meta:
        ordering = ['order']


class BuildingEntrance(models.Model):
    building = models.ForeignKey(
        Building, on_delete=models.CASCADE, verbose_name=_("Building"), null=False, blank=False
    )
    description = models.CharField(_("Description"), max_length=50, blank=False)
    address = models.CharField(_("Address"), max_length=50, blank=False)

    def __str__(self):
        return f"BuildingEntrance: {self.description}"

    class Meta:
        ordering = ['description']


class BuildingUnitType(models.Model):
    description = models.CharField(_("Description"), max_length=50, blank=False)

    def __str__(self):
        return f"BuildingUnitType: {self.description}"

    class Meta:
        ordering = ['description']


class BuildingUnit(models.Model):
    building = models.ForeignKey(
        Building, on_delete=models.CASCADE, verbose_name=_("Building"), null=False, blank=False
    )
    type = models.ForeignKey(
        BuildingUnitType, on_delete=models.CASCADE, verbose_name=_("Type"), null=False, blank=False
    )
    entrance = models.ForeignKey(
        BuildingEntrance, on_delete=models.CASCADE, verbose_name=_("Entrance"), null=True, blank=True
    )
    registration_id = models.CharField(_("Registration Id"), max_length=50, blank=False)
    description = models.CharField(_("Description"), max_length=50, blank=False)
    numerator = models.IntegerField(_("Numerator"), blank=False)
    denominator = models.IntegerField(_("Denominator"), blank=False)
    users = models.ManyToManyField(User, through='BuildingUnitUser', related_name='building_units')

    def __str__(self):
        return f"BuildingUnit: {self.description}"

    @property
    def owners(self):
        return User.objects.filter(
            unit_memberships__building_unit=self, unit_memberships__role=BuildingUnitUser.ROLE_OWNER
        )

    @property
    def tenants(self):
        return User.objects.filter(
            unit_memberships__building_unit=self, unit_memberships__role=BuildingUnitUser.ROLE_TENANT
        )

    class Meta:
        ordering = ['description']


class BuildingUnitUser(models.Model):
    ROLE_OWNER = 'owner'
    ROLE_TENANT = 'tenant'
    ROLE_CHOICES = (
        (ROLE_OWNER, _("Owner")),
        (ROLE_TENANT, _("Tenant")),
    )

    building_unit = models.ForeignKey(
        BuildingUnit, on_delete=models.CASCADE, related_name='unit_users', verbose_name=_("Building unit")
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='unit_memberships')
    role = models.CharField(_("Role"), max_length=10, choices=ROLE_CHOICES, default=ROLE_OWNER)

    def __str__(self):
        return f"BuildingUnitUser: {self.user} ({self.role})"

    class Meta:
        unique_together = ('building_unit', 'user', 'role')
        ordering = ['building_unit', 'role', 'user']


# Faults
#####################


class FaultReport(models.Model):
    subject = models.CharField(_("Subject"), max_length=50)
    slug = models.CharField(max_length=50, unique=True)
    description = models.TextField(_("Description"))
    created_date = models.DateTimeField(auto_now_add=True)
    created_by_user = models.ForeignKey(User, on_delete=models.CASCADE)
    assigned_to_user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='assigned_fault_set', null=True, blank=True
    )
    watching_users = models.ManyToManyField(User, related_name='watching_fault_set')
    closed = models.BooleanField(_("Closed"), default=False)
    entrance = models.ForeignKey(
        BuildingEntrance, on_delete=models.CASCADE, verbose_name=_("Entrance"), null=True, blank=True
    )

    def __str__(self):
        return f"FaultReport: {self.subject}"

    @property
    def assets(self):
        return self.faultasset_set.all()

    @property
    def image_assets(self):
        return [a for a in self.assets if a.is_image]

    @property
    def other_assets(self):
        return [a for a in self.assets if not a.is_image]

    @property
    def comments(self):
        return self.faultcomment_set.all()

    class Meta:
        ordering = ['-id']
        permissions = (
            ("svjis_view_fault_menu", _("Can view Faults menu")),
            ("svjis_fault_reporter", _("Can report fault")),
            ("svjis_fault_resolver", _("Can resolve fault")),
        )

    def can_be_edited_by(self, user: User) -> bool:
        if user.has_perm(svjis_fault_resolver):
            return True
        return not self.closed and user.has_perm(svjis_fault_reporter) and self.created_by_user_id == user.id

    def log_taking_ticket(self, user: User):
        FaultReportLog.objects.create(fault_report=self, user=user, resolver=user, type=FaultReportLog.TYPE_ASSIGNED)

    def log_closing_ticket(self, user: User):
        FaultReportLog.objects.create(
            fault_report=self, user=user, resolver=self.assigned_to_user, type=FaultReportLog.TYPE_CLOSED
        )

    def log_reopening_ticket(self, user: User):
        FaultReportLog.objects.create(
            fault_report=self, user=user, resolver=self.assigned_to_user, type=FaultReportLog.TYPE_REOPENED
        )

    def save(self, **kwargs):
        if not self.slug:
            unique_slugify(self, self.subject)
        super().save(**kwargs)


def fault_directory_path(instance, filename):
    return f'{MEDIA_FAULT_ASSETS_DIR}/{instance.fault_report.slug}/{filename}'


class FaultAsset(models.Model):
    description = models.CharField(_("Description"), max_length=100)
    file = models.FileField(_("File"), upload_to=fault_directory_path)
    fault_report = models.ForeignKey(FaultReport, on_delete=models.CASCADE, verbose_name=_("Fault report"))
    created_date = models.DateTimeField(auto_now_add=True)
    created_by_user = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return f"FaultAsset: {self.description}"

    @property
    def basename(self):
        return os.path.basename(self.file.path)

    @property
    def icon(self):
        return get_asset_icon(self.basename)

    @property
    def is_image(self):
        return self.icon == 'image'

    def delete(self, *args, **kwargs):
        if os.path.isfile(self.file.path):
            os.remove(self.file.path)
        super().delete(*args, **kwargs)

    class Meta:
        ordering = ['id']


class FaultComment(models.Model):
    fault_report = models.ForeignKey(FaultReport, on_delete=models.CASCADE, verbose_name=_("Fault report"))
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    created_date = models.DateTimeField(auto_now_add=True)
    body = models.TextField(_("Body"))

    def __str__(self):
        return f"FaultComment: {self.fault_report} - {self.body}"

    @property
    def is_editable(self) -> bool:
        age = get_age_in_minutes(self.created_date)
        if age is not None:
            return age <= COMMENT_IS_EDITABLE_MINUTES
        else:
            return False

    class Meta:
        ordering = ['id']
        permissions = (("svjis_add_fault_comment", _("Can add Fault comment")),)


class FaultReportLog(models.Model):
    TYPE_MODIFIED = "modified"
    TYPE_ASSIGNED = "assigned"
    TYPE_CLOSED = "closed"
    TYPE_REOPENED = "reopened"
    TYPE_CREATED = "created"

    TYPE_CHOICES = (
        (TYPE_MODIFIED, _("Modified")),
        (TYPE_ASSIGNED, _("Assigned")),
        (TYPE_CLOSED, _("Closed")),
        (TYPE_REOPENED, _("Reopened")),
        (TYPE_CREATED, _("Created")),
    )

    fault_report = models.ForeignKey(FaultReport, on_delete=models.CASCADE, related_name='logs')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_fault_report_logs', null=True)
    resolver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='resolved_fault_report_logs', null=True)
    type = models.CharField(_("Type"), max_length=10, choices=TYPE_CHOICES, default=TYPE_MODIFIED)
    entry_time = models.DateTimeField(auto_now_add=True)

    objects = managers.FaultReportLogManager()

    def __str__(self):
        return f"FaultReportLog: {self.fault_report} ({self.type})"


# Adverts
#####################


class AdvertType(models.Model):
    description = models.CharField(_("Description"), max_length=50, blank=False)

    class Meta:
        ordering = ['description']

    def __str__(self):
        return self.description


def advert_cover_directory_path(instance, filename):
    # Keyed by the author, not the advert pk, since the pk doesn't exist yet
    # when a cover image is uploaded together with a brand new advert.
    return f'{MEDIA_ADVERT_ASSETS_DIR}/covers/{instance.created_by_user_id}/{filename}'


class Advert(models.Model):
    type = models.ForeignKey(AdvertType, on_delete=models.CASCADE, verbose_name=_("Type"))
    header = models.CharField(_("Header"), max_length=50)
    body = models.TextField(_("Body"))
    cover_image = models.FileField(_("Cover image"), upload_to=advert_cover_directory_path, null=True, blank=True)
    created_by_user = models.ForeignKey(User, on_delete=models.CASCADE)
    phone = models.CharField(_("Phone"), max_length=30, blank=True)
    email = models.CharField(_("E-Mail"), max_length=50, blank=True)
    created_date = models.DateTimeField(auto_now_add=True)
    published = models.BooleanField(_("Published"), default=True)

    def __str__(self):
        return f"Advert: {self.header}"

    @property
    def assets(self):
        return self.advertasset_set.all()

    @property
    def image_assets(self):
        return [a for a in self.assets if a.is_image]

    @property
    def other_assets(self):
        return [a for a in self.assets if not a.is_image]

    def delete(self, *args, **kwargs):
        if self.cover_image and os.path.isfile(self.cover_image.path):
            os.remove(self.cover_image.path)
        for asset in self.assets:
            asset.delete()
        super().delete(*args, **kwargs)

    class Meta:
        ordering = ['-id']
        permissions = (
            ("svjis_view_adverts_menu", _("Can view Adverts menu")),
            ("svjis_add_advert", _("Can add Advert")),
        )


def advert_directory_path(instance, filename):
    return f'{MEDIA_ADVERT_ASSETS_DIR}/{instance.advert.pk}/{filename}'


class AdvertAsset(models.Model):
    description = models.CharField(_("Description"), max_length=100)
    file = models.FileField(_("File"), upload_to=advert_directory_path)
    advert = models.ForeignKey(Advert, on_delete=models.CASCADE, verbose_name=_("Advert"))
    created_date = models.DateTimeField(auto_now_add=True)
    created_by_user = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return f"AdvertAsset: {self.description}"

    @property
    def basename(self):
        return os.path.basename(self.file.path)

    @property
    def icon(self):
        return get_asset_icon(self.basename)

    @property
    def is_image(self):
        return self.icon == 'image'

    def delete(self, *args, **kwargs):
        if os.path.isfile(self.file.path):
            os.remove(self.file.path)
        super().delete(*args, **kwargs)

    class Meta:
        ordering = ['-id']


# Projects
#####################


class ProjectStatus(models.Model):
    name = models.CharField(_("Name"), max_length=50)
    order = models.IntegerField(_("Order"))
    is_closed = models.BooleanField(_("Closed state"), default=False)
    color = models.CharField(_("Color"), max_length=10, choices=BADGE_COLOR_CHOICES, default='slate')

    def __str__(self):
        return f"ProjectStatus: {self.name}"

    class Meta:
        ordering = ['order']
        permissions = (("svjis_edit_admin_project_statuses", _("Can edit Project statuses")),)


class Project(models.Model):
    subject = models.CharField(_("Subject"), max_length=100)
    slug = models.CharField(max_length=100, unique=True)
    description = models.TextField(_("Description"))
    created_date = models.DateTimeField(auto_now_add=True)
    created_by_user = models.ForeignKey(User, on_delete=models.CASCADE)
    assigned_to_user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='assigned_project_set', null=True, blank=True
    )
    watching_users = models.ManyToManyField(User, related_name='watching_project_set')
    status = models.ForeignKey(ProjectStatus, on_delete=models.PROTECT, verbose_name=_("Status"))
    deadline = models.DateField(_("Deadline"), null=True, blank=True)

    def __str__(self):
        return f"Project: {self.subject}"

    @property
    def assets(self):
        return self.projectasset_set.all()

    @property
    def image_assets(self):
        return [a for a in self.assets if a.is_image]

    @property
    def other_assets(self):
        return [a for a in self.assets if not a.is_image]

    @property
    def comments(self):
        return self.projectcomment_set.all()

    class Meta:
        ordering = ['-id']
        permissions = (
            ("svjis_view_project_menu", _("Can view Projects menu")),
            ("svjis_add_project", _("Can add Project")),
            ("svjis_manage_projects", _("Can manage all Projects")),
        )

    def can_be_edited_by(self, user: User) -> bool:
        if user.has_perm(svjis_manage_projects):
            return True
        if self.status.is_closed:
            return False
        return user.has_perm(svjis_view_project_menu) and user.id in (
            self.created_by_user_id,
            self.assigned_to_user_id,
        )

    def log_status_change(self, user: User, from_status: ProjectStatus, to_status: ProjectStatus):
        ProjectLog.objects.create(
            project=self,
            user=user,
            assignee=self.assigned_to_user,
            from_status=from_status,
            to_status=to_status,
            type=ProjectLog.TYPE_STATUS_CHANGED,
        )

    def save(self, **kwargs):
        if not self.slug:
            unique_slugify(self, self.subject)
        super().save(**kwargs)


def project_directory_path(instance, filename):
    return f'{MEDIA_PROJECT_ASSETS_DIR}/{instance.project.slug}/{filename}'


class ProjectAsset(models.Model):
    description = models.CharField(_("Description"), max_length=100)
    file = models.FileField(_("File"), upload_to=project_directory_path)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, verbose_name=_("Project"))
    created_date = models.DateTimeField(auto_now_add=True)
    created_by_user = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return f"ProjectAsset: {self.description}"

    @property
    def basename(self):
        return os.path.basename(self.file.path)

    @property
    def icon(self):
        return get_asset_icon(self.basename)

    @property
    def is_image(self):
        return self.icon == 'image'

    def delete(self, *args, **kwargs):
        if os.path.isfile(self.file.path):
            os.remove(self.file.path)
        super().delete(*args, **kwargs)

    class Meta:
        ordering = ['id']


class ProjectComment(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, verbose_name=_("Project"))
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    created_date = models.DateTimeField(auto_now_add=True)
    body = models.TextField(_("Body"))

    def __str__(self):
        return f"ProjectComment: {self.project} - {self.body}"

    @property
    def is_editable(self) -> bool:
        age = get_age_in_minutes(self.created_date)
        if age is not None:
            return age <= COMMENT_IS_EDITABLE_MINUTES
        else:
            return False

    class Meta:
        ordering = ['id']
        permissions = (("svjis_add_project_comment", _("Can add Project comment")),)


class ProjectLog(models.Model):
    TYPE_MODIFIED = "modified"
    TYPE_ASSIGNED = "assigned"
    TYPE_STATUS_CHANGED = "status_changed"
    TYPE_CREATED = "created"

    TYPE_CHOICES = (
        (TYPE_MODIFIED, _("Modified")),
        (TYPE_ASSIGNED, _("Assigned")),
        (TYPE_STATUS_CHANGED, _("Status changed")),
        (TYPE_CREATED, _("Created")),
    )

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='logs')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_project_logs', null=True)
    assignee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assigned_project_logs', null=True)
    from_status = models.ForeignKey(
        ProjectStatus, on_delete=models.SET_NULL, related_name='+', null=True, blank=True
    )
    to_status = models.ForeignKey(ProjectStatus, on_delete=models.SET_NULL, related_name='+', null=True, blank=True)
    type = models.CharField(_("Type"), max_length=15, choices=TYPE_CHOICES, default=TYPE_MODIFIED)
    entry_time = models.DateTimeField(auto_now_add=True)

    objects = managers.ProjectLogManager()

    def __str__(self):
        return f"ProjectLog: {self.project} ({self.type})"


# Tags
#####################


class Tag(models.Model):
    name = models.CharField(_("Name"), max_length=30, unique=True)
    color = models.CharField(_("Color"), max_length=10, choices=BADGE_COLOR_CHOICES, default='slate')

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        permissions = (("svjis_edit_admin_tags", _("Can edit Tags")),)


TAG_MODELS = [
    (Project, _("Project")),
]


def get_tag_model_labels():
    return {ContentType.objects.get_for_model(model).pk: label for model, label in TAG_MODELS}


class TaggedItem(models.Model):
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    def __str__(self):
        return f"TaggedItem: {self.tag} - {self.content_object}"

    class Meta:
        unique_together = ('tag', 'content_type', 'object_id')


# Custom fields
#####################


CUSTOM_FIELD_MODELS = [
    (User, _("User")),
    (BuildingUnit, _("Building unit")),
    (Advert, _("Advert")),
    (Board, _("Board member")),
    (BuildingEntrance, _("Entrance")),
    (FaultReport, _("Fault report")),
    (Project, _("Project")),
]


def get_custom_field_model_labels():
    return {ContentType.objects.get_for_model(model).pk: label for model, label in CUSTOM_FIELD_MODELS}


class CustomFieldDefinition(models.Model):
    TYPE_TEXT = 'text'
    TYPE_NUMBER = 'number'
    TYPE_ENUM = 'enum'
    TYPE_DATETIME = 'datetime'
    TYPE_BOOLEAN = 'boolean'
    TYPE_CHOICES = (
        (TYPE_TEXT, _("Text")),
        (TYPE_NUMBER, _("Number")),
        (TYPE_ENUM, _("Choice list")),
        (TYPE_DATETIME, _("Date/time")),
        (TYPE_BOOLEAN, _("Yes/No")),
    )

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, verbose_name=_("Entity type"))
    name = models.CharField(_("Name"), max_length=50)
    field_type = models.CharField(_("Type"), max_length=10, choices=TYPE_CHOICES, default=TYPE_TEXT)
    enum_options = models.CharField(
        _("Options (comma-separated)"),
        max_length=500,
        blank=True,
        help_text=_("Only used when Type is 'Choice list', e.g.: malý,střední,velký"),
    )

    def enum_choices(self):
        return [o.strip() for o in self.enum_options.split(',') if o.strip()]

    def __str__(self):
        return f"CustomFieldDefinition: {self.content_type} - {self.name}"

    class Meta:
        unique_together = ('content_type', 'name')
        ordering = ['content_type', 'name']
        permissions = (("svjis_edit_admin_custom_fields", _("Can edit Custom fields")),)


class CustomFieldValue(models.Model):
    field_definition = models.ForeignKey(CustomFieldDefinition, on_delete=models.CASCADE, related_name='values')
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    value = models.CharField(_("Value"), max_length=255)

    def __str__(self):
        return f"CustomFieldValue: {self.field_definition.name} = {self.value}"

    class Meta:
        unique_together = ('field_definition', 'content_type', 'object_id')
