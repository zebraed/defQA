"""アニメーションキー生成モジュール"""
from maya import cmds

from ..utils.name_match import match_any_pattern
from ..utils.pair_detector import find_pair_node
from .animation_layer import delete_animation_layer, select_base_animation_layer


_DEFAULT_ROTATE_VALUES = [0, 45, 0, -45, 0]
_DEFAULT_TRANSLATE_VALUES = [0, 0.2, 0, -0.2, 0]
_DEFAULT_SCALE_VALUES = [1.0, 1.5, 1.0, 0.5, 1.0]

_ROTATE_ATTRS = frozenset(["rotateX", "rotateY", "rotateZ"])
_TRANSLATE_ATTRS = frozenset(["translateX", "translateY", "translateZ"])
_SCALE_ATTRS = frozenset(["scaleX", "scaleY", "scaleZ"])

_PAIR_MODES = frozenset(["pair_mirror", "pair_same", "pair_offset"])


def capture_initial_values(targets):
    """
    targetsの現在値を保存する。

    Args:
        targets: {node: [attrs]}

    Returns:
        dict: {node: {attr: value}}
    """
    initial = {}
    for node, attrs in targets.items():
        initial[node] = {}
        for attr in attrs:
            initial[node][attr] = cmds.getAttr(f"{node}.{attr}")
    return initial


def restore_initial_values(targets, initial_values, animation_layer=None):
    """初期値を復元する"""
    if animation_layer:
        select_base_animation_layer()

    for node, attrs in targets.items():
        for attr in attrs:
            node_vals = initial_values.get(node, {})
            if attr not in node_vals:
                continue
            try:
                cmds.setAttr(f"{node}.{attr}", node_vals[attr])
            except Exception:
                pass


def restore_pose_from_metadata(metadata):
    """メタデータに保存したStartFrame時点のポーズを復元する"""
    initial_values = metadata.get("initial_values")
    if not initial_values:
        return

    animation_layer = metadata.get("animation_layer")
    if animation_layer:
        select_base_animation_layer()

    targets = {}
    for node, attr_values in initial_values.items():
        if not cmds.objExists(node):
            continue
        targets[node] = list(attr_values.keys())

    restore_initial_values(targets, initial_values)

    start_frame = metadata.get("start_frame")
    if start_frame is not None:
        cmds.currentTime(start_frame)


def infer_pair_modes(targets, template):
    """
    プリセットのparts定義から各ノード・attrのpair_modeを推定する。

    Returns:
        dict: {node: {attr: pair_mode}}
    """
    pair_modes = {}
    for node, attrs in targets.items():
        mode = _infer_pair_mode_for_node(node, template)
        pair_modes[node] = {attr: mode for attr in attrs}
    return pair_modes


def expand_targets_for_pairs(targets, all_nodes, pair_rules, pair_modes):
    """
    pair系モードでペア側ノードも初期値保存・復元対象に含める。

    Returns:
        dict: {node: [attrs]}
    """
    expanded = {}
    for node, attrs in targets.items():
        expanded[node] = list(attrs)

    for node, attrs in targets.items():
        for attr in attrs:
            mode = _get_pair_mode(node, attr, pair_modes)
            if mode not in _PAIR_MODES:
                continue

            pair_node = find_pair_node(node, all_nodes, pair_rules)
            if pair_node is None:
                continue

            if pair_node not in expanded:
                expanded[pair_node] = []
            if attr not in expanded[pair_node]:
                expanded[pair_node].append(attr)

    return expanded


