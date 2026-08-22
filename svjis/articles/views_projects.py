import os
from pathlib import PurePosixPath
from . import utils, forms, models, views_admin
from django.conf import settings
from django.contrib.auth.decorators import permission_required
from django.contrib.contenttypes.models import ContentType
from django.contrib import messages
from django.core.paginator import Paginator, InvalidPage
from django.db import transaction
from django.db.models import Count, Q
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST
from .model_utils import PICTURE_ICONS, resize_uploaded_image
from .permissions import (
    svjis_view_project_menu,
    svjis_add_project,
    svjis_manage_projects,
    svjis_add_project_comment,
)
from .templatetags.article_filters import highlight, highlight_exact


def get_side_menu(active_item, user):
    side_menu = [
        {
            'perms': svjis_view_project_menu,
            'description': _("Active") + f' ({models.Project.objects.filter(status__is_closed=False).count()})',
            'link': reverse(projects_list_view) + '?scope=active',
            'active': True if active_item == 'active' else False,
        },
        {
            'perms': svjis_view_project_menu,
            'description': _("Mine")
            + f' ({models.Project.objects.filter(Q(created_by_user=user) | Q(assigned_to_user=user)).count()})',
            'link': reverse(projects_list_view) + '?scope=mine',
            'active': True if active_item == 'mine' else False,
        },
        {
            'perms': svjis_view_project_menu,
            'description': _("All") + f' ({models.Project.objects.count()})',
            'link': reverse(projects_list_view) + '?scope=all',
            'active': True if active_item == 'all' else False,
        },
        {
            'perms': svjis_view_project_menu,
            'description': _("Kanban board"),
            'link': reverse(projects_kanban_view),
            'active': True if active_item == 'kanban' else False,
        },
    ]
    return [x for x in side_menu if x['perms'] is None or user.has_perm(x['perms'])]


# Projects - Project
@permission_required(svjis_view_project_menu)
@require_GET
def projects_list_view(request):
    project_list = models.Project.objects.select_related('created_by_user', 'assigned_to_user', 'status')
    scope = request.GET.get('scope', 'active')
    if scope == 'active':
        project_list = project_list.filter(status__is_closed=False)
    if scope == 'mine':
        project_list = project_list.filter(Q(created_by_user=request.user) | Q(assigned_to_user=request.user))

    status_id = request.GET.get('status', '')
    if status_id.isdigit():
        project_list = project_list.filter(status_id=int(status_id))

    tag_id = request.GET.get('tag', '')
    if tag_id.isdigit():
        ct = ContentType.objects.get_for_model(models.Project)
        tagged_ids = models.TaggedItem.objects.filter(content_type=ct, tag_id=int(tag_id)).values_list(
            'object_id', flat=True
        )
        project_list = project_list.filter(pk__in=list(tagged_ids))

    # Search
    search = request.GET.get('search')
    if search is not None and not str(search).isdigit() and len(search) < 3:
        messages.error(request, _("Search: Keyword '{}' is too short. Type at least 3 characters.").format(search))
        search = None
    if search is not None and len(search) > 100:
        messages.error(request, _("Search: Keyword is too long. Type maximum of 100 characters."))
        search = None
    if search is not None:
        query = Q(subject__icontains=search) | Q(description__icontains=search)
        if str(search).isdigit():
            query |= Q(id=int(search))
        project_list = project_list.filter(query)
        header = _("Search results") + f": {search}"
    else:
        search = ''
        header = _("Projects")

    # Paginator
    is_paginated = len(project_list) > getattr(settings, 'SVJIS_PROJECTS_PAGE_SIZE', 10)
    page = request.GET.get('page', 1)
    paginator = Paginator(project_list, per_page=getattr(settings, 'SVJIS_PROJECTS_PAGE_SIZE', 10))
    page_obj = paginator.get_page(page)
    try:
        project_list = paginator.page(page)
    except InvalidPage:
        project_list = paginator.page(paginator.num_pages)
    page_parameter = f'scope={scope}' if search == '' else f"search={search}"

    rows = []
    for obj in project_list:
        detail_url = reverse('project', kwargs={'slug': obj.slug})
        if search:
            detail_url += f'?search={search}'
        actions = []
        if obj.can_be_edited_by(request.user):
            actions.append(
                {'url': reverse('projects_project_edit', args=[obj.pk]), 'icon': 'edit', 'label': _('Edit')}
            )
        actions.append({'url': detail_url, 'icon': 'view', 'label': _('View')})
        rows.append(
            {
                'url': detail_url,
                'row_class': 'closed-ticket' if obj.status.is_closed else '',
                'cells': {
                    'id': highlight_exact(str(obj.pk), search),
                    'subject': highlight(obj.subject, search),
                    'status': obj.status.name,
                    'assignee': (
                        f'{obj.assigned_to_user.first_name} {obj.assigned_to_user.last_name}'
                        if obj.assigned_to_user
                        else ''
                    ),
                    'deadline': obj.deadline.strftime('%d.%m.%Y') if obj.deadline else '',
                },
                'actions': actions,
            }
        )

    ctx = utils.get_context()
    ctx['aside_menu_name'] = _("Projects")
    ctx['header'] = header
    ctx['is_paginated'] = is_paginated
    ctx['page_obj'] = page_obj
    ctx['page_parameter'] = page_parameter
    ctx['search_endpoint'] = reverse(projects_list_view)
    ctx['search'] = search
    ctx['aside_menu_items'] = get_side_menu(scope, request.user)
    ctx['tray_menu_items'] = utils.get_tray_menu('projects', request.user)
    ctx['object_list'] = project_list
    ctx['all_statuses'] = models.ProjectStatus.objects.all()
    ctx['all_tags'] = models.Tag.objects.all()
    ctx['selected_status'] = status_id
    ctx['selected_tag'] = tag_id
    ctx['columns'] = [
        {'key': 'id', 'label': _('No.')},
        {'key': 'subject', 'label': _('Subject')},
        {'key': 'status', 'label': _('Status')},
        {'key': 'assignee', 'label': _('Assigned to'), 'hide_on_mobile': True},
        {'key': 'deadline', 'label': _('Deadline'), 'hide_on_mobile': True},
    ]
    ctx['rows'] = rows
    ctx['table_id'] = 'projects-table'
    ctx['desc_id'] = 'projects'
    ctx['list_search'] = True
    return render(request, "projects_list.html", ctx)


