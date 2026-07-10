"""defQA メインウィンドウ"""
import copy
import json
import os
import platform
import subprocess
import sys
import webbrowser
from typing import Optional

from maya import cmds
from maya.app.general.mayaMixin import MayaQWidgetBaseMixin
from maya import OpenMaya as om
from maya import OpenMayaUI as omui

from .qt_compat import QtWidgets, QtCore, QtGui, QtUiTools, wrapInstance, QAction
from ..core.scanner import scan_controller_set
from ..core.template_loader import load_preset, get_preset_path, get_override_path
from ..core.preset_builder import build_parts_from_controllers, is_controller_muted
from ..core.animation_layer import setup_generation_layer
from ..core.animation_builder import (
    capture_initial_values,
    restore_initial_values,
    build_animation,
    delete_generated_keys,
    restore_pose_from_metadata,
    get_test_values,
    expand_targets_for_pairs,
)
from ..core.bookmark import create_bookmarks_from_targets, delete_defqa_bookmarks
from ..core.metadata import (
    load_metadata,
    clear_metadata,
    get_generation_start_frame,
    record_generation,
)
from ..utils.name_match import match_any_pattern
from .models import ControllerItem, AttrItem
from .controller_tree_model import ControllerTreeModel
from .attr_table_model import AttrTableModel, COL_PAIR
from .check_box_header import CheckBoxHeaderView
from .pair_mode_delegate import PairModeDelegate
from .empty_state_view import EmptyStateView


DIR_NAME = os.path.dirname(__file__)
_REPO_ROOT = os.path.abspath(os.path.join(DIR_NAME, "..", ".."))


