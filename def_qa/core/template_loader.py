"""YAMLプリセットを読み込むモジュール"""
import copy
import os

from ..vendor import get_yaml

yaml = get_yaml()

DEFQA_PRESET_PATH_ENV = "DEFQA_PRESET_PATH"

_MODULE_DIR = os.path.dirname(__file__)
_DEFAULT_PRESETS_DIR = os.path.normpath(
    os.path.join(_MODULE_DIR, "..", "presets"),
)


def get_presets_dir():
    """
    プリセット配置ディレクトリを返す。

    環境変数 DEFQA_PRESET_PATH が設定されていればそれをpresets/ルートとして使う。
    未設定時はパッケージ同梱の presets/ を使う。
    """
    custom_path = os.environ.get(DEFQA_PRESET_PATH_ENV, "").strip()
    if custom_path:
        return os.path.normpath(os.path.abspath(custom_path))
    return _DEFAULT_PRESETS_DIR


def get_overrides_dir():
    """overrideプリセット配置ディレクトリを返す"""
    return os.path.join(get_presets_dir(), "overrides")


class _PresetDumper(yaml.SafeDumper):
    """プリセット保存用YAMLダンパー"""


def _is_flow_style_list(data):
    """数値リストのみインライン表記にする"""
    if not data:
        return True
    for item in data:
        if not isinstance(item, (int, float)):
            return False
    return True


def _represent_list(dumper, data):
    return dumper.represent_sequence(
        "tag:yaml.org,2002:seq",
        data,
        flow_style=_is_flow_style_list(data),
    )


_PresetDumper.add_representer(list, _represent_list)

PRESETS_DIR = get_presets_dir()
OVERRIDES_DIR = get_overrides_dir()

_DEFAULT_TIMELINE = {
    "start_frame": 1,
    "default_span": 8,
    "gap_frame": 4,
    "part_gap_frame": 10,
    "return_to_neutral": True,
}

_DEFAULT_OPTIONS = {
    "use_animation_layer": False,
    "animation_layer_name": "defQA_anim_layer",
    "create_time_slider_bookmarks": False,
    "enable_translate": True,
    "enable_rotate": True,
    "enable_scale": False,
}

_DEFAULT_PAIR_RULES = [
    {"left": "_L_", "right": "_R_"},
    {"left": "_L0_", "right": "_R0_"},
    {"left": "_L", "right": "_R"},
    {"left": "left", "right": "right"},
    {"left": "Left", "right": "Right"},
]


def load_preset(preset_path=None, override_path=None):
    """
    YAMLプリセットを読み込む。パスがNoneの場合はデフォルト設定を返す。

    Args:
        preset_path: ベースYAMLファイルのパス
        override_path: キャラクターoverride YAMLのパス

    Returns:
        dict: マージ済みプリセットデータ
    """
    if preset_path is None and override_path is None:
        return _build_default_preset()

    if preset_path:
        preset = _load_yaml_file(preset_path)
        _apply_defaults(preset)
    else:
        preset = _build_default_preset()

    if override_path:
        override = _load_yaml_file(override_path)
        if preset_path is None and override.get("extends"):
            base_path = get_preset_path(override["extends"])
            if base_path:
                preset = _load_yaml_file(base_path)
                _apply_defaults(preset)
        preset = merge_presets(preset, override)
    elif preset.get("extends"):
        base_path = get_preset_path(preset["extends"])
        if base_path:
            base_preset = _load_yaml_file(base_path)
            _apply_defaults(base_preset)
            preset = merge_presets(base_preset, preset)

    _apply_defaults(preset)
    return preset


def merge_presets(base, override):
    """
    ベースプリセットにoverrideをdeepcopyしてマージする。

    partsセクションは部位単位でマージする。
    """
    if not override:
        return copy.deepcopy(base)

    merged = copy.deepcopy(base)
    for key, value in override.items():
        if key == "extends":
            continue
        if key == "parts" and isinstance(value, dict):
            merged["parts"] = _merge_parts(merged.get("parts", {}), value)
            continue
        if (
            key in merged
            and isinstance(merged[key], dict)
            and isinstance(value, dict)
        ):
            merged[key] = merge_presets(merged[key], value)
            continue
        merged[key] = copy.deepcopy(value)
    return merged