@permission_required(svjis_view_project_menu)
@require_GET
def projects_kanban_view(request):
    show_closed = request.GET.get('show_closed') == '1'
    statuses = models.ProjectStatus.objects.all()
    if not show_closed:
        statuses = statuses.exclude(is_closed=True)

    project_list = list(
        models.Project.objects.select_related('status', 'assigned_to_user').annotate(
            comment_count=Count('projectcomment', distinct=True),
            asset_count=Count('projectasset', distinct=True),
        )
    )

    ct = ContentType.objects.get_for_model(models.Project)
    tags_by_project = {}
    for ti in models.TaggedItem.objects.filter(
        content_type=ct, object_id__in=[p.id for p in project_list]
    ).select_related('tag'):
        tags_by_project.setdefault(ti.object_id, []).append(ti.tag)

    for p in project_list:
        p.tag_list = tags_by_project.get(p.id, [])
        p.can_edit_by_me = p.can_be_edited_by(request.user)

    columns = [
        {'status': s, 'projects': [p for p in project_list if p.status_id == s.id]}
        for s in statuses
    ]

    ctx = utils.get_context()
    ctx['aside_menu_name'] = _("Projects")
    ctx['aside_menu_items'] = get_side_menu('kanban', request.user)
    ctx['tray_menu_items'] = utils.get_tray_menu('projects', request.user)
    ctx['columns'] = columns
    ctx['show_closed'] = show_closed
    return render(request, "projects_kanban.html", ctx)


@permission_required(svjis_view_project_menu)
@require_GET
def project_view(request, slug):
    project = get_object_or_404(models.Project, slug=slug)
    ct = ContentType.objects.get_for_model(models.Project)
    tag_ids = models.TaggedItem.objects.filter(content_type=ct, object_id=project.pk).values_list(
        'tag_id', flat=True
    )

    ctx = utils.get_context()
    ctx['aside_menu_name'] = _("Projects")
    ctx['aside_menu_items'] = get_side_menu('active', request.user)
    ctx['tray_menu_items'] = utils.get_tray_menu('projects', request.user)
    ctx['obj'] = project
    ctx['search'] = request.GET.get('search', '')
    ctx['asset_form'] = forms.ProjectAssetForm
    ctx['comment_form'] = forms.ProjectCommentForm
    ctx['can_edit'] = project.can_be_edited_by(request.user)
    ctx['can_manage'] = request.user.has_perm(svjis_manage_projects)
    ctx['all_statuses'] = models.ProjectStatus.objects.all()
    ctx['tags'] = models.Tag.objects.filter(pk__in=list(tag_ids))
    ctx['custom_fields'] = views_admin.get_custom_fields_context(models.Project, project)

    ctx['breadcrumbs'] = [
        {'label': _('Projects'), 'url': reverse(projects_list_view)},
        {'label': project.subject},
    ]
    return render(request, "project.html", ctx)