def build_animation(
    targets,
    template,
    start_frame,
    default_span,
    gap_frame,
    part_gap_frame,
    initial_values=None,
    value_overrides=None,
    pair_modes=None,
    pair_rules=None,
    all_nodes=None,
):
    """
    targets内の各ノード・attrにテストアニメーションキーを生成する。

    Args:
        targets: {node: [attrs]}
        template: プリセットデータ（partsセクションを参照）
        start_frame: 開始フレーム
        default_span: キー間のフレーム数
        gap_frame: attr間のギャップフレーム
        part_gap_frame: ノード間のギャップフレーム
        initial_values: {node: {attr: value}} 初期値（neutralとして使用）
        value_overrides: {node: {attr: [values]}} UI編集値などの上書き
        pair_modes: {node: {attr: pair_mode}}
        pair_rules: L/R置換ルール
        all_nodes: ペア検索対象ノード一覧

    Returns:
        tuple: (end_frame, metadata_targets)
    """
    if pair_modes is None:
        pair_modes = {}
    if pair_rules is None:
        pair_rules = template.get("pair_rules", [])
    if all_nodes is None:
        all_nodes = list(targets.keys())

    frame = start_frame
    metadata_targets = []
    processed = set()

    for node, attrs in targets.items():
        node_meta = {"node": node, "attrs": [], "start_frame": frame}
        node_start = frame

        for attr in attrs:
            pair_key = _make_pair_key(node, attr, all_nodes, pair_rules, pair_modes)
            if pair_key in processed:
                continue

            values = _get_values(
                node,
                attr,
                template,
                initial_values,
                value_overrides=value_overrides,
            )
            span = _get_span(node, attr, template, default_span)
            mode = _get_pair_mode(node, attr, pair_modes)
            pair_node = find_pair_node(node, all_nodes, pair_rules)

            if mode in _PAIR_MODES and pair_node is not None:
                attr_start = frame
                if mode == "pair_mirror":
                    frame = _key_pair_mirror(
                        node,
                        pair_node,
                        attr,
                        values,
                        frame,
                        span,
                        mirror_sign=_mirror_sign_for_attr(attr),
                    )
                elif mode == "pair_same":
                    frame = _key_pair_same(
                        node,
                        pair_node,
                        attr,
                        values,
                        frame,
                        span,
                    )
                else:
                    frame = _key_pair_offset(
                        node,
                        pair_node,
                        attr,
                        values,
                        frame,
                        span,
                        gap_frame,
                    )

                attr_end = frame - span
                node_meta["attrs"].append(attr)
                _add_metadata_target(
                    metadata_targets,
                    pair_node,
                    attr,
                    attr_start,
                    attr_end,
                )
                processed.add(pair_key)
            else:
                frame = _key_sequence(node, attr, values, frame, span)
                node_meta["attrs"].append(attr)
                processed.add((node, attr))

            frame += gap_frame

        if node_meta["attrs"]:
            node_meta["end_frame"] = frame - gap_frame
            metadata_targets.append(node_meta)
            frame = node_meta["end_frame"] + part_gap_frame
        else:
            frame = node_start

    end_frame = start_frame
    if metadata_targets:
        end_frame = metadata_targets[-1]["end_frame"]

    return end_frame, metadata_targets


def get_test_values(node, attr, template, initial_values=None):
    """
    テンプレートとattrからテスト値リストを返す。
    UIのプレビュー用途などで使用する。
    """
    return _get_values(node, attr, template, initial_values)


def delete_generated_keys(metadata):
    """メタデータに基づいて生成したキーを削除する"""
    animation_layer = metadata.get("animation_layer")
    if animation_layer and delete_animation_layer(animation_layer):
        return

    start_frame = metadata.get("start_frame")
    end_frame = metadata.get("end_frame")

    for target in metadata.get("targets", []):
        node = target["node"]
        if not cmds.objExists(node):
            continue
        for attr in target["attrs"]:
            if not cmds.attributeQuery(attr, node=node, exists=True):
                continue
            plug = f"{node}.{attr}"
            cmds.cutKey(plug, time=(start_frame, end_frame), option="keys")


def _key_sequence(node, attr, values, start_frame, span):
    """単一attrにキーシーケンスを打つ。最終フレームの次フレームを返す"""
    plug = f"{node}.{attr}"
    frame = start_frame
    for value in values:
        cmds.setAttr(plug, value)
        cmds.setKeyframe(plug, time=frame)
        frame += span
    return frame


def _key_pair_same(left_node, right_node, attr, values, start_frame, span):
    """左右を同じ値で同時にキーする"""
    frame = start_frame
    for value in values:
        left_plug = f"{left_node}.{attr}"
        right_plug = f"{right_node}.{attr}"
        cmds.setAttr(left_plug, value)
        cmds.setAttr(right_plug, value)
        cmds.setKeyframe(left_plug, time=frame)
        cmds.setKeyframe(right_plug, time=frame)
        frame += span
    return frame


def _mirror_sign_for_attr(attr):
    """pair_mirror時の右側符号。scaleは左右同値、rotateは反転"""
    if attr in _SCALE_ATTRS:
        return 1
    return -1


