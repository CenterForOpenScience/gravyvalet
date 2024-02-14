# -*- coding: utf-8 -*-
"""Consolidates settings from defaults.py and local.py.

::
"""
import warnings

from .settings import *  # noqa


try:
    from .local import *  # noqa
except ImportError:
    warnings.warn(
        "No api/base/settings/local.py settings file found. Did you remember to "
        "copy local-dist.py to local.py?",
        ImportWarning,
    )