@permission_required(svjis_view_project_menu)
@require_GET
def projects_project_edit_view(request, pk):
    project = get_object_or_404(models.Project, pk=pk)
    if not project.can_be_edited_by(request.user):
        raise Http404
    form = forms.ProjectForm(instance=project)

    tags_ctx = views_admin.get_tags_context(models.Project, project)

    ctx = utils.get_context()
    ctx['aside_menu_name'] = _("Projects")
    ctx['form'] = form
    ctx['pk'] = pk
    ctx['can_manage'] = request.user.has_perm(svjis_manage_projects)
    ctx['custom_fields'] = views_admin.get_custom_fields_context(models.Project, project)
    ctx.update(tags_ctx)
    ctx['aside_menu_items'] = get_side_menu('active', request.user)
    ctx['tray_menu_items'] = utils.get_tray_menu('projects', request.user)
    return render(request, "projects_edit.html", ctx)


@permission_required(svjis_add_project)
@require_GET
def projects_project_create_view(request):
    initial = {'created_by_user': request.user.pk}
    status_id = request.GET.get('status', '')
    default_status = models.ProjectStatus.objects.filter(pk=int(status_id)).first() if status_id.isdigit() else None
    if default_status is None:
        default_status = models.ProjectStatus.objects.order_by('order').first()
    if default_status:
        initial['status'] = default_status.pk
    form = forms.ProjectForm(initial=initial)
    ctx = utils.get_context()
    ctx['aside_menu_name'] = _("Projects")
    ctx['form'] = form
    ctx['pk'] = 0
    ctx.update(views_admin.get_tags_context(models.Project, None))
    ctx['aside_menu_items'] = get_side_menu('active', request.user)
    ctx['tray_menu_items'] = utils.get_tray_menu('projects', request.user)
    return render(request, "projects_create.html", ctx)


@permission_required(svjis_add_project)
@require_POST
def projects_project_create_save_view(request):
    pk = int(request.POST['pk'])
    form = forms.ProjectForm(request.POST)

    with transaction.atomic():
        if not form.is_valid() or pk != 0:
            for error in form.errors:
                messages.error(request, error)
            return redirect(reverse(projects_list_view) + '?scope=active')

        obj = form.save(commit=False)
        if (
            "created_by_user" not in form.data
            or form.data["created_by_user"] == ''
            or not request.user.has_perm(svjis_manage_projects)
        ):
            obj.created_by_user = request.user
        if not request.user.has_perm(svjis_manage_projects):
            obj.assigned_to_user = None
            obj.status = models.ProjectStatus.objects.order_by('order').first()
        elif obj.status_id is None:
            obj.status = models.ProjectStatus.objects.order_by('order').first()
        obj.save()
        for f in request.FILES.getlist('gallery'):
            try:
                f = resize_uploaded_image(f)
            except OSError:
                pass
            models.ProjectAsset.objects.create(project=obj, description='', file=f, created_by_user=request.user)
        views_admin.save_tags(request, obj)
        models.ProjectLog.objects.log_actions(request=request, form=form, queryset=[obj], created=True)

        # Set watching users
        obj.watching_users.add(obj.created_by_user)
        if obj.assigned_to_user is not None:
            obj.watching_users.add(obj.assigned_to_user)
        managers = (
            models.User.objects.filter(groups__permissions__codename='svjis_manage_projects')
            .exclude(is_active=False)
            .distinct()
        )
        for u in managers:
            obj.watching_users.add(u)

        # Send notifications
        recipients = [u for u in obj.watching_users.all() if u != obj.created_by_user]
        utils.send_new_project_notification(recipients, f"{request.scheme}://{request.get_host()}", obj)

        # Send assigned notification
        if obj.assigned_to_user is not None and request.user != obj.assigned_to_user:
            utils.send_project_assigned_notification(
                obj.assigned_to_user, request.user, f"{request.scheme}://{request.get_host()}", obj
            )
    messages.info(request, _('Saved'))
    return redirect(project_view, slug=obj.slug)


