from __future__ import absolute_import

import numpy as np
import collections
from cartoframes import utils
from ..utils.html import HTMLMap
from ..utils import defaults
from ..basemap.basemaps import Basemaps
from ..source.geojson import GeoJSON


class Map(object):
    """CARTO VL-powered interactive map

    Args:
        layers (list of Layer-types): List of layers. One or more of
          :py:class:`Layer <cartoframes.contrib.vector.Layer>`.
        context (:py:class:`CartoContext <cartoframes.context.CartoContext>`):
          A :py:class:`CartoContext <cartoframes.context.CartoContext>`
          instance
        size (tuple of int): a (width, height) pair for the size of the map.
          Default is (1024, 632)
        basemap (str):
          - if a `str`, name of a CARTO vector basemap. One of `positron`,
            `voyager`, or `darkmatter` from the :obj:`BaseMaps` class
          - if a `dict`, Mapbox or other style as the value of the `style` key.
            If a Mapbox style, the access token is the value of the `token`
            key.
        bounds (dict or list): a dict with `east`,`north`,`west`,`south`
          properties, or a list of floats in the following order: [west,
          south, east, north]. If not provided the bounds will be automatically
          calculated to fit all features.

    Example:

        .. code::

            from cartoframes import carto_vl as vl
            from cartoframes import CartoContext

            context = CartoContext(
                base_url='https://your_user_name.carto.com',
                api_key='your api key'
            )

            vl.Map([vl.Layer('table in your account')], context)

        CARTO basemap style.

        .. code::

            from cartoframes import carto_vl as vl
            from cartoframes import CartoContext

            context = CartoContext(
                base_url='https://your_user_name.carto.com',
                api_key='your api key'
            )

            vl.Map(
                [vl.Layer('table in your account')],
                context,
                basemap=vector.basemaps.darkmatter
            )

        Custom basemap style. Here we use the Mapbox streets style, which
        requires an access token.

        .. code::

            from cartoframes import carto_vl as vl
            from cartoframes import CartoContext

            context = CartoContext(
                base_url='https://your_user_name.carto.com',
                api_key='your api key'
            )

            basemap = {
                'style': 'mapbox://styles/mapbox/streets-v9',
                'token: '<your mapbox token>'
            }

            vl.Map(
                [vl.Layer('table in your account')],
                context,
                basemap
            )

        Custom bounds

        .. code::

            from cartoframes import carto_vl as vl
            from cartoframes import CartoContext

            context = CartoContext(
                base_url='https://your_user_name.carto.com',
                api_key='your api key'
            )

            bounds = {
                'west': -10,
                'east': 10,
                'north': -10,
                'south': 10
            }

            vl.Map(
                [vl.Layer('table in your account')],
                context,
                bounds
            )
    """

    @utils.temp_ignore_warnings
    def __init__(self,
                 layers=None,
                 size=None,
                 basemap=Basemaps.voyager,
                 bounds=None,
                 viewport=None,
                 template=None,
                 **kwargs):

        self.layers = _init_layers(layers)
        self.size = size
        self.basemap = basemap
        self.viewport = viewport
        self.template = template
        self.sources = _get_map_layers(self.layers)
        self.bounds = _get_bounds(bounds, self.layers)
        self._carto_vl_path = kwargs.get('_carto_vl_path', defaults._CARTO_VL_PATH)
        self._airship_path = kwargs.get('_airship_path', None)
        self._htmlMap = HTMLMap()

        self._htmlMap.set_content(
            size=self.size,
            sources=self.sources,
            bounds=self.bounds,
            viewport=self.viewport,
            basemap=self.basemap,
            _carto_vl_path=self._carto_vl_path,
            _airship_path=self._airship_path)

    def _repr_html_(self):
        return self._htmlMap.html


def _get_bounds(bounds, layers):
    return (
        _format_bounds(bounds)
        if bounds
        else _get_super_bounds(layers)
    )


def _init_layers(layers):
    if layers is None:
        return None
    if not isinstance(layers, collections.Iterable):
        return [layers]
    else:
        return layers[::-1]


def _get_map_layers(layers):
    if layers is None:
        return None
    return list(map(_set_map_layer, layers))


def _set_map_layer(layer):
    return ({
        'type': layer.source.type,
        'query': layer.source.query,
        'credentials': layer.source.credentials,
        'legend': layer.legend,
        'interactivity': layer.interactivity,
        'viz': layer.viz
    })


