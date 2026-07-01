"""defQA - Deformation QA Animation Generator"""

__author__ = "zebraed"
__status__ = "stable"
__license__ = "MIT"
__copyright__ = "Copyright 2026 zebraed"
__version__ = "1.0.0"


from .run import generate, delete
from .core.template_loader import list_presets, get_preset_path, list_overrides, get_override_path
from .ui import showUI


def Reload():
    """
    Reload all the modules.
    """
    import sys
    for k in list(sys.modules):
        if k.startswith(__name__):
            del sys.modules[k]
    print(__name__ + " Reloaded.")


__all__ = [
    "generate",
    "delete",
    "list_presets",
    "get_preset_path",
    "list_overrides",
    "get_override_path",
    "showUI",
    "Reload",
]
