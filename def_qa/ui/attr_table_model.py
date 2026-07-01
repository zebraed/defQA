"""アトリビュートテーブル表示用 QAbstractTableModel"""
from .qt_compat import QtCore
from .models import AttrItem


_HEADERS = ["", "Part", "Side", "Attr", "Values", "Pair"]
_COL_ENABLED = 0
_COL_PART = 1
_COL_SIDE = 2
_COL_ATTR = 3
_COL_VALUES = 4
_COL_PAIR = 5
COL_PAIR = _COL_PAIR

PAIR_MODES = ("single", "pair_mirror", "pair_same", "pair_offset")

PAIR_MODE_LABELS = {
    "single": "single",
    "pair_mirror": "mirror",
    "pair_same": "same",
    "pair_offset": "offset",
}

_PAIR_MODE_ALIASES = {
    "mirror": "pair_mirror",
    "same": "pair_same",
    "offset": "pair_offset",
}


def normalize_pair_mode(value):
    text = str(value).strip()
    if text in PAIR_MODES:
        return text
    alias = _PAIR_MODE_ALIASES.get(text)
    if alias:
        return alias
    return "single"


class AttrTableModel(QtCore.QAbstractTableModel):
    """
    AttrItemリストをQTableViewに表示するモデル。
    カラム: Check, Part, Side, Attr, Values, Pair
    """

    attrs_reset = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items: list = []

    def set_attrs(self, items):
        self.beginResetModel()
        self._items = list(items)
        self.endResetModel()
        self.attrs_reset.emit()

    def get_attrs(self):
        return list(self._items)

    def get_enabled_summary(self):
        if not self._items:
            return False, False

        all_enabled = True
        any_enabled = False
        for item in self._items:
            if item.enabled:
                any_enabled = True
            else:
                all_enabled = False
        return all_enabled, any_enabled

    def set_all_enabled(self, enabled):
        if not self._items:
            return

        changed = False
        for item in self._items:
            if item.enabled != enabled:
                item.enabled = enabled
                changed = True

        if changed:
            self.notify_check_states_changed()

    def toggle_all_enabled(self):
        all_enabled, _any_enabled = self.get_enabled_summary()
        self.set_all_enabled(not all_enabled)

    def notify_check_states_changed(self):
        if not self._items:
            return
        top_left = self.index(0, _COL_ENABLED)
        bottom_right = self.index(len(self._items) - 1, _COL_ENABLED)
        self.dataChanged.emit(top_left, bottom_right, [QtCore.Qt.CheckStateRole])

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self._items)

    def columnCount(self, parent=QtCore.QModelIndex()):
        return len(_HEADERS)

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid():
            return None
        item = self._items[index.row()]
        col = index.column()

        if col == _COL_ENABLED:
            if role == QtCore.Qt.CheckStateRole:
                return QtCore.Qt.Checked if item.enabled else QtCore.Qt.Unchecked
            return None

        if col == _COL_PART:
            if role == QtCore.Qt.DisplayRole:
                return item.part
            if role == QtCore.Qt.EditRole:
                return item.part
            return None

        if col == _COL_SIDE:
            if role == QtCore.Qt.DisplayRole:
                return item.side
            if role == QtCore.Qt.EditRole:
                return item.side
            return None

        if col == _COL_ATTR:
            if role == QtCore.Qt.DisplayRole:
                return item.attr
            return None

        if col == _COL_VALUES:
            if role in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole):
                return ", ".join(
                    str(int(v) if v == int(v) else v) for v in item.values
                )
            return None

        if col == _COL_PAIR:
            if role == QtCore.Qt.DisplayRole:
                return PAIR_MODE_LABELS.get(
                    normalize_pair_mode(item.pair_mode),
                    item.pair_mode,
                )
            if role == QtCore.Qt.EditRole:
                return normalize_pair_mode(item.pair_mode)
            return None

        return None

    def setData(self, index, value, role=QtCore.Qt.EditRole):
        if not index.isValid():
            return False
        item = self._items[index.row()]
        col = index.column()

        if col == _COL_ENABLED and role == QtCore.Qt.CheckStateRole:
            item.enabled = _is_checked(value)
            self.dataChanged.emit(index, index, [role])
            return True

        if col == _COL_VALUES and role == QtCore.Qt.EditRole:
            try:
                vals = [float(v.strip()) for v in value.split(",") if v.strip()]
                if vals:
                    item.values = vals
                    self.dataChanged.emit(index, index, [role])
                    return True
            except ValueError:
                pass
            return False

        if col == _COL_PART and role == QtCore.Qt.EditRole:
            item.part = str(value).strip()
            self.dataChanged.emit(index, index, [role])
            return True

        if col == _COL_SIDE and role == QtCore.Qt.EditRole:
            item.side = str(value).strip()
            self.dataChanged.emit(index, index, [role])
            return True

        if col == _COL_PAIR and role == QtCore.Qt.EditRole:
            item.pair_mode = normalize_pair_mode(value)
            self.dataChanged.emit(index, index, [role])
            return True

        return False

    def flags(self, index):
        if not index.isValid():
            return QtCore.Qt.NoItemFlags
        col = index.column()
        base = QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
        if col == _COL_ENABLED:
            return base | QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEditable
        if col in (_COL_PART, _COL_SIDE, _COL_VALUES, _COL_PAIR):
            return base | QtCore.Qt.ItemIsEditable
        return base

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            return _HEADERS[section]
        return None


def _is_checked(value):
    if value == QtCore.Qt.Checked:
        return True

    raw_value = getattr(value, "value", value)
    checked_value = getattr(QtCore.Qt.Checked, "value", QtCore.Qt.Checked)

    try:
        return int(raw_value) == int(checked_value)
    except (TypeError, ValueError):
        return False