def _format_bounds(bounds):
    if isinstance(bounds, dict):
        return _dict_bounds(bounds)

    return _list_bounds(bounds)


def _list_bounds(bounds):
    if len(bounds) != 4:
        raise ValueError('bounds list must have exactly four values in the '
                         'order: [west, south, east, north]')

    return _dict_bounds({
        'west': bounds[0],
        'south': bounds[1],
        'east': bounds[2],
        'north': bounds[3]
    })


def _dict_bounds(bounds):
    if 'west' not in bounds or 'east' not in bounds or 'north' not in bounds\
            or 'south' not in bounds:
        raise ValueError('bounds must have east, west, north and '
                         'south properties')

    return '[[{west}, {south}], [{east}, {north}]]'.format(**bounds)


def _get_super_bounds(layers):
    """"""
    if layers:
        hosted_layers = [
            layer for layer in layers
            if not isinstance(layer.source, GeoJSON)
        ]
        local_layers = [
            layer for layer in layers
            if isinstance(layer.source, GeoJSON)
        ]
    else:
        hosted_layers = []
        local_layers = []

    hosted_bounds = dict.fromkeys(['west', 'south', 'east', 'north'])
    local_bounds = dict.fromkeys(['west', 'south', 'east', 'north'])
        
    if hosted_layers:
        hosted_bounds = _get_bounds_hosted(hosted_layers)

    if local_layers:
        local_bounds = _get_bounds_local(local_layers)

    bounds = _combine_bounds(hosted_bounds, local_bounds)

    return _format_bounds(bounds)


def _get_bounds_local(layers):
    """Aggregates bounding boxes of all local layers

        return: dict of bounding box of all bounds in layers
    """
    if not layers:
        return {'west': None, 'south': None, 'east': None, 'north': None}

    bounds = layers[0].bounds

    for layer in layers[1:]:
        bounds = np.concatenate(
            (
                np.minimum(
                    bounds[:2],
                    layer.bounds[:2]
                ),
                np.maximum(
                    bounds[2:],
                    layer.bounds[2:]
                )
            )
        )

    return dict(zip(['west', 'south', 'east', 'north'], bounds))


def _get_bounds_hosted(layers):
    """Aggregates bounding boxes of all hosted layers

        return: dict of bounding box of all bounds in layers
    """
    if not layers:
        return {'west': None, 'south': None, 'east': None, 'north': None}

    context = layers[0].source.context
    bounds = context._get_bounds([layers[0]])

    for layer in layers[1:]:
        context = layer.source.context
        next_bounds = context._get_bounds(layer)
        bounds = _combine_bounds(bounds, next_bounds)

    return bounds


def _combine_bounds(bbox1, bbox2):
    """Takes two bounding boxes dicts and gives a new bbox that encompasses
    them both"""
    WORLD = {'west': -180, 'south': -85.1, 'east': 180, 'north': 85.1}
    ALL_KEYS = set(WORLD.keys())

    # if neither are defined, use the world
    if not bbox1 and not bbox2:
        return WORLD
    # if all nones, use the world
    if _dict_all_nones(bbox1) and _dict_all_nones(bbox2):
        return WORLD

    # if one is none return the other
    if not bbox1 or not bbox2:
        return bbox1 or bbox2

    assert ALL_KEYS == set(bbox1.keys()) and ALL_KEYS == set(bbox2.keys()),\
        'Input bounding boxes must have the same dictionary keys'
    # create dict with cardinal directions and None-valued keys
    outbbox = dict.fromkeys(['west', 'south', 'east', 'north'])

    # set values and/or defaults
    for coord in ('north', 'east'):
        outbbox[coord] = np.nanmax([
                _conv2nan(bbox1[coord]),
                _conv2nan(bbox2[coord])
            ])
    for coord in ('south', 'west'):
        outbbox[coord] = np.nanmin([
                _conv2nan(bbox1[coord]),
                _conv2nan(bbox2[coord])
            ])

    return outbbox


def _dict_all_nones(bbox_dict):
    """Returns True if all dict values are None"""
    return bbox_dict and all(v is None for v in bbox_dict.values())


def _conv2nan(val):
    """convert Nones to np.nans"""
    return np.nan if val is None else val