@permission_required(svjis_view_project_menu)
@require_POST
def projects_project_update_view(request):
    pk = int(request.POST['pk'])
    instance = get_object_or_404(models.Project, pk=pk)
    if not instance.can_be_edited_by(request.user):
        raise Http404
    original_assignee = instance.assigned_to_user
    original_status = instance.status
    original_status_id = instance.status_id

    # Only a manager may reassign or change the status; anyone else editing their own
    # project must not be able to smuggle these in via crafted POST data.
    data = request.POST
    if not request.user.has_perm(svjis_manage_projects):
        data = request.POST.copy()
        data['created_by_user'] = instance.created_by_user_id
        data['assigned_to_user'] = original_assignee.pk if original_assignee else ''
        data['status'] = original_status_id
    elif not data.get('status'):
        # status is optional at the form level (non-managers never see the field), so a
        # manager submitting without it must still fall back to the current status rather
        # than trying to save a NULL into a non-nullable column.
        data = request.POST.copy()
        data['status'] = original_status_id

    form = forms.ProjectForm(data, instance=instance)

    with transaction.atomic():
        if form.is_valid():
            form.save()
            for f in request.FILES.getlist('gallery'):
                try:
                    f = resize_uploaded_image(f)
                except OSError:
                    pass
                models.ProjectAsset.objects.create(
                    project=instance, description='', file=f, created_by_user=request.user
                )
            for error in views_admin.save_custom_fields(request, instance):
                messages.error(request, error)
            views_admin.save_tags(request, instance)
            models.ProjectLog.objects.log_actions(request=request, form=form, queryset=[instance])
        else:
            for error in form.errors:
                messages.error(request, error)

        # Set watching user
        instance.watching_users.add(request.user)

        # Send assigned notification
        if (
            original_assignee != instance.assigned_to_user
            and request.user != instance.assigned_to_user
            and instance.assigned_to_user is not None
        ):
            utils.send_project_assigned_notification(
                instance.assigned_to_user, request.user, f"{request.scheme}://{request.get_host()}", instance
            )

        # Send status changed notification
        if original_status_id != instance.status_id:
            instance.log_status_change(request.user, original_status, instance.status)
            recipients = [u for u in instance.watching_users.all() if u != request.user]
            utils.send_project_status_changed_notification(
                recipients,
                request.user,
                f"{request.scheme}://{request.get_host()}",
                instance,
                original_status,
                instance.status,
            )

    messages.info(request, _('Saved'))
    return redirect(project_view, slug=instance.slug)


# Projects - Status change (list/detail dropdown + Kanban drag&drop)
@permission_required(svjis_view_project_menu)
@require_POST
def projects_project_change_status_view(request):
    pk = int(request.POST['pk'])
    project = get_object_or_404(models.Project, pk=pk)
    if not project.can_be_edited_by(request.user):
        raise Http404

    new_status = get_object_or_404(models.ProjectStatus, pk=int(request.POST['status_id']))
    old_status = project.status

    with transaction.atomic():
        if new_status.pk != old_status.pk:
            project.status = new_status
            project.save()
            project.log_status_change(request.user, old_status, new_status)
            recipients = [u for u in project.watching_users.all() if u != request.user]
            utils.send_project_status_changed_notification(
                recipients,
                request.user,
                f"{request.scheme}://{request.get_host()}",
                project,
                old_status,
                new_status,
            )

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return HttpResponse(status=204)
    return redirect(project_view, slug=project.slug)


# Projects - Tags (inline "+ Add tag" on the create/edit sidebar, via AJAX)
@permission_required(svjis_view_project_menu)
@require_POST
def project_tag_create_view(request):
    name = request.POST.get('name', '').strip()
    if not name:
        return JsonResponse({'error': str(_('Tag name is required.'))}, status=400)
    color = request.POST.get('color', 'slate')
    if color not in dict(models.BADGE_COLOR_CHOICES):
        color = 'slate'
    tag, _created = models.Tag.objects.get_or_create(name__iexact=name, defaults={'name': name, 'color': color})
    return JsonResponse({'id': tag.pk, 'name': tag.name, 'color': tag.color})


# Projects - ProjectAsset
@permission_required(svjis_view_project_menu)
@require_POST
def projects_project_asset_save_view(request):
    project_pk = int(request.POST.get('project_pk'))
    project = get_object_or_404(models.Project, pk=project_pk)
    if not project.can_be_edited_by(request.user):
        raise Http404
    form = forms.ProjectAssetForm(request.POST, request.FILES)
    if form.is_valid():
        obj = form.save(commit=False)
        obj.project = project
        obj.created_by_user = request.user
        extension = os.path.splitext(obj.file.name)[1][1:].lower()
        if extension in PICTURE_ICONS:
            try:
                resized = resize_uploaded_image(obj.file)
            except OSError:
                pass
            else:
                obj.file.save(resized.name, resized, save=False)
        obj.save()
    else:
        for error in form.errors:
            messages.error(request, error)
    return redirect(reverse('project', kwargs={'slug': project.slug}) + '#assets')


