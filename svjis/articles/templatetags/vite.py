import json

from django import template
from django.conf import settings
from django.contrib.staticfiles.storage import staticfiles_storage
from django.utils.safestring import mark_safe

register = template.Library()

MANIFEST_PATH = settings.BASE_DIR / 'articles' / 'static' / 'dist' / 'manifest.json'


def _load_manifest():
    if not MANIFEST_PATH.exists():
        return {}
    return json.loads(MANIFEST_PATH.read_text())


@register.simple_tag
def vite_asset(entry):
    data = _load_manifest().get(entry)
    if data is None:
        return ''
    return staticfiles_storage.url(f"dist/{data['file']}")


@register.simple_tag
def vite_css(entry):
    data = _load_manifest().get(entry, {})
    links = [f'<link rel="stylesheet" href="{staticfiles_storage.url(f"dist/{css}")}">' for css in data.get('css', [])]
    return mark_safe('\n'.join(links))
