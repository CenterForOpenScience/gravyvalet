# Foreign Addon Development Guide

This guide explains how to develop Foreign Addons for gravyvalet, allowing you to create custom integrations that can be distributed as standalone Python packages.

## Overview

Foreign Addons are Django apps that extend gravyvalet's functionality by implementing new external service integrations. They can be developed independently and distributed as regular Python packages.

## Requirements

- Python 3.9+
- Django 4.2+
- gravyvalet

## Development Steps

### Create Your Package Structure

Create a standard Python package structure:

```
your_addon_package/
├── setup.py
├── README.md
├── your_addon_app/
│   ├── __init__.py
│   ├── apps.py
│   ├── your_imp.py # your AddonImp implementation
│   └── static/
│       └── {AppConfig.name}/    # typically, `your_addon_package.your_addon_app`
│           └── icons/      # Place your addon's icon files here
│               └── your_icon.svg
```

A foreign addon package can include multiple foreign addons. To do so,
just include multiple Django apps that behave as foreign addons.

### Implement Your Django App Config

Create `apps.py` with a class that inherits from `ForeignAddonConfig`:

```python
from addon_toolkit.interfaces.foreign_addon_config import ForeignAddonConfig
from .your_imp import YourServiceImp

class YourAddonConfig(ForeignAddonConfig):
    name = "your_addon_package.your_addon_app"

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

### Implement Your AddonImp

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

### Choose a Unique Addon Name and Document the name

**CRITICAL**: Your `addon_name` must be unique to avoid conflicts.

Before choosing a name, check built-in addon namesin
`addon_service.common.known_imps.KnownAddonImps` and avoid to use the
names enumerated.

Document the name clearly so users know exactly what to use. Since users
can use the package name of the addon application instaed of
`addon_name` value, document the package name too is a good manner.

### Adding Icons for Your Addon

Foreign addons can provide custom icons that will be available in the gravyvalet admin interface.

#### Icon Directory Convention

Place your icon files in the `static/{AppConfig.name}/icons/` directory within your addon app:

```
your_addon_app/
├── static/
│   └── {AppConfig.name}    # typically, your_addon_package.your_addon_app/
│       └── icons/
│           ├── your_service.svg
│           ├── your_service.png
│           └── your_service_alt.jpg
```

#### Supported Formats

- SVG (recommended for scalability)
- PNG
- JPG/JPEG

### Package and Distribute

Create a `setup.py` for your package:

```python
from setuptools import setup, find_packages

setup(
    name="your-addon-package",
    version="1.0.0",
    packages=find_packages(),
    include_package_data=True,  # Important for including static files
    install_requires=[
        "django>=4.2",
    ],
    package_data={
        'your_addon_app': [
            'static/your_addon_package.your_addon_app/icons/*',  # Include icon files
        ],
    },
)
```

## Installation and Usage

Users can install and use your foreign addon by:

1. Installing your package:
```bash
pip install your-addon-package
```

2. Adding it to Django's `INSTALLED_APPS`:
```python
INSTALLED_APPS = [
    # ... other apps
    "your_addon_package.your_addon_app",
]
```

3. Registering it in gravyvalet's `ADDON_APPS`:
```python
ADDON_APPS = {
    # ... other addons
    "YOUR_ADDON_APP_NAME": 5000,  # Use a unique ID >= 5000
}
```
