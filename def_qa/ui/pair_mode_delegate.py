"""Pair列用QComboBoxデリゲート"""
from .qt_compat import QtWidgets, QtCore

from .attr_table_model import PAIR_MODES, PAIR_MODE_LABELS, normalize_pair_mode


class PairModeDelegate(QtWidgets.QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        combo = QtWidgets.QComboBox(parent)
        for mode in PAIR_MODES:
            label = PAIR_MODE_LABELS.get(mode, mode)
            combo.addItem(label, mode)
        return combo

    def setEditorData(self, editor, index):
        value = normalize_pair_mode(index.model().data(index, QtCore.Qt.EditRole))
        idx = editor.findData(value)
        if idx < 0:
            idx = 0
        editor.setCurrentIndex(idx)

    def setModelData(self, editor, model, index):
        value = editor.currentData()
        if value is None:
            value = editor.currentText()
        model.setData(index, value, QtCore.Qt.EditRole)

    def displayText(self, value, locale):
        mode = normalize_pair_mode(value)
        return PAIR_MODE_LABELS.get(mode, mode)