@permission_required(svjis_view_project_menu)
@require_GET
def projects_project_asset_delete_view(request, pk):
    obj = get_object_or_404(models.ProjectAsset, pk=pk)
    project = obj.project
    if project.can_be_edited_by(request.user):
        obj.delete()
    return redirect(reverse('project', kwargs={'slug': project.slug}) + '#assets')


# Projects - ProjectComment
@permission_required(svjis_add_project_comment)
@require_POST
def project_comment_save_view(request):
    project_pk = int(request.POST.get('project_pk'))
    project = get_object_or_404(models.Project, pk=project_pk)
    form = forms.ProjectCommentForm(request.POST)
    if form.is_valid():
        obj = form.save(commit=False)
        obj.project = project
        obj.author = request.user
        obj.save()
        recipients = [u for u in project.watching_users.all() if u != request.user]
        utils.send_project_comment_notification(recipients, f"{request.scheme}://{request.get_host()}", project, obj)
        return redirect(reverse(project_watch_view) + f"?id={project_pk}&comment_id={obj.pk}&watch=1")
    else:
        messages.error(request, form.errors)
        return redirect(reverse('project', kwargs={'slug': project.slug}))


@permission_required(svjis_add_project_comment)
@require_GET
def project_comment_edit_view(request, pk):
    comment = get_object_or_404(models.ProjectComment, pk=pk)
    if comment.author == request.user and comment.is_editable:
        ctx = utils.get_context()
        ctx['aside_menu_name'] = _("Projects")
        ctx['form'] = forms.ProjectCommentForm(instance=comment)
        ctx['aside_menu_items'] = get_side_menu('active', request.user)
        ctx['tray_menu_items'] = utils.get_tray_menu('projects', request.user)
        return render(request, "project_comment_edit.html", ctx)
    else:
        messages.error(request, _('Comment cannot be modified anymore'))
        return redirect(reverse('project', kwargs={'slug': comment.project.slug}))


@permission_required(svjis_add_project_comment)
@require_POST
def project_comment_modify_view(request):
    comment_pk = int(request.POST.get('comment_pk'))
    comment = get_object_or_404(models.ProjectComment, pk=comment_pk)
    if comment.author == request.user and comment.is_editable:
        form = forms.ProjectCommentForm(request.POST, instance=comment)
        if form.is_valid():
            form.save()
        else:
            messages.error(request, form.errors)
        return redirect(
            reverse(project_watch_view) + f"?id={comment.project.pk}&comment_id={comment.pk}&watch=1"
        )
    else:
        messages.error(request, _('Comment cannot be modified anymore'))
        return redirect(reverse('project', kwargs={'slug': comment.project.slug}))


# Projects - Watching
@permission_required(svjis_view_project_menu)
@require_GET
def project_watch_view(request):
    try:
        pk = int(request.GET.get('id'))
        comment_pk = int(request.GET.get('comment_id', 0))
        watch = int(request.GET.get('watch'))
    except TypeError:
        raise Http404 from None

    project = get_object_or_404(models.Project, pk=pk)

    if watch == 0:
        project.watching_users.remove(request.user)
    else:
        project.watching_users.add(request.user)

    qs = f'#comment_{comment_pk}' if comment_pk > 0 else ''
    return redirect(reverse('project', kwargs={'slug': project.slug}) + qs)


# Projects - Log
@permission_required(svjis_view_project_menu)
@require_GET
def projects_project_logs_view(request, slug):
    project = get_object_or_404(models.Project, slug=slug)
    log = models.ProjectLog.objects.filter(project=project).order_by('-entry_time')

    ctx = utils.get_context()
    ctx['aside_menu_name'] = _("Projects")
    ctx['aside_menu_items'] = get_side_menu('active', request.user)
    ctx['tray_menu_items'] = utils.get_tray_menu('projects', request.user)
    ctx['obj'] = project
    ctx['log'] = log
    ctx['breadcrumbs'] = [
        {'label': _('Projects'), 'url': reverse(projects_list_view)},
        {'label': project.subject, 'url': reverse(project_view, args=[project.slug])},
        {'label': _('Log')},
    ]
    return render(request, "project_log.html", ctx)


# Media
@permission_required(svjis_view_project_menu)
@require_GET
def get_project_asset(request, slug, filename):
    # Block path traversal attempts like ../../secret.txt
    safe_name = PurePosixPath(filename).name
    if safe_name != filename:
        raise Http404()

    asset = get_object_or_404(models.ProjectAsset, file=f"{models.MEDIA_PROJECT_ASSETS_DIR}/{slug}/{safe_name}")
    return FileResponse(asset.file.open("rb"), as_attachment=False, filename=safe_name)
