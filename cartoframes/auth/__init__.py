from __future__ import absolute_import

from ..credentials import Credentials
from ..context import CartoContext as Context

_default_context = None


def set_default_context(context=None, base_url=None, api_key=None, creds=None, session=None):
    global _default_context
    if isinstance(context, Context):
        _default_context = context
    elif isinstance(base_url, str) and isinstance(api_key, str):
        _default_context = Context(base_url=base_url, api_key=api_key, session=session)
    elif isinstance(creds, Credentials):
        _default_context = Context(creds=creds, session=session)
    else:
        raise ValueError('Invalid inputs. Pass a Context, a base_url and api_key pair, or a Credentials object.')


__all__ = [
    'Context',
    'set_default_context'
]
