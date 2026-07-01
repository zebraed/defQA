"""SettingsビューからプリセットYAML用dictを組み立てる"""
import copy

from ..utils.name_match import match_any_pattern


def node_to_pattern(node):
    """ノード名からプリセット用のglobパターンを作る"""
    short_name = node.split("|")[-1]
    return f"*{short_name}*"


def _primary_part_name(ctrl_item):
    for attr_item in ctrl_item.attrs:
        if attr_item.part:
            return attr_item.part
    return ""


def _primary_side(ctrl_item, part_name):
    for attr_item in ctrl_item.attrs:
        if attr_item.part == part_name and attr_item.side:
            return attr_item.side
    return ""


def _primary_pair_mode(ctrl_item, part_name):
    for attr_item in ctrl_item.attrs:
        if attr_item.part == part_name and attr_item.pair_mode:
            return attr_item.pair_mode
    return "single"


def node_matches_part(node, part_data):
    """part_dataのpatterns定義にノードが属するか"""
    if not isinstance(part_data, dict):
        return False

    left_patterns = part_data.get("left_patterns", [])
    if match_any_pattern(node, left_patterns):
        return True

    right_patterns = part_data.get("right_patterns", [])
    if match_any_pattern(node, right_patterns):
        return True

    patterns = part_data.get("patterns", [])
    if match_any_pattern(node, patterns):
        return True

    return False


def is_controller_muted(node, preset):
    """プリセット定義からコントローラーのMute状態を返す"""
    parts = preset.get("parts", {})
    if not isinstance(parts, dict):
        return False

    for part_data in parts.values():
        if not node_matches_part(node, part_data):
            continue

        if part_data.get("muted"):
            return True

        muted_patterns = part_data.get("muted_patterns", [])
        if muted_patterns and match_any_pattern(node, muted_patterns):
            return True

    return False


def _build_mute_fields(controllers):
    """部位内コントローラーのMute状態からYAML用フィールドを作る"""
    muted_controllers = [ctrl_item for ctrl_item in controllers if ctrl_item.muted]
    if not muted_controllers:
        return {}

    unmuted_controllers = [ctrl_item for ctrl_item in controllers if not ctrl_item.muted]
    if not unmuted_controllers:
        return {"muted": True}

    muted_patterns = []
    seen_patterns = set()
    for ctrl_item in muted_controllers:
        pattern = node_to_pattern(ctrl_item.node)
        if pattern in seen_patterns:
            continue
        seen_patterns.add(pattern)
        muted_patterns.append(pattern)

    if not muted_patterns:
        return {}

    return {"muted_patterns": sorted(muted_patterns)}


def build_parts_from_controllers(ctrl_items, base_parts=None, default_span=8):
    """
    ControllerItemリストからpartsセクションを組み立てる。

    Settingsビューで編集されたPart/Side/Values/Pairを反映する。
    スキャン結果が無い場合はbase_partsをそのまま返す。
    """
    base_parts = base_parts if base_parts is not None else {}
    if not ctrl_items:
        return copy.deepcopy(base_parts)

    controllers_by_part = {}
    for ctrl_item in ctrl_items:
        part_name = _primary_part_name(ctrl_item)
        if not part_name:
            continue
        if part_name not in controllers_by_part:
            controllers_by_part[part_name] = []
        controllers_by_part[part_name].append(ctrl_item)

    if not controllers_by_part:
        return copy.deepcopy(base_parts)

    parts = {}
    for part_name, controllers in controllers_by_part.items():
        base_part = base_parts.get(part_name, {})
        part_data = {}

        pair_mode = base_part.get("pair_mode", "single")
        ui_pair_mode = _primary_pair_mode(controllers[0], part_name)
        if ui_pair_mode:
            pair_mode = ui_pair_mode
        part_data["pair_mode"] = pair_mode

        left_patterns = []
        right_patterns = []
        patterns = []
        seen_patterns = set()

        for ctrl_item in controllers:
            side = _primary_side(ctrl_item, part_name)
            pattern = node_to_pattern(ctrl_item.node)
            if pattern in seen_patterns:
                continue
            seen_patterns.add(pattern)

            if side == "L":
                left_patterns.append(pattern)
            elif side == "R":
                right_patterns.append(pattern)
            else:
                patterns.append(pattern)

        if left_patterns:
            part_data["left_patterns"] = sorted(left_patterns)
        if right_patterns:
            part_data["right_patterns"] = sorted(right_patterns)
        if patterns:
            part_data["patterns"] = sorted(patterns)

        base_tests = base_part.get("tests", {})
        tests = {}
        for ctrl_item in controllers:
            for attr_item in ctrl_item.attrs:
                if attr_item.part != part_name:
                    continue
                if attr_item.attr in tests:
                    continue

                span = default_span
                base_entry = base_tests.get(attr_item.attr, {})
                if "span" in base_entry:
                    span = base_entry["span"]

                tests[attr_item.attr] = {
                    "values": list(attr_item.values),
                    "span": span,
                }

        if tests:
            part_data["tests"] = tests

        part_data.update(_build_mute_fields(controllers))

        parts[part_name] = part_data

    return parts
