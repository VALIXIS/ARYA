"""
tools/__init__.py
-----------------
Importing this package registers all tools into the shared registry.

Simply do:
    from app.tools import registry          # registry is populated
    from app.tools.tool_registry import registry  # same object

The order of imports here controls registration order (cosmetic only).
"""

from .tool_registry import registry          # noqa: F401  — re-export

# Importing each module triggers its top-level registry.register() calls.
from . import browser_tools   # noqa: F401
from . import app_tools       # noqa: F401
from . import file_tools      # noqa: F401
from . import system_tools    # noqa: F401
from . import media_tools     # noqa: F401
from . import device_tools    # noqa: F401
from . import smarthome_tools # noqa: F401
from . import mobile_tools    # noqa: F401
from . import weather_tools   # noqa: F401
from . import execute_tools   # noqa: F401
from . import scheduler_tools # noqa: F401

