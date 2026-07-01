"""コントローラーリスト表示用 QStandardItemModel"""
import os
import re

from maya import cmds
from .qt_compat import QtCore, QtGui, QtWidgets


_ICON_DIR = os.path.join(os.path.dirname(__file__), "icons")
_ICON_CACHE = {}


def _palette_text_color(disabled):
    """テーマの有効/無効テキスト色を返す"""
    palette = QtWidgets.QApplication.palette()
    group = QtGui.QPalette.Disabled if disabled else QtGui.QPalette.Active
    return palette.color(group, QtGui.QPalette.Text)


class ControllerTreeModel(QtGui.QStandardItemModel):
    """
    ControllerItemをDAG親子関係に沿ってQTreeViewに表示するモデル。
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items: list = []
        self._item_by_node = {}
        self.setHorizontalHeaderLabels(["Controller"])

    def set_controllers(self, items):
        """表示するControllerItemリストをDAG階層でセットする"""
        self.clear()
        self.setHorizontalHeaderLabels(["Controller"])
        self._items = list(items)
        self._item_by_node = {}

        node_set = {ctrl_item.node for ctrl_item in self._items}
        children_by_parent = {}

        for ctrl_item in self._items:
            parent_node = _find_parent_node(ctrl_item.node, node_set)
            if parent_node not in children_by_parent:
                children_by_parent[parent_node] = []
            children_by_parent[parent_node].append(ctrl_item)

        for siblings in children_by_parent.values():
            siblings.sort(key=lambda item: _natural_sort_key(_short_name(item.node)))

        root_item = self.invisibleRootItem()
        self._append_children(root_item, None, children_by_parent)

    def _append_children(self, parent_item, parent_node, children_by_parent):
        """親ノード配下の子を自然順で追加する"""
        siblings = children_by_parent.get(parent_node, [])
        for ctrl_item in siblings:
            item = QtGui.QStandardItem(_short_name(ctrl_item.node))
            item.setEditable(False)
            item.setData(ctrl_item, QtCore.Qt.UserRole)
            self._apply_item_appearance(item, ctrl_item)
            parent_item.appendRow(item)
            self._item_by_node[ctrl_item.node] = item
            self._append_children(item, ctrl_item.node, children_by_parent)

    def get_controllers(self):
        """全ControllerItemを返す"""
        return list(self._items)

    def get_item_from_index(self, index):
        """QModelIndexからControllerItemを返す"""
        if not index.isValid():
            return None
        item = self.itemFromIndex(index)
        if item is None:
            return None
        return item.data(QtCore.Qt.UserRole)

    def get_index_by_node(self, node):
        """ノード名からQModelIndexを返す"""
        item = self._item_by_node.get(node)
        if item is None:
            return QtCore.QModelIndex()
        return item.index()

    def refresh_controller_appearance(self, ctrl_item):
        """コントローラー1件の有効状態表示を更新する"""
        standard_item = self._item_by_node.get(ctrl_item.node)
        if standard_item is None:
            return
        self._apply_item_appearance(standard_item, ctrl_item)

    def refresh_all_appearances(self):
        """全コントローラーの有効状態表示を更新する"""
        for ctrl_item in self._items:
            self.refresh_controller_appearance(ctrl_item)

    def _apply_item_appearance(self, standard_item, ctrl_item):
        """Mute状態とノード種別に応じた表示を更新する"""
        standard_item.setEnabled(True)
        standard_item.setForeground(_palette_text_color(ctrl_item.muted))
        standard_item.setIcon(_controller_icon(ctrl_item.node))


def _controller_icon(node):
    """コントローラーノード種別に応じたアイコンを返す"""
    icon_name = _controller_icon_name(node)
    cached = _ICON_CACHE.get(icon_name)
    if cached is not None:
        return cached
    if icon_name.startswith(":/"):
        icon = QtGui.QIcon(icon_name)
    else:
        path = os.path.join(_ICON_DIR, f"{icon_name}.svg")
        if os.path.isfile(path):
            icon = QtGui.QIcon(path)
        else:
            icon = QtGui.QIcon()

    _ICON_CACHE[icon_name] = icon
    return icon


def _controller_icon_name(node):
    """nurbsCurveシェイプの有無でアイコン名を決める"""
    if not cmds.objExists(node):
        return ":/transform"

    shapes = cmds.listRelatives(node, shapes=True, noIntermediate=True)
    if not shapes:
        return ":/transform"

    for shape in shapes:
        if cmds.nodeType(shape) == "nurbsCurve":
            return "nurbsCurve"

    return ":/transform"


def _short_name(node):
    """DAGパスを除いた表示名を返す"""
    return node.split("|")[-1]


def _natural_sort_key(text):
    """自然順ソート用キー。数値部分を整数として比較する"""
    parts = re.split(r"(\d+)", text)
    key = []
    for part in parts:
        if part.isdigit():
            key.append(int(part))
        else:
            key.append(part.lower())
    return key


def _find_parent_node(node, node_set):
    """セット内に存在するDAG上の親を探す"""
    parts = [part for part in node.split("|") if part]
    for i in range(len(parts) - 1, 0, -1):
        parent_path = "|" + "|".join(parts[:i])
        if parent_path in node_set:
            return parent_path
    return None
