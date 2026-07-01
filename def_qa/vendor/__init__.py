"""Third-party vendored libraries for Maya environments.

PyYAML and Qt.py are bundled for environments where they are not installed.
"""

import os
import sys

_VENDOR_DIR = os.path.dirname(os.path.abspath(__file__))


def _add_vendor_to_path():
    if _VENDOR_DIR not in sys.path:
        sys.path.insert(0, _VENDOR_DIR)


def get_yaml():
    try:
        import yaml
        return yaml
    except ImportError:
        pass

    _add_vendor_to_path()
    import yaml
    return yaml


def get_qt():
    try:
        import Qt
        return Qt
    except ImportError:
        pass

    _add_vendor_to_path()
    import Qt
    return Qt