class DefQAMainWindow(MayaQWidgetBaseMixin, QtWidgets.QMainWindow):
    """defQA メインウィンドウ"""

    object_name = "defQA_MainWindow"
    singleton_key = None
    optionvar_key = "defQA_MainWindow_settings"
    icon_dir = None
    window_icon = "defqa_icon.svg"
    docs_dir = _REPO_ROOT
    quickstart_doc_file = "README.md"
    web_doc_file = None

    def __init__(self):
        maya_main_window_ptr = omui.MQtUtil.mainWindow()
        maya_main_window = wrapInstance(
            int(maya_main_window_ptr),
            QtWidgets.QWidget,
        )

        super().__init__(maya_main_window)

        self._close_other_instances()

        self.setObjectName(self.object_name)
        self.setWindowTitle("DefQA")
        self._set_window_icon()
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        self.qtui: Optional[QtWidgets.QWidget] = None
        self.line_preset: Optional[QtWidgets.QLineEdit] = None
        self.line_override: Optional[QtWidgets.QLineEdit] = None
        self.btn_open_preset: Optional[QtWidgets.QPushButton] = None
        self.line_ctrl_set: Optional[QtWidgets.QLineEdit] = None
        self.btn_set_ctrl_set: Optional[QtWidgets.QPushButton] = None
        self.btn_scan: Optional[QtWidgets.QPushButton] = None
        self.splitter: Optional[QtWidgets.QSplitter] = None
        self.tree_controllers: Optional[QtWidgets.QTreeView] = None
        self._controller_view: Optional[EmptyStateView] = None
        self.table_attrs: Optional[QtWidgets.QTableView] = None
        self._attr_header: Optional[CheckBoxHeaderView] = None
        self.chk_rotate: Optional[QtWidgets.QCheckBox] = None
        self.chk_translate: Optional[QtWidgets.QCheckBox] = None
        self.chk_scale: Optional[QtWidgets.QCheckBox] = None
        self.chk_use_anim_layer: Optional[QtWidgets.QCheckBox] = None
        self.chk_return_neutral: Optional[QtWidgets.QCheckBox] = None
        self.chk_bookmarks: Optional[QtWidgets.QCheckBox] = None
        self.radio_selected: Optional[QtWidgets.QRadioButton] = None
        self.radio_all: Optional[QtWidgets.QRadioButton] = None
        self.btn_generate: Optional[QtWidgets.QPushButton] = None
        self.btn_delete: Optional[QtWidgets.QPushButton] = None

        self._menu_bar = None
        self._ctrl_model = ControllerTreeModel()
        self._attr_model = AttrTableModel()
        self._syncing_selection = False
        self._selection_callback_id = None
        self._timeline_overrides = {}
        self._preset_cache = None
        self._factory_settings = {}
        self._geometry_snapshot_for_save = None
        self._splitter_initialized = False

        self._setup_ui()
        self._setup_signals()

        try:
            self._factory_settings = self._gather_settings_from_ui()
        except Exception:
            self._factory_settings = {}
        try:
            self._load_settings()
        except Exception:
            pass

        self._auto_scan_if_ready()
        self._start_selection_watcher()
        self._update_delete_button_state()

    def _close_other_instances(self):
        """他のインスタンスを閉じる"""
        singleton_key = self._get_singleton_key()
        for q_window in self.parent().findChildren(QtWidgets.QMainWindow):
            if q_window is self:
                continue
            if q_window.objectName() == singleton_key:
                q_window.close()

    def _get_singleton_key(self) -> str:
        """シングルトン判定キーを返す"""
        return (
            getattr(self.__class__, "singleton_key", None)
            or self.object_name
        )

    # --- UI setup ---

    def _get_icon_dir(self) -> str:
        """ウィンドウアイコンのディレクトリを返す"""
        return getattr(self.__class__, "icon_dir", None) or os.path.join(
            DIR_NAME,
            "icons",
        )

    def _get_window_icon_path(self) -> Optional[str]:
        """ウィンドウアイコンのファイルパスを解決する"""
        icon_file = getattr(self.__class__, "window_icon", "defqa_icon.svg")
        if not icon_file:
            return None
        if os.path.isabs(icon_file) and os.path.isfile(icon_file):
            return icon_file
        icon_dir = self._get_icon_dir()
        path = os.path.join(icon_dir, icon_file)
        if os.path.isfile(path):
            return path
        base, ext = os.path.splitext(icon_file)
        if not ext:
            for suffix in (".svg", ".png", ".ico"):
                candidate = path + suffix
                if os.path.isfile(candidate):
                    return candidate
        return None

    def _set_window_icon(self) -> None:
        """ウィンドウアイコンを設定する"""
        path = self._get_window_icon_path()
        if path:
            self.setWindowIcon(QtGui.QIcon(path))

    def _setup_ui(self):
        loader = QtUiTools.QUiLoader()
        ui_path = os.path.join(DIR_NAME, "gui_main.ui")
        qfile = QtCore.QFile(ui_path)
        qfile.open(QtCore.QFile.ReadOnly)
        self.qtui = loader.load(qfile, self)
        qfile.close()

        self.line_preset = self.qtui.findChild(QtWidgets.QLineEdit, "line_preset")
        self.line_override = self.qtui.findChild(QtWidgets.QLineEdit, "line_override")
        self.btn_open_preset = self.qtui.findChild(QtWidgets.QPushButton, "btn_open_preset")
        self.line_ctrl_set = self.qtui.findChild(QtWidgets.QLineEdit, "line_ctrl_set")
        self.btn_set_ctrl_set = self.qtui.findChild(QtWidgets.QPushButton, "btn_set_ctrl_set")
        self.btn_scan = self.qtui.findChild(QtWidgets.QPushButton, "btn_scan")
        self.splitter = self.qtui.findChild(QtWidgets.QSplitter, "splitter")
        if self.splitter is not None:
            self.splitter.setStretchFactor(0, 1)
            self.splitter.setStretchFactor(1, 1)
        self.tree_controllers = self.qtui.findChild(QtWidgets.QTreeView, "tree_controllers")
        self.table_attrs = self.qtui.findChild(QtWidgets.QTableView, "table_attrs")
        self.chk_rotate = self.qtui.findChild(QtWidgets.QCheckBox, "chk_rotate")
        self.chk_translate = self.qtui.findChild(QtWidgets.QCheckBox, "chk_translate")
        self.chk_scale = self.qtui.findChild(QtWidgets.QCheckBox, "chk_scale")
        self.chk_use_anim_layer = self.qtui.findChild(QtWidgets.QCheckBox, "chk_use_anim_layer")
        self.chk_return_neutral = self.qtui.findChild(QtWidgets.QCheckBox, "chk_return_neutral")
        self.chk_bookmarks = self.qtui.findChild(QtWidgets.QCheckBox, "chk_bookmarks")
        self.radio_selected = self.qtui.findChild(QtWidgets.QRadioButton, "radio_selected")
        self.radio_all = self.qtui.findChild(QtWidgets.QRadioButton, "radio_all")
        self.btn_generate = self.qtui.findChild(QtWidgets.QPushButton, "btn_generate")
        self.btn_delete = self.qtui.findChild(QtWidgets.QPushButton, "btn_delete")

        self.tree_controllers.setModel(self._ctrl_model)
        self.tree_controllers.setIconSize(QtCore.QSize(16, 16))
        self.tree_controllers.setIndentation(12)
        self.tree_controllers.header().hide()
        self.tree_controllers.header().setSectionResizeMode(
            QtWidgets.QHeaderView.Stretch
        )

        if self.splitter is not None:
            splitter_index = self.splitter.indexOf(self.tree_controllers)
            self.tree_controllers.setParent(None)
            self._controller_view = EmptyStateView(
                self.tree_controllers,
                (
                    "No controllers loaded.\n"
                    "Enter a controller set and click Scan to get started."
                ),
            )
            self.splitter.insertWidget(splitter_index, self._controller_view)
        self._update_controller_empty_state()

        hh = CheckBoxHeaderView(check_column=0, parent=self.table_attrs)
        self._attr_header = hh
        self.table_attrs.setHorizontalHeader(hh)
        self.table_attrs.setModel(self._attr_model)
        self.table_attrs.setItemDelegateForColumn(COL_PAIR, PairModeDelegate(self.table_attrs))
        hh.setMinimumSectionSize(24)
        hh.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(4, QtWidgets.QHeaderView.Stretch)
        hh.setSectionResizeMode(5, QtWidgets.QHeaderView.ResizeToContents)
        self.table_attrs.verticalHeader().setVisible(False)

        central = QtWidgets.QWidget(self)
        layout = QtWidgets.QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        self.create_menu_bar(layout)
        layout.addWidget(self.qtui)
        self.setCentralWidget(central)

        self._apply_qss()

    def _update_controller_empty_state(self):
        """Controller Viewの空状態オーバーレイ表示を更新する"""
        if self._controller_view is None:
            return
        empty = not self._ctrl_model.get_controllers()
        self._controller_view.set_empty_visible(empty)

    def create_menu_bar(self, root_layout: QtWidgets.QBoxLayout) -> None:
        menubar = QtWidgets.QMenuBar(self)

        preset_menu = menubar.addMenu("Preset")
        act_preset = QAction("Open Preset Dialog...", self)
        act_preset.triggered.connect(self._on_open_preset_dialog)
        preset_menu.addAction(act_preset)

        edit_menu = menubar.addMenu("Edit")
        act_save_settings = QAction("Save Settings", self)
        act_save_settings.triggered.connect(self._on_menu_save_settings)
        edit_menu.addAction(act_save_settings)

        act_reset_settings = QAction("Reset Settings", self)
        act_reset_settings.triggered.connect(self._on_menu_reset_settings)
        edit_menu.addAction(act_reset_settings)

        help_menu = menubar.addMenu("Help")
        if self.quickstart_doc_file:
            act_help = QAction("Open Quick Start Document", self)
            act_help.triggered.connect(self._open_document)
            help_menu.addAction(act_help)

        if self.quickstart_doc_file and self.web_doc_file:
            help_menu.addSeparator()

        if self.web_doc_file:
            act_doc = QAction("Web Documentation", self)
            act_doc.triggered.connect(self._open_web_document)
            help_menu.addAction(act_doc)

        if self.quickstart_doc_file or self.web_doc_file:
            help_menu.addSeparator()

        act_about = QAction("About...", self)
        act_about.triggered.connect(self._show_about_dialog)
        help_menu.addAction(act_about)

        if hasattr(self, "setMenuBar"):
            self.setMenuBar(menubar)
        else:
            menubar.setMinimumHeight(22)
            root_layout.insertWidget(0, menubar)
        self._menu_bar = menubar

    def _apply_qss(self):
        qss_path = os.path.join(DIR_NAME, "gui_main.qss")
        if os.path.isfile(qss_path):
            with open(qss_path, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())

    def _setup_signals(self):
        self.btn_scan.clicked.connect(lambda *_args: self._on_scan())
        self.btn_set_ctrl_set.clicked.connect(self._on_set_controller_set_from_selection)
        self.btn_open_preset.clicked.connect(self._on_open_preset_dialog)
        self.btn_generate.clicked.connect(self._on_generate)
        self.btn_delete.clicked.connect(self._on_delete)
        self.chk_rotate.toggled.connect(self._on_attr_filter_changed)
        self.chk_translate.toggled.connect(self._on_attr_filter_changed)
        self.chk_scale.toggled.connect(self._on_attr_filter_changed)

        self._attr_header.masterClicked.connect(self._on_attr_master_checkbox_clicked)
        self._attr_model.attrs_reset.connect(self._sync_attr_master_checkbox)
        self._attr_model.dataChanged.connect(self._on_attr_table_data_changed)

        self.tree_controllers.selectionModel().currentChanged.connect(
            self._on_controller_selected
        )
        self.tree_controllers.selectionModel().selectionChanged.connect(
            self._on_controller_selection_changed
        )

        self.tree_controllers.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.tree_controllers.customContextMenuRequested.connect(
            self._on_controller_context_menu
        )

    def _on_controller_context_menu(self, pos):
        """Controller Viewの右クリックメニュー"""
        index = self.tree_controllers.indexAt(pos)
        item_at_pos = self._ctrl_model.get_item_from_index(index)
        selected = self._selected_controller_items()
        if item_at_pos is not None and item_at_pos not in selected:
            selected = [item_at_pos]

        has_muted = any(
            item.muted for item in self._ctrl_model.get_controllers()
        )

        menu = QtWidgets.QMenu(self.tree_controllers)

        act_mute = menu.addAction("Mute")
        act_mute.setEnabled(bool(selected))
        act_mute.triggered.connect(
            lambda *_args: self._set_controllers_muted(selected, True)
        )

        act_unmute = menu.addAction("Unmute")
        act_unmute.setEnabled(bool(selected))
        act_unmute.triggered.connect(
            lambda *_args: self._set_controllers_muted(selected, False)
        )

        menu.addSeparator()

        act_unmute_all = menu.addAction("Unmute All")
        act_unmute_all.setEnabled(has_muted)
        act_unmute_all.triggered.connect(self._unmute_all_controllers)

        menu.exec_(self.tree_controllers.viewport().mapToGlobal(pos))

    def _set_controllers_muted(self, ctrl_items, muted):
        """選択コントローラーのMute状態を変更する"""
        for ctrl_item in ctrl_items:
            ctrl_item.muted = muted
            self._ctrl_model.refresh_controller_appearance(ctrl_item)

    def _unmute_all_controllers(self):
        """全コントローラーのMuteを解除する"""
        for ctrl_item in self._ctrl_model.get_controllers():
            ctrl_item.muted = False
        self._ctrl_model.refresh_all_appearances()

    # --- handlers ---

    def _auto_scan_if_ready(self):
        """保存済みController Setがシーンにあれば起動時に自動Scanする"""
        if self.line_ctrl_set is None:
            return
        set_name = self.line_ctrl_set.text().strip()
        if not set_name:
            return
        if not cmds.objExists(set_name):
            return
        if cmds.nodeType(set_name) != "objectSet":
            return
        self._on_scan(silent=True)

    def _on_set_controller_set_from_selection(self):
        """Maya選択中のobjectSet名をController Set欄へ設定する"""
        selected = cmds.ls(selection=True)
        object_sets = [
            node for node in selected
            if cmds.nodeType(node) == "objectSet"
        ]
        if not object_sets:
            cmds.warning("defQA: Please select an objectSet")
            return

        set_name = object_sets[0]
        if len(object_sets) > 1:
            cmds.warning(
                f"defQA: Multiple objectSets are selected. Using the first set: {set_name}"
            )

        self.line_ctrl_set.setText(set_name)

    def _on_scan(self, silent=False):
        set_name = self.line_ctrl_set.text().strip()
        if not set_name:
            if not silent:
                cmds.warning("defQA: Please enter a Controller Set name")
            return

        preset = self._load_current_preset()

        try:
            targets = scan_controller_set(
                set_name,
                enable_rotate=self.chk_rotate.isChecked(),
            )
        except ValueError as e:
            if not silent:
                cmds.warning(f"defQA: {e}")
            return

        if not targets:
            if not silent:
                cmds.warning(f"defQA: No targets found: {set_name}")
            return

        previous_mute = {
            item.node: item.muted
            for item in self._ctrl_model.get_controllers()
        }

        ctrl_items = [
            ControllerItem(
                node=node,
                enabled=True,
                muted=previous_mute.get(
                    node,
                    is_controller_muted(node, preset),
                ),
                attrs=[
                    self._build_attr_item(node, attr, preset)
                    for attr in attrs
                ],
            )
            for node, attrs in targets.items()
        ]

        self._ctrl_model.set_controllers(ctrl_items)
        self._update_controller_empty_state()
        self.tree_controllers.expandAll()
        if ctrl_items:
            self.tree_controllers.setCurrentIndex(self._ctrl_model.index(0, 0))

        self._on_attr_filter_changed()
        self._refresh_preset_cache()
        print(f"[defQA] Scanned {len(ctrl_items)} controllers")

    def _build_attr_item(self, node, attr, preset):
        """プリセットからSettingsビュー用のAttrItemを作る"""
        part, side, pair_mode = _get_part_side_pair(node, preset)
        return AttrItem(
            attr=attr,
            enabled=True,
            part=part,
            side=side,
            values=get_test_values(node, attr, preset),
            pair_mode=pair_mode,
        )

    def _on_controller_selected(self, current, _previous):
        item = self._ctrl_model.get_item_from_index(current)
        self._attr_model.set_attrs(item.attrs if item else [])

    def _on_attr_master_checkbox_clicked(self):
        """SettingsビューCheck列ヘッダーのマスターチェック"""
        self._attr_model.toggle_all_enabled()
        self._sync_attr_master_checkbox()

    def _sync_attr_master_checkbox(self):
        """マスターチェックボックスの表示を行の有効状態に同期する"""
        if self._attr_header is None:
            return
        all_enabled, any_enabled = self._attr_model.get_enabled_summary()
        self._attr_header.set_master_check_state(all_enabled, any_enabled)

    def _on_attr_table_data_changed(self, top_left, bottom_right, roles):
        """個別Check変更時にマスターチェック表示を更新する"""
        if not roles:
            return
        if QtCore.Qt.CheckStateRole not in roles:
            return
        if top_left.column() != 0:
            return
        self._sync_attr_master_checkbox()

    def _on_controller_selection_changed(self, _selected, _deselected):
        if self._syncing_selection:
            return

        items = self._selected_controller_items()
        nodes = [item.node for item in items if cmds.objExists(item.node)]
        self._syncing_selection = True
        try:
            if nodes:
                cmds.select(nodes, replace=True)
            else:
                cmds.select(clear=True)
        finally:
            self._syncing_selection = False

    def _on_open_preset_dialog(self):
        from .preset_dialog import PresetDialog
        self._refresh_preset_cache()
        dlg = PresetDialog(
            preset_name=self.line_preset.text().strip(),
            override_name=self.line_override.text().strip(),
            parent=self,
            export_preset=self.export_preset_for_save,
        )
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            self.line_preset.setText(dlg.get_preset_name())
            self.line_override.setText(dlg.get_override_name())
            self._timeline_overrides = dlg.get_timeline_settings()
            if self._ctrl_model.get_controllers():
                preset = self._load_current_preset()
                self._apply_preset_to_controllers(preset)
            self._refresh_preset_cache()

    def export_preset_for_save(self, timeline_settings=None):
        """SettingsビューとUI状態から保存用プリセットdictを組み立てる"""
        preset = self._load_current_preset()
        preset = copy.deepcopy(preset)

        timeline = dict(preset.get("timeline", {}))
        if timeline_settings is not None:
            timeline.update(timeline_settings)
        elif self._timeline_overrides:
            timeline.update(self._timeline_overrides)
        preset["timeline"] = timeline

        options = dict(preset.get("options", {}))
        if self.chk_use_anim_layer is not None:
            options["use_animation_layer"] = bool(self.chk_use_anim_layer.isChecked())
        if self.chk_return_neutral is not None:
            options["return_to_neutral"] = bool(self.chk_return_neutral.isChecked())
        if self.chk_bookmarks is not None:
            options["create_time_slider_bookmarks"] = bool(
                self.chk_bookmarks.isChecked()
            )
        preset["options"] = options

        default_span = timeline.get("default_span", 8)
        base_parts = preset.get("parts", {})
        ctrl_items = self._ctrl_model.get_controllers()
        preset["parts"] = build_parts_from_controllers(
            ctrl_items,
            base_parts,
            default_span,
        )
        return preset

    def _refresh_preset_cache(self):
        """現在のSettingsビュー内容を内部キャッシュへ保存する"""
        try:
            self._preset_cache = self.export_preset_for_save()
        except Exception:
            self._preset_cache = None

    def _apply_preset_to_controllers(self, preset):
        """読み込んだプリセットをControllerItemへ反映する"""
        for ctrl_item in self._ctrl_model.get_controllers():
            ctrl_item.muted = is_controller_muted(ctrl_item.node, preset)
            new_attrs = []
            for attr_item in ctrl_item.attrs:
                part, side, pair_mode = _get_part_side_pair(
                    ctrl_item.node,
                    preset,
                )
                new_attrs.append(AttrItem(
                    attr=attr_item.attr,
                    enabled=attr_item.enabled,
                    part=part,
                    side=side,
                    values=get_test_values(
                        ctrl_item.node,
                        attr_item.attr,
                        preset,
                    ),
                    pair_mode=pair_mode,
                ))
            ctrl_item.attrs = new_attrs

        self._ctrl_model.refresh_all_appearances()

        current = self.tree_controllers.currentIndex()
        if current.isValid():
            self._on_controller_selected(current, QtCore.QModelIndex())

    def _on_attr_filter_changed(self, *_args):
        """AttrsフィルターとSettingsビューのCheck列を連動する"""
        enabled_by_group = {
            "translate": self.chk_translate.isChecked(),
            "rotate": self.chk_rotate.isChecked(),
            "scale": self.chk_scale.isChecked(),
        }

        for ctrl_item in self._ctrl_model.get_controllers():
            for attr_item in ctrl_item.attrs:
                group = _attr_group(attr_item.attr)
                if group not in enabled_by_group:
                    continue
                attr_item.enabled = enabled_by_group[group]

        self._attr_model.notify_check_states_changed()
        self._sync_attr_master_checkbox()

    def _on_generate(self):
        items = self._target_controller_items()
        if not items:
            cmds.warning("defQA: No target controllers")
            return
        self._generate(items)

    def _on_delete(self):
        self._delete()

    def _target_controller_items(self):
        """RadioボタンのTarget設定に応じたControllerItemを返す（Mutedは除外）"""
        if self.radio_all.isChecked():
            items = self._ctrl_model.get_controllers()
        else:
            items = self._selected_controller_items()
        return [item for item in items if not item.muted]

    def _selected_controller_items(self):
        """ツリービューで選択されているControllerItemを重複なしで返す"""
        items = []
        seen_nodes = set()
        for index in self.tree_controllers.selectedIndexes():
            item = self._ctrl_model.get_item_from_index(index)
            if item is None or item.node in seen_nodes:
                continue
            items.append(item)
            seen_nodes.add(item.node)
        return items

    def _start_selection_watcher(self):
        """Maya上の選択変更をController Viewへ同期する"""
        if self._selection_callback_id is not None:
            return
        try:
            self._selection_callback_id = om.MEventMessage.addEventCallback(
                "SelectionChanged",
                self._on_maya_selection_changed,
            )
        except Exception as e:
            cmds.warning(f"defQA: Failed to start selection watcher: {e}")
            self._selection_callback_id = None

    def _stop_selection_watcher(self):
        """Maya選択変更コールバックを解除する"""
        if self._selection_callback_id is None:
            return
        try:
            om.MMessage.removeCallback(self._selection_callback_id)
        except Exception:
            pass
        self._selection_callback_id = None

    def _on_maya_selection_changed(self, *_args):
        """Maya上の選択をController Viewへ反映する"""
        if self._syncing_selection:
            return
        self._sync_controller_view_from_maya_selection()

    def _sync_controller_view_from_maya_selection(self):
        """現在のMayaセレクションをController Viewへ反映する"""
        selected_nodes = cmds.ls(selection=True, long=True)
        indexes = [
            self._ctrl_model.get_index_by_node(node)
            for node in selected_nodes
        ]
        indexes = [index for index in indexes if index.isValid()]

        self._syncing_selection = True
        try:
            selection_model = self.tree_controllers.selectionModel()
            selection_model.clearSelection()

            for index in indexes:
                selection_model.select(
                    index,
                    QtCore.QItemSelectionModel.Select
                    | QtCore.QItemSelectionModel.Rows,
                )

            if indexes:
                current = indexes[0]
                selection_model.setCurrentIndex(
                    current,
                    QtCore.QItemSelectionModel.Current
                    | QtCore.QItemSelectionModel.Rows,
                )
                self.tree_controllers.scrollTo(current)
                self._on_controller_selected(current, QtCore.QModelIndex())
            else:
                self._attr_model.set_attrs([])
        finally:
            self._syncing_selection = False

    # --- core operations ---

    def _generate(self, ctrl_items):
        saved_maya_selection = cmds.ls(selection=True, long=True)

        preset = self._load_current_preset()
        timeline = preset["timeline"]
        if self._timeline_overrides:
            timeline.update(self._timeline_overrides)
        preset["options"]["use_animation_layer"] = self.chk_use_anim_layer.isChecked()
        preset["options"]["return_to_neutral"] = self.chk_return_neutral.isChecked()
        preset["options"]["create_time_slider_bookmarks"] = self.chk_bookmarks.isChecked()

        targets = {
            ctrl_item.node: [a.attr for a in ctrl_item.attrs if a.enabled]
            for ctrl_item in ctrl_items
            if (
                ctrl_item.enabled
                and not ctrl_item.muted
                and any(a.enabled for a in ctrl_item.attrs)
            )
        }
        value_overrides = {
            ctrl_item.node: {
                attr_item.attr: list(attr_item.values)
                for attr_item in ctrl_item.attrs
                if attr_item.enabled
            }
            for ctrl_item in ctrl_items
            if ctrl_item.enabled and not ctrl_item.muted
        }
        pair_modes = {
            ctrl_item.node: {
                attr_item.attr: attr_item.pair_mode
                for attr_item in ctrl_item.attrs
                if attr_item.enabled
            }
            for ctrl_item in ctrl_items
            if ctrl_item.enabled and not ctrl_item.muted
        }

        if not targets:
            cmds.warning("defQA: No enabled attributes")
            return

        all_nodes = [item.node for item in self._ctrl_model.get_controllers()]
        pair_rules = preset.get("pair_rules", [])
        expanded_targets = expand_targets_for_pairs(
            targets,
            all_nodes,
            pair_rules,
            pair_modes,
        )

        initial_values = capture_initial_values(expanded_targets)

        existing_metadata = load_metadata()
        start_frame = get_generation_start_frame(existing_metadata, timeline)

        animation_layer = setup_generation_layer(
            preset["options"],
            existing_metadata,
            expanded_targets,
        )
        if preset["options"].get("use_animation_layer") and animation_layer is None:
            cmds.warning(
                "defQA: Animation Layer is unavailable. Keys will be set on the base layer"
            )

        end_frame, metadata_targets = build_animation(
            targets=targets,
            template=preset,
            start_frame=start_frame,
            default_span=timeline["default_span"],
            gap_frame=timeline["gap_frame"],
            part_gap_frame=timeline["part_gap_frame"],
            initial_values=initial_values,
            value_overrides=value_overrides,
            pair_modes=pair_modes,
            pair_rules=pair_rules,
            all_nodes=all_nodes,
        )

        if preset["options"].get("return_to_neutral", True):
            restore_initial_values(
                expanded_targets,
                initial_values,
                animation_layer=animation_layer,
            )

        bookmark_nodes = []
        if preset["options"].get("create_time_slider_bookmarks", False):
            existing_bookmarks = []
            if existing_metadata:
                existing_bookmarks = existing_metadata.get("bookmarks", [])
            bookmark_nodes = create_bookmarks_from_targets(
                metadata_targets,
                preset,
                existing_bookmarks=existing_bookmarks,
            )

        metadata = record_generation(
            existing_metadata,
            timeline,
            end_frame,
            metadata_targets,
            initial_values,
            bookmark_nodes,
            template_name=preset.get("template"),
            animation_layer=animation_layer,
        )

        cmds.playbackOptions(
            minTime=metadata["start_frame"],
            maxTime=metadata["end_frame"],
        )

        layer_note = ""
        if animation_layer:
            layer_note = f"  layer={animation_layer}"
        print(
            f"[defQA] Generated: frame {start_frame} - {end_frame}  "
            f"({len(targets)} controllers, "
            f"total {metadata['start_frame']}-{metadata['end_frame']})"
            f"{layer_note}"
        )

        self._restore_maya_selection(saved_maya_selection)
        self._update_delete_button_state()

    def _update_delete_button_state(self):
        """メタノードの有無に応じてDeleteボタンの有効状態を更新する"""
        if self.btn_delete is None:
            return
        self.btn_delete.setEnabled(load_metadata() is not None)

    def _restore_maya_selection(self, nodes):
        """生成処理後にMayaセレクションを復元する"""
        if not nodes:
            return

        existing = [node for node in nodes if cmds.objExists(node)]
        if not existing:
            return

        self._syncing_selection = True
        try:
            cmds.select(existing, replace=True)
        finally:
            self._syncing_selection = False

        self._sync_controller_view_from_maya_selection()

    def _delete(self):
        metadata = load_metadata()
        if metadata is None:
            cmds.warning("defQA: No metadata found to delete")
            return
        delete_generated_keys(metadata)
        restore_pose_from_metadata(metadata)
        delete_defqa_bookmarks(metadata)
        clear_metadata()
        print("[defQA] Deleted generated animation.")
        self._update_delete_button_state()

    def _load_current_preset(self):
        preset_name = self.line_preset.text().strip()
        override_name = ""
        if self.line_override is not None:
            override_name = self.line_override.text().strip()
        preset_path = get_preset_path(preset_name) if preset_name else None
        override_path = get_override_path(override_name) if override_name else None
        return load_preset(preset_path, override_path=override_path)


    def _get_optionvar_key(self) -> str:
        return getattr(self.__class__, "optionvar_key", None) \
            or f"{self.__class__.__name__}_settings"

    def _window_geometry_for_settings(self) -> dict:
        fg = self.frameGeometry()
        geo = self.geometry()
        return {
            "x": fg.x(),
            "y": fg.y(),
            "width": geo.width(),
            "height": geo.height(),
        }

    def _gather_settings_from_ui(self) -> dict:
        settings = {}
        try:
            snap = getattr(self, "_geometry_snapshot_for_save", None)
            if isinstance(snap, dict) and snap:
                settings["window_geometry"] = {
                    "x": snap["x"],
                    "y": snap["y"],
                    "width": snap["width"],
                    "height": snap["height"],
                }
            else:
                settings["window_geometry"] = self._window_geometry_for_settings()
        except Exception as e:
            print(f"[defQA] Failed to gather window geometry: {e}")

        if self.line_ctrl_set is not None:
            settings["ctrl_set"] = self.line_ctrl_set.text()
        if self.line_preset is not None:
            settings["preset"] = self.line_preset.text()
        if self.line_override is not None:
            settings["override"] = self.line_override.text()
        if self.chk_rotate is not None:
            settings["chk_rotate"] = bool(self.chk_rotate.isChecked())
        if self.chk_translate is not None:
            settings["chk_translate"] = bool(self.chk_translate.isChecked())
        if self.chk_scale is not None:
            settings["chk_scale"] = bool(self.chk_scale.isChecked())
        if self.chk_use_anim_layer is not None:
            settings["chk_use_anim_layer"] = bool(self.chk_use_anim_layer.isChecked())
        if self.chk_return_neutral is not None:
            settings["chk_return_neutral"] = bool(self.chk_return_neutral.isChecked())
        if self.chk_bookmarks is not None:
            settings["chk_bookmarks"] = bool(self.chk_bookmarks.isChecked())
        if self.radio_all is not None:
            settings["target_all"] = bool(self.radio_all.isChecked())
        if self.splitter is not None:
            sizes = list(self.splitter.sizes())
            if len(sizes) == self.splitter.count() and all(s > 0 for s in sizes):
                settings["splitter_sizes"] = sizes
        if self._timeline_overrides:
            settings["timeline_overrides"] = dict(self._timeline_overrides)

        return settings

    def _apply_settings_to_ui(self, settings: dict) -> None:
        if not isinstance(settings, dict):
            return

        try:
            geom = settings.get("window_geometry")
            if not isinstance(geom, dict):
                legacy = settings.get("geometry")
                if isinstance(legacy, dict):
                    geom = {
                        "x": legacy.get("x", 100),
                        "y": legacy.get("y", 100),
                        "width": legacy.get("w", legacy.get("width", 740)),
                        "height": legacy.get("h", legacy.get("height", 540)),
                    }
            if isinstance(geom, dict):
                self.resize(
                    geom.get("width", 740),
                    geom.get("height", 540),
                )
                self.move(geom.get("x", 100), geom.get("y", 100))
        except Exception as e:
            print(f"[defQA] Failed to apply window geometry: {e}")

        if self.line_ctrl_set is not None and settings.get("ctrl_set") is not None:
            self.line_ctrl_set.setText(settings["ctrl_set"])
        if self.line_preset is not None and settings.get("preset") is not None:
            self.line_preset.setText(settings["preset"])
        if self.line_override is not None and settings.get("override") is not None:
            self.line_override.setText(settings["override"])
        if self.chk_rotate is not None and settings.get("chk_rotate") is not None:
            self.chk_rotate.setChecked(settings["chk_rotate"])
        if self.chk_translate is not None and settings.get("chk_translate") is not None:
            self.chk_translate.setChecked(settings["chk_translate"])
        if self.chk_scale is not None and settings.get("chk_scale") is not None:
            self.chk_scale.setChecked(settings["chk_scale"])
        if self.chk_use_anim_layer is not None and settings.get("chk_use_anim_layer") is not None:
            self.chk_use_anim_layer.setChecked(settings["chk_use_anim_layer"])
        if self.chk_return_neutral is not None and settings.get("chk_return_neutral") is not None:
            self.chk_return_neutral.setChecked(settings["chk_return_neutral"])
        if self.chk_bookmarks is not None and settings.get("chk_bookmarks") is not None:
            self.chk_bookmarks.setChecked(settings["chk_bookmarks"])
        if self.radio_all is not None and settings.get("target_all") is not None:
            self.radio_all.setChecked(settings["target_all"])
            if self.radio_selected is not None:
                self.radio_selected.setChecked(not settings["target_all"])
        if self.splitter is not None:
            sizes = settings.get("splitter_sizes")
            if isinstance(sizes, list) and len(sizes) == self.splitter.count():
                if all(s > 0 for s in sizes):
                    self.splitter.setSizes(sizes)
                    self._splitter_initialized = True
        if settings.get("timeline_overrides"):
            self._timeline_overrides = dict(settings["timeline_overrides"])

    def _save_settings(self, silent: bool = False):
        try:
            data = self._gather_settings_from_ui()
            cmds.optionVar(sv=(self._get_optionvar_key(), json.dumps(data)))
            if not silent:
                print("[defQA] Save settings succeeded.")
        except Exception as e:
            print(f"[defQA] Failed to save settings: {e}")

    def _load_settings(self) -> None:
        try:
            key = self._get_optionvar_key()
            if cmds.optionVar(exists=key):
                raw = cmds.optionVar(q=key)
                if isinstance(raw, (list, tuple)) and raw:
                    raw = raw[0]
                if isinstance(raw, str) and raw:
                    settings = json.loads(raw)
                    self._apply_settings_to_ui(settings)
                    return
            if self._factory_settings:
                self._apply_settings_to_ui(self._factory_settings)
        except Exception as e:
            print(f"[defQA] Failed to load settings: {e}")

    def _reset_settings(self) -> None:
        ok = True
        try:
            key = self._get_optionvar_key()
            if cmds.optionVar(exists=key):
                cmds.optionVar(remove=key)
        except Exception as e:
            ok = False
            print(f"[defQA] Failed to reset settings: {e}")

        try:
            if self._factory_settings:
                factory = dict(self._factory_settings)
                factory.pop("window_geometry", None)
                factory.pop("splitter_sizes", None)
                self._apply_settings_to_ui(factory)
                self._splitter_initialized = False
                QtCore.QTimer.singleShot(0, self._set_equal_splitter_sizes)
        except Exception as e:
            ok = False
            print(f"[defQA] Failed to reset settings: {e}")

        if ok:
            print("[defQA] Reset settings succeeded.")

    def _on_menu_save_settings(self):
        try:
            self._save_settings()
        except Exception as e:
            print(f"[defQA] Failed to save settings: {e}")

    def _on_menu_reset_settings(self):
        try:
            self._reset_settings()
        except Exception as e:
            print(f"[defQA] Failed to reset settings: {e}")

    def _get_docs_dir(self) -> str:
        explicit = getattr(self.__class__, "docs_dir", None)
        if explicit:
            return os.path.abspath(explicit)
        return os.path.abspath(os.path.join(DIR_NAME, "docs"))

    def _open_document(self, filename: Optional[str] = None) -> None:
        if filename is None or isinstance(filename, bool):
            filename = getattr(self.__class__, "quickstart_doc_file", "README.md")
        if not isinstance(filename, str) or not filename.strip():
            cmds.warning("defQA: Quick Start Document is not configured.")
            return

        doc_path = None
        try:
            doc_path = os.path.join(self._get_docs_dir(), filename)
            if not os.path.exists(doc_path):
                raise FileNotFoundError(doc_path)

            opened = False
            try:
                url = QtCore.QUrl.fromLocalFile(doc_path)
                opened = bool(QtGui.QDesktopServices.openUrl(url))
            except Exception:
                opened = False

            if not opened:
                if platform.system() == "Windows":
                    try:
                        os.startfile(doc_path)  # type: ignore[attr-defined]
                    except Exception:
                        subprocess.Popen(
                            ["cmd", "/c", "start", "", doc_path],
                            shell=True,
                        )
                else:
                    subprocess.Popen(["xdg-open", doc_path])
        except Exception:
            cmds.warning(
                "defQA: Failed to open Quick Start Document: "
                f"{doc_path or filename}"
            )

    def _get_about_module(self):
        """About表示用のパッケージモジュールを返す"""
        tool_name = self.__class__.__module__.split(".", maxsplit=1)[0]
        pkg = sys.modules.get(tool_name)
        if pkg is not None:
            return tool_name, pkg
        pkg = sys.modules.get(self.__class__.__module__)
        if pkg is not None:
            return tool_name, pkg
        return tool_name, None

    def _show_about_dialog(self) -> None:
        """About...ダイアログを表示する"""
        tool_name, pkg = self._get_about_module()
        author = getattr(pkg, "__author__", "")
        copyright_ = getattr(pkg, "__copyright__", "")
        email = getattr(pkg, "__email__", "")
        status = getattr(pkg, "__status__", "")
        version = getattr(pkg, "__version__", "")

        lines = [
            f"{tool_name}  v{version}",
            "",
            f"Author: {author}",
            f"Email: {email}",
            f"Copyright: {copyright_}",
            f"Status: {status}",
        ]
        QtWidgets.QMessageBox.about(
            self,
            f"About {tool_name}",
            "\n".join(lines),
        )

    def _open_web_document(self, filename: Optional[str] = None) -> None:
        try:
            if filename is None or isinstance(filename, bool):
                filename = getattr(self.__class__, "web_doc_file", None)
            if not isinstance(filename, str) or not filename.strip():
                cmds.warning("defQA: Web documentation is not configured.")
                return
            index_path = os.path.join(self._get_docs_dir(), filename)
            if not os.path.isfile(index_path):
                cmds.warning(f"defQA: Web documentation not found: {index_path}")
                return
            if webbrowser.open(index_path):
                print(f"[defQA] Web documentation opened: {index_path}")
        except Exception:
            cmds.warning("defQA: Failed to open web documentation")

    def _set_equal_splitter_sizes(self) -> None:
        if self.splitter is None:
            return
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setSizes([1, 1])
        self._splitter_initialized = True

    def showEvent(self, event):
        super().showEvent(event)
        if self._splitter_initialized or self.splitter is None:
            return
        sizes = self.splitter.sizes()
        if len(sizes) != self.splitter.count() or any(s <= 0 for s in sizes):
            self._set_equal_splitter_sizes()
        self._splitter_initialized = True

    def closeEvent(self, event):
        self._stop_selection_watcher()
        try:
            self._geometry_snapshot_for_save = self._window_geometry_for_settings()
            self._save_settings(silent=True)
        except Exception as e:
            print(f"[defQA] Failed to save settings: {e}")
        finally:
            self._geometry_snapshot_for_save = None
        super().closeEvent(event)


