"""PySide6 / PySide2 互換レイヤー"""

from ..vendor import get_qt

_qt = get_qt()
QtWidgets = _qt.QtWidgets
QtCore = _qt.QtCore
QtGui = _qt.QtGui

try:
    from PySide6 import QtUiTools
    from PySide6.QtCore import QByteArray
    from PySide6.QtGui import QAction
    from shiboken6 import wrapInstance
    PYSIDE_VERSION = 6
except ImportError:
    try:
        from PySide2 import QtUiTools
        from PySide2.QtCore import QByteArray
        from PySide2.QtWidgets import QAction
        from shiboken2 import wrapInstance
        PYSIDE_VERSION = 2
    except ImportError as e:
        raise ImportError(
            "Neither PySide6 nor PySide2 could be imported. "
            "Ensure you are running this in a Maya environment "
            "with PySide installed."
        ) from e

__all__ = [
    'QtWidgets',
    'QtCore',
    'QtGui',
    'QtUiTools',
    'QByteArray',
    'QAction',
    'wrapInstance',
    'PYSIDE_VERSION',
]
