"""プリセット選択・タイムライン設定ダイアログ"""
from .qt_compat import QtWidgets, QtCore

from ..core.template_loader import (
    list_presets,
    list_overrides,
    load_preset,
    get_preset_path,
    get_override_path,
    save_preset,
)

NEW_TEMPLATE_ENTRY = "New Template..."
NEW_OVERRIDE_ENTRY = "New Override..."


class PresetDialog(QtWidgets.QDialog):
    """
    プリセット選択とタイムライン設定を編集するダイアログ。
    メニュー > Preset > Open Preset Dialog... から開く。
    """

    def __init__(
        self,
        preset_name="",
        override_name="",
        parent=None,
        export_preset=None
    ):
        super().__init__(parent)
        self._export_preset = export_preset
        self.setWindowTitle("Preset Dialog")
        self.setMinimumWidth(340)

        self._setup_ui()
        self._populate_presets()
        self._populate_overrides()

        if preset_name:
            self.combo_preset.setCurrentText(preset_name)
        if override_name:
            self.combo_override.setCurrentText(override_name)

    def _setup_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(8)

        row_preset = QtWidgets.QHBoxLayout()
        row_preset.addWidget(QtWidgets.QLabel("Template:"))
        self.combo_preset = QtWidgets.QComboBox()
        row_preset.addWidget(self.combo_preset)
        layout.addLayout(row_preset)

        row_override = QtWidgets.QHBoxLayout()
        row_override.addWidget(QtWidgets.QLabel("Override:"))
        self.combo_override = QtWidgets.QComboBox()
        row_override.addWidget(self.combo_override)
        layout.addLayout(row_override)

        sep = QtWidgets.QFrame()
        sep.setFrameShape(QtWidgets.QFrame.HLine)
        sep.setFrameShadow(QtWidgets.QFrame.Sunken)
        layout.addWidget(sep)

        form = QtWidgets.QFormLayout()
        form.setLabelAlignment(QtCore.Qt.AlignRight)
        form.setFieldGrowthPolicy(QtWidgets.QFormLayout.AllNonFixedFieldsGrow)

        self.spin_start_frame = QtWidgets.QSpinBox()
        self.spin_start_frame.setRange(-9999, 99999)
        self.spin_start_frame.setValue(1)
        form.addRow("Start Frame:", self.spin_start_frame)

        self.spin_default_span = QtWidgets.QSpinBox()
        self.spin_default_span.setRange(1, 999)
        self.spin_default_span.setValue(8)
        form.addRow("Default Span:", self.spin_default_span)

        self.spin_gap_frame = QtWidgets.QSpinBox()
        self.spin_gap_frame.setRange(0, 999)
        self.spin_gap_frame.setValue(4)
        form.addRow("Gap Frames:", self.spin_gap_frame)

        self.spin_part_gap_frame = QtWidgets.QSpinBox()
        self.spin_part_gap_frame.setRange(0, 999)
        self.spin_part_gap_frame.setValue(10)
        form.addRow("Part Gap Frames:", self.spin_part_gap_frame)

        layout.addLayout(form)

        self.btn_save_preset = QtWidgets.QPushButton("Save Preset")
        self.btn_load_preset = QtWidgets.QPushButton("Load Preset")

        row_preset_buttons = QtWidgets.QHBoxLayout()
        row_preset_buttons.setSpacing(8)
        row_preset_buttons.addStretch()
        row_preset_buttons.addWidget(self.btn_save_preset)
        row_preset_buttons.addWidget(self.btn_load_preset)
        layout.addLayout(row_preset_buttons)

        self.btn_ok = QtWidgets.QPushButton("OK")
        self.btn_cancel = QtWidgets.QPushButton("Cancel")
        self.btn_ok.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)

        button_policy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Fixed,
        )
        self.btn_ok.setSizePolicy(button_policy)
        self.btn_cancel.setSizePolicy(button_policy)

        row_dialog_buttons = QtWidgets.QHBoxLayout()
        row_dialog_buttons.setSpacing(8)
        row_dialog_buttons.addWidget(self.btn_ok, 1)
        row_dialog_buttons.addWidget(self.btn_cancel, 1)
        layout.addLayout(row_dialog_buttons)

        self.combo_preset.currentTextChanged.connect(self._on_preset_changed)
        self.combo_override.currentTextChanged.connect(self._on_preset_changed)
        self.btn_save_preset.clicked.connect(self._on_save_preset)
        self.btn_load_preset.clicked.connect(self._on_load_preset)

    def _populate_presets(self):
        self.combo_preset.blockSignals(True)
        current = self.combo_preset.currentText()
        self.combo_preset.clear()
        self.combo_preset.addItem("")
        for name in sorted(list_presets()):
            self.combo_preset.addItem(name)
        self.combo_preset.addItem(NEW_TEMPLATE_ENTRY)
        if current:
            self.combo_preset.setCurrentText(current)
        self.combo_preset.blockSignals(False)

    def _populate_overrides(self):
        self.combo_override.blockSignals(True)
        current = self.combo_override.currentText()
        self.combo_override.clear()
        self.combo_override.addItem("")
        for name in sorted(list_overrides()):
            self.combo_override.addItem(name)
        self.combo_override.addItem(NEW_OVERRIDE_ENTRY)
        if current:
            self.combo_override.setCurrentText(current)
        self.combo_override.blockSignals(False)

    def _is_new_template_entry(self, name):
        return name.strip() == NEW_TEMPLATE_ENTRY

    def _is_new_override_entry(self, name):
        return name.strip() == NEW_OVERRIDE_ENTRY

    def _is_new_entry(self, name):
        return (
            self._is_new_template_entry(name)
            or self._is_new_override_entry(name)
        )

    def _normalize_combo_name(self, name):
        text = name.strip()
        if not text or self._is_new_entry(text):
            return ""
        return text

    def _apply_preset_timeline(self, preset):
        """プリセットのタイムライン設定をスピンへ反映する"""
        tl = preset.get("timeline", {})
        self.spin_start_frame.setValue(tl.get("start_frame", 1))
        self.spin_default_span.setValue(tl.get("default_span", 8))
        self.spin_gap_frame.setValue(tl.get("gap_frame", 4))
        self.spin_part_gap_frame.setValue(tl.get("part_gap_frame", 10))

    def _on_preset_changed(self, *_args):
        """プリセット変更時にタイムライン設定を更新する"""
        if self._is_new_template_entry(self.combo_preset.currentText()):
            return
        if self._is_new_override_entry(self.combo_override.currentText()):
            return

        preset = self._load_selected_preset()
        if preset is None:
            return
        self._apply_preset_timeline(preset)

    def _load_selected_preset(self):
        preset_name = self._normalize_combo_name(self.combo_preset.currentText())
        override_name = self._normalize_combo_name(self.combo_override.currentText())
        preset_path = get_preset_path(preset_name) if preset_name else None
        override_path = get_override_path(override_name) if override_name else None
        if preset_path is None and override_path is None:
            return None
        try:
            return load_preset(preset_path, override_path=override_path)
        except Exception:
            return None

    def _prompt_preset_name(self, default_name=""):
        name, ok = QtWidgets.QInputDialog.getText(
            self,
            "Save Preset",
            "Preset name:",
            text=default_name,
        )
        if not ok:
            return None
        name = name.strip()
        if not name:
            return None
        if self._is_new_entry(name):
            QtWidgets.QMessageBox.warning(
                self,
                "Save Preset",
                "New Template... / New Override... cannot be used as preset names",
            )
            return None
        return name

    def _build_preset_for_save(self, template_name=None):
        """保存用プリセットdictを組み立てる"""
        if self._export_preset is not None:
            preset = self._export_preset(self.get_timeline_settings())
        else:
            preset = load_preset()
            preset["timeline"].update(self.get_timeline_settings())

        if template_name:
            preset["template"] = template_name
        return preset

    def _save_new_template(self):
        name = self._prompt_preset_name()
        if name is None:
            return

        preset = self._build_preset_for_save(template_name=name)
        if not preset.get("parts"):
            QtWidgets.QMessageBox.warning(
                self,
                "Save Preset",
                "parts is empty. Load a template and scan before saving",
            )
            return

        try:
            path = save_preset(preset, name, as_override=False)
            self._populate_presets()
            self.combo_preset.setCurrentText(name)
            QtWidgets.QMessageBox.information(self, "Save Preset", f"Saved:\n{path}")
        except Exception as exc:
            QtWidgets.QMessageBox.warning(self, "Save Preset", str(exc))

    def _save_new_override(self):
        template_name = self._normalize_combo_name(self.combo_preset.currentText())
        if not template_name:
            QtWidgets.QMessageBox.warning(
                self,
                "Save Preset",
                "Select a template before saving an override",
            )
            return

        name = self._prompt_preset_name()
        if name is None:
            return

        full_preset = self._build_preset_for_save()
        preset = {
            "extends": template_name,
            "template": name,
            "version": full_preset.get("version", "0.1.0"),
            "timeline": full_preset.get("timeline", self.get_timeline_settings()),
            "parts": full_preset.get("parts", {}),
        }

        try:
            path = save_preset(preset, name, as_override=True)
            self._populate_overrides()
            self.combo_override.setCurrentText(name)
            QtWidgets.QMessageBox.information(self, "Save Preset", f"Saved:\n{path}")
        except Exception as exc:
            QtWidgets.QMessageBox.warning(self, "Save Preset", str(exc))

    def _on_save_preset(self):
        override_name = self.combo_override.currentText().strip()
        template_name = self.combo_preset.currentText().strip()

        if self._is_new_override_entry(override_name):
            self._save_new_override()
            return
        if self._is_new_template_entry(template_name):
            self._save_new_template()
            return

        preset = self._build_preset_for_save()
        loaded = self._load_selected_preset()
        if loaded is None and self._export_preset is None:
            QtWidgets.QMessageBox.warning(
                self,
                "Save Preset",
                "Select a preset to load",
            )
            return

        default_name = override_name
        if not default_name:
            default_name = template_name
        name = self._prompt_preset_name(default_name=default_name)
        if name is None:
            return

        as_override = override_name != ""
        if not as_override:
            answer = QtWidgets.QMessageBox.question(
                self,
                "Save Preset",
                "Save as an override preset?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            )
            as_override = answer == QtWidgets.QMessageBox.Yes

        try:
            path = save_preset(preset, name, as_override=as_override)
            if as_override:
                self._populate_overrides()
                self.combo_override.setCurrentText(name)
            else:
                self._populate_presets()
                self.combo_preset.setCurrentText(name)
            QtWidgets.QMessageBox.information(self, "Save Preset", f"Saved:\n{path}")
        except Exception as exc:
            QtWidgets.QMessageBox.warning(self, "Save Preset", str(exc))

    def _sync_loaded_preset_to_parent(self, preset):
        """読み込んだプリセットを親ウィンドウへ反映する"""
        parent = self.parent()
        if parent is None:
            return

        line_preset = getattr(parent, "line_preset", None)
        if line_preset is not None:
            line_preset.setText(self.get_preset_name())

        line_override = getattr(parent, "line_override", None)
        if line_override is not None:
            line_override.setText(self.get_override_name())

        timeline_overrides = getattr(parent, "_timeline_overrides", None)
        if timeline_overrides is not None:
            parent._timeline_overrides = self.get_timeline_settings()

        apply_preset = getattr(parent, "_apply_preset_to_controllers", None)
        if apply_preset is not None and getattr(parent, "_ctrl_model", None):
            if parent._ctrl_model.get_controllers():
                apply_preset(preset)

        refresh_cache = getattr(parent, "_refresh_preset_cache", None)
        if refresh_cache is not None:
            refresh_cache()

    def _format_loaded_preset_message(self, preset):
        template_name = self._normalize_combo_name(self.combo_preset.currentText())
        override_name = self._normalize_combo_name(self.combo_override.currentText())
        tl = preset.get("timeline", {})
        part_count = len(preset.get("parts", {}))

        lines = [
            "Preset loaded.",
            "",
            f"Template: {template_name or '(default)'}",
            f"Override: {override_name or '(none)'}",
            "",
            f"Start Frame: {tl.get('start_frame', 1)}",
            f"Default Span: {tl.get('default_span', 8)}",
            f"Gap Frames: {tl.get('gap_frame', 4)}",
            f"Part Gap Frames: {tl.get('part_gap_frame', 10)}",
            f"Parts: {part_count}",
        ]
        return "\n".join(lines)

    def _on_load_preset(self):
        if self._is_new_template_entry(self.combo_preset.currentText()):
            QtWidgets.QMessageBox.warning(
                self,
                "Load Preset",
                f"{NEW_TEMPLATE_ENTRY} cannot be loaded",
            )
            return
        if self._is_new_override_entry(self.combo_override.currentText()):
            QtWidgets.QMessageBox.warning(
                self,
                "Load Preset",
                f"{NEW_OVERRIDE_ENTRY} cannot be loaded",
            )
            return

        preset_name = self._normalize_combo_name(self.combo_preset.currentText())
        override_name = self._normalize_combo_name(self.combo_override.currentText())
        if not preset_name and not override_name:
            QtWidgets.QMessageBox.warning(
                self,
                "Load Preset",
                "Select a template or override",
            )
            return

        preset = self._load_selected_preset()
        if preset is None:
            QtWidgets.QMessageBox.warning(
                self,
                "Load Preset",
                "Failed to load preset",
            )
            return

        self._apply_preset_timeline(preset)
        self._sync_loaded_preset_to_parent(preset)
        QtWidgets.QMessageBox.information(
            self,
            "Load Preset",
            self._format_loaded_preset_message(preset),
        )

    def get_preset_name(self):
        return self._normalize_combo_name(self.combo_preset.currentText())

    def get_override_name(self):
        return self._normalize_combo_name(self.combo_override.currentText())

    def get_timeline_settings(self):
        return {
            "start_frame": self.spin_start_frame.value(),
            "default_span": self.spin_default_span.value(),
            "gap_frame": self.spin_gap_frame.value(),
            "part_gap_frame": self.spin_part_gap_frame.value(),
        }
