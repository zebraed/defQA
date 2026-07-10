"""メッセージ付きビューコンテナ"""
from .qt_compat import QtWidgets, QtCore, QtGui


class EmptyStateView(QtWidgets.QWidget):
    """子ビューの上にメッセージを中央表示する"""

    def __init__(self, view, message, parent=None):
        super().__init__(parent)
        self._view = view
        self._view.setParent(self)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._view)

        self._overlay = QtWidgets.QLabel(message, self)
        self._overlay.setObjectName("controller_empty_overlay")
        self._overlay.setAlignment(QtCore.Qt.AlignCenter)
        self._overlay.setWordWrap(True)
        self._overlay.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        self._apply_overlay_style()
        self._overlay.hide()

    def _apply_overlay_style(self):
        palette = QtWidgets.QApplication.palette()
        text_color = palette.color(
            QtGui.QPalette.Disabled,
            QtGui.QPalette.Text,
        )
        base_color = palette.color(QtGui.QPalette.Base)
        self._overlay.setStyleSheet(
            "color: {text};"
            "background-color: {base};"
            "padding: 16px;".format(
                text=text_color.name(),
                base=base_color.name(),
            )
        )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._overlay.setGeometry(self.rect())

    def set_empty_visible(self, visible):
        self._overlay.setVisible(visible)