def list_presets():
    """presets/ディレクトリのYAMLファイル名リストを返す（拡張子なし）"""
    if not os.path.isdir(PRESETS_DIR):
        return []
    names = []
    for fname in os.listdir(PRESETS_DIR):
        if fname.endswith((".yaml", ".yml")):
            names.append(os.path.splitext(fname)[0])
    return names


def list_overrides():
    """presets/overrides/のYAMLファイル名リストを返す（拡張子なし）"""
    if not os.path.isdir(OVERRIDES_DIR):
        return []
    names = []
    for fname in os.listdir(OVERRIDES_DIR):
        if fname.endswith((".yaml", ".yml")):
            names.append(os.path.splitext(fname)[0])
    return names


def get_preset_path(preset_name):
    """プリセット名からフルパスを返す。見つからない場合はNoneを返す"""
    if not preset_name:
        return None
    for ext in (".yaml", ".yml"):
        path = os.path.join(PRESETS_DIR, preset_name + ext)
        if os.path.isfile(path):
            return path
    return None


def get_override_path(override_name):
    """override名からフルパスを返す。見つからない場合はNoneを返す"""
    if not override_name:
        return None
    for ext in (".yaml", ".yml"):
        path = os.path.join(OVERRIDES_DIR, override_name + ext)
        if os.path.isfile(path):
            return path
    return None


def save_preset(preset_data, preset_name, as_override=False):
    """
    プリセットデータをYAMLファイルに保存する。

    Args:
        preset_data: 保存するdict
        preset_name: ファイル名（拡張子なし）
        as_override: Trueの場合はoverrides/に保存

    Returns:
        str: 保存したファイルパス
    """
    target_dir = OVERRIDES_DIR if as_override else PRESETS_DIR
    os.makedirs(target_dir, exist_ok=True)
    path = os.path.join(target_dir, f"{preset_name}.yaml")
    with open(path, "w", encoding="utf-8") as handle:
        yaml.dump(
            preset_data,
            handle,
            Dumper=_PresetDumper,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
        )
    return path


def _load_yaml_file(path):
    """YAMLファイルを読み込む"""
    with open(path, "r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Invalid preset file: {path}")
    return data


_MUTE_KEYS = ("muted", "muted_patterns")


def _merge_part_mute_fields(merged_part, override_part):
    """Override側のMute定義でベース側のMute状態を置き換える"""
    if not any(key in override_part for key in _MUTE_KEYS):
        return

    if "muted" in override_part:
        merged_part["muted"] = copy.deepcopy(override_part["muted"])
    else:
        merged_part.pop("muted", None)

    if "muted_patterns" in override_part:
        merged_part["muted_patterns"] = copy.deepcopy(
            override_part["muted_patterns"]
        )
    else:
        merged_part.pop("muted_patterns", None)


def _merge_parts(base_parts, override_parts):
    """partsセクションを部位単位でマージする"""
    merged = copy.deepcopy(base_parts)
    for part_name, part_data in override_parts.items():
        if part_name not in merged:
            merged[part_name] = copy.deepcopy(part_data)
            continue
        if isinstance(part_data, dict) and isinstance(merged[part_name], dict):
            merged[part_name] = merge_presets(merged[part_name], part_data)
            _merge_part_mute_fields(merged[part_name], part_data)
        else:
            merged[part_name] = copy.deepcopy(part_data)
    return merged


def _build_default_preset():
    return {
        "template": "default",
        "version": "0.1.0",
        "timeline": _DEFAULT_TIMELINE.copy(),
        "options": _DEFAULT_OPTIONS.copy(),
        "pair_rules": list(_DEFAULT_PAIR_RULES),
        "parts": {},
    }


def _apply_defaults(data):
    """dataにデフォルト値をマージする（既存キーは上書きしない）"""
    if "timeline" not in data:
        data["timeline"] = {}
    for key, value in _DEFAULT_TIMELINE.items():
        data["timeline"].setdefault(key, value)

    if "options" not in data:
        data["options"] = {}
    for key, value in _DEFAULT_OPTIONS.items():
        data["options"].setdefault(key, value)

    data.setdefault("pair_rules", list(_DEFAULT_PAIR_RULES))
    data.setdefault("parts", {})
