"""SettingsビューCheck列ヘッダー用マスターチェックボックス"""
from .qt_compat import QtCore, QtGui, QtWidgets


class CheckBoxHeaderView(QtWidgets.QHeaderView):
    """指定列ヘッダーにマスターチェックボックスを表示するQHeaderView"""

    masterClicked = QtCore.Signal()

    def __init__(self, check_column=0, parent=None):
        super(CheckBoxHeaderView, self).__init__(QtCore.Qt.Horizontal, parent)
        self._check_column = check_column
        self._check_state = QtCore.Qt.Unchecked
        self._updating = False

    def set_master_check_state(self, all_enabled, any_enabled):
        """行の有効状態に合わせてマスターチェックの表示を更新する"""
        if not any_enabled:
            state = QtCore.Qt.Unchecked
        elif all_enabled:
            state = QtCore.Qt.Checked
        else:
            state = QtCore.Qt.PartiallyChecked

        if self._check_state == state:
            return

        self._updating = True
        try:
            self._check_state = state
            self.viewport().update()
        finally:
            self._updating = False

    def paintSection(self, painter, rect, logical_index):
        painter.save()
        super(CheckBoxHeaderView, self).paintSection(painter, rect, logical_index)
        painter.restore()

        if logical_index != self._check_column:
            return

        option = QtWidgets.QStyleOptionButton()
        option.rect = self._checkbox_rect(rect)
        option.state = QtWidgets.QStyle.State_Enabled
        if self._check_state == QtCore.Qt.Checked:
            option.state |= QtWidgets.QStyle.State_On
        elif self._check_state == QtCore.Qt.PartiallyChecked:
            option.state |= QtWidgets.QStyle.State_NoChange
        else:
            option.state |= QtWidgets.QStyle.State_Off

        QtWidgets.QApplication.style().drawControl(
            QtWidgets.QStyle.CE_CheckBox,
            option,
            painter,
        )

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            index = self.logicalIndexAt(event.pos())
            if index == self._check_column:
                section_pos = self.sectionViewportPosition(index)
                section_size = self.sectionSize(index)
                section_rect = QtCore.QRect(
                    section_pos,
                    0,
                    section_size,
                    self.height(),
                )
                if self._checkbox_rect(section_rect).contains(event.pos()):
                    if not self._updating:
                        self.masterClicked.emit()
                    return
        super(CheckBoxHeaderView, self).mousePressEvent(event)

    def _checkbox_rect(self, section_rect):
        style = QtWidgets.QApplication.style()
        indicator_width = style.pixelMetric(
            QtWidgets.QStyle.PM_IndicatorWidth,
            None,
            self,
        )
        indicator_height = style.pixelMetric(
            QtWidgets.QStyle.PM_IndicatorHeight,
            None,
            self,
        )
        x = section_rect.x() + (
            (section_rect.width() - indicator_width) // 2
        )
        y = section_rect.y() + (
            (section_rect.height() - indicator_height) // 2
        )
        return QtCore.QRect(x, y, indicator_width, indicator_height)