def _get_part_side_pair(node, preset):
    """プリセットのparts定義からPart/Side/Pairを推定する"""
    parts = preset.get("parts", {})
    for part_name, part_data in parts.items():
        pair_mode = part_data.get("pair_mode", "single")

        left_patterns = part_data.get("left_patterns", [])
        if match_any_pattern(node, left_patterns):
            return part_name, "L", pair_mode

        right_patterns = part_data.get("right_patterns", [])
        if match_any_pattern(node, right_patterns):
            return part_name, "R", pair_mode

        patterns = part_data.get("patterns", [])
        if match_any_pattern(node, patterns):
            return part_name, _infer_side_from_name(node), pair_mode

    return "", _infer_side_from_name(node), "single"


def _infer_side_from_name(node):
    """ノード名からSideを推定する"""
    short_name = node.split("|")[-1].split(":")[-1]
    if "_L_" in short_name or "_L" in short_name:
        return "L"
    if "_R_" in short_name or "_R" in short_name:
        return "R"
    if "left" in short_name.lower():
        return "L"
    if "right" in short_name.lower():
        return "R"
    return ""


def _attr_group(attr):
    """TRS attr名からグループ名を返す"""
    if attr.startswith("translate"):
        return "translate"
    if attr.startswith("rotate"):
        return "rotate"
    if attr.startswith("scale"):
        return "scale"
    return ""


def show():
    """defQA メインウィンドウを表示する"""
    win = DefQAMainWindow()
    win.show()
    win.raise_()
    win.activateWindow()
    return win


def showUI():
    """外部公開用エントリポイント"""
    show()