def _key_pair_mirror(left_node, right_node, attr, values, start_frame, span, mirror_sign=-1):
    """左右を符号反転して同時にキーする"""
    frame = start_frame
    for value in values:
        left_value = value
        right_value = value * mirror_sign

        left_plug = f"{left_node}.{attr}"
        right_plug = f"{right_node}.{attr}"
        cmds.setAttr(left_plug, left_value)
        cmds.setAttr(right_plug, right_value)
        cmds.setKeyframe(left_plug, time=frame)
        cmds.setKeyframe(right_plug, time=frame)
        frame += span
    return frame


def _key_pair_offset(left_node, right_node, attr, values, start_frame, span, gap_frame):
    """左右を時間差でキーする"""
    frame = _key_sequence(left_node, attr, values, start_frame, span)
    frame += gap_frame
    frame = _key_sequence(right_node, attr, values, frame, span)
    return frame


def _get_pair_mode(node, attr, pair_modes):
    """UIまたはデフォルトからpair_modeを取得する"""
    node_modes = pair_modes.get(node, {})
    if attr in node_modes:
        return node_modes[attr]
    return "single"


def _make_pair_key(node, attr, all_nodes, pair_rules, pair_modes):
    """ペア処理の重複防止キーを作る"""
    mode = _get_pair_mode(node, attr, pair_modes)
    if mode not in _PAIR_MODES:
        return (node, attr)

    pair_node = find_pair_node(node, all_nodes, pair_rules)
    if pair_node is None:
        return (node, attr)

    pair_nodes = tuple(sorted([node, pair_node]))
    return (pair_nodes, attr)


def _get_values(node, attr, template, initial_values, value_overrides=None):
    """テンプレートのparts定義からvaluesを取得する。なければデフォルト値"""
    if value_overrides:
        node_values = value_overrides.get(node, {})
        if attr in node_values:
            values = list(node_values[attr])
            if initial_values:
                neutral = initial_values.get(node, {}).get(attr)
                if neutral is not None and values:
                    values[0] = neutral
                    values[-1] = neutral
            return values

    part_tests = _find_part_tests(node, attr, template)
    if part_tests and "values" in part_tests:
        values = list(part_tests["values"])
        if initial_values:
            neutral = initial_values.get(node, {}).get(attr)
            if neutral is not None:
                values[0] = neutral
                values[-1] = neutral
        return values

    if attr in _ROTATE_ATTRS:
        base = list(_DEFAULT_ROTATE_VALUES)
    elif attr in _TRANSLATE_ATTRS:
        base = list(_DEFAULT_TRANSLATE_VALUES)
    else:
        base = list(_DEFAULT_SCALE_VALUES)

    if initial_values:
        neutral = initial_values.get(node, {}).get(attr)
        if neutral is not None:
            base[0] = neutral
            base[-1] = neutral
    return base


def _get_span(node, attr, template, default_span):
    """テンプレートのparts定義からspanを取得する。なければdefault_span"""
    part_tests = _find_part_tests(node, attr, template)
    if part_tests and "span" in part_tests:
        return part_tests["span"]
    return default_span


def _add_metadata_target(metadata_targets, node, attr, start_frame, end_frame):
    """メタデータにノード・attrを追加または更新する"""
    for entry in metadata_targets:
        if entry["node"] != node:
            continue
        if attr not in entry["attrs"]:
            entry["attrs"].append(attr)
        entry["start_frame"] = min(entry["start_frame"], start_frame)
        entry["end_frame"] = max(entry["end_frame"], end_frame)
        return

    metadata_targets.append({
        "node": node,
        "attrs": [attr],
        "start_frame": start_frame,
        "end_frame": end_frame,
    })


def _infer_pair_mode_for_node(node, template):
    """プリセットのparts定義からノードのpair_modeを推定する"""
    parts = template.get("parts", {})
    for part_data in parts.values():
        patterns = (
            part_data.get("patterns", [])
            + part_data.get("left_patterns", [])
            + part_data.get("right_patterns", [])
        )
        if match_any_pattern(node, patterns):
            return part_data.get("pair_mode", "single")
    return "single"


def _find_part_tests(node, attr, template):
    """templateのpartsからノードにマッチするpartのattr設定を返す"""
    parts = template.get("parts", {})
    for part_data in parts.values():
        patterns = (
            part_data.get("patterns", [])
            + part_data.get("left_patterns", [])
            + part_data.get("right_patterns", [])
        )
        if not match_any_pattern(node, patterns):
            continue
        tests = part_data.get("tests", {})
        if attr in tests:
            return tests[attr]
    return None
