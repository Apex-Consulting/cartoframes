
from .. import defaults
from ..popup import Popup


def serialize_palette(palette):
    if isinstance(palette, (list, tuple)):
        return '[{}]'.format(','.join(palette))
    return palette


def get_value(value, geom_type, prop):
    if value is None:
        return defaults.STYLE.get(geom_type, {}).get(prop)
    return value


def get_popup(popup, title, alt_title, value):
    if isinstance(popup, Popup):
        return popup

    return {
        'hover': {
            'title': title or alt_title,
            'value': '$' + value
        }
    }
