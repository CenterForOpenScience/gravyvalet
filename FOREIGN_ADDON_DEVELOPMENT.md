# Foreign Addon Development Guide

This guide explains how to develop Foreign Addons for gravyvalet, allowing you to create custom integrations that can be distributed as standalone Python packages.

## Overview

Foreign Addons are Django apps that extend gravyvalet's functionality by implementing new external service integrations. They can be developed independently and distributed as regular Python packages.

## Requirements

- Python 3.9+
- Django 4.2+
- gravyvalet addon_toolkit

## Development Steps

### 1. Create Your Package Structure

Create a standard Python package structure:

```
your_addon_package/
├── setup.py
├── README.md
├── your_addon/
│   ├── __init__.py
│   ├── apps.py
│   └── your_imp.py (your AddonImp implementation)
```

### 2. Implement Your Django App Config

Create `apps.py` with a class that inherits from `ForeignAddonConfig`:

```python
from addon_toolkit.interfaces.foreign_addon_config import ForeignAddonConfig
from .your_imp import YourServiceImp

class YourAddonConfig(ForeignAddonConfig):
    name = "your_addon_package.your_addon"

    @property
    def imp(self):
        """Return your AddonImp implementation class."""
        return YourServiceImp

    @property
    def addon_name(self):
        """Return the unique name for your addon.

        IMPORTANT: This name MUST be unique across all addons in any
        gravyvalet installation. Users will reference this name in their
        ADDON_APPS configuration.
        """
        return "YOUR_ADDON_APP_NAME"
```

### 3. Implement Your AddonImp

Create your AddonImp implementation based on the type of service:

```python
from addon_toolkit.imp import AddonImp
from addon_toolkit.imp_subclasses.storage import StorageAddonImp

class YourServiceImp(StorageAddonImp):
    # Implement required methods and properties
    # See addon_toolkit documentation for details
    pass
```

The modules under the `addon_imps` package are good examples to
implement this part.

### 4. Choose a Unique Addon Name and Document the name

**CRITICAL**: Your `addon_name` must be unique to avoid conflicts.

Before choosing a name, check built-in addon namesin
`addon_service.common.known_imps.KnownAddonImps` and avoid to use the
names enumerated.

Document the name clearly so users know exactly what to use. Since users
can use the package name of the addon application instaed of
`addon_name` value, document the package name too is a good manner.
