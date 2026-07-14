"""Time Slider Bookmark管理モジュール"""
from maya import cmds


BOOKMARK_PREFIX = "defQA_"

_BOOKMARK_COLORS = [
    (0.36, 0.75, 0.45),
    (0.30, 0.60, 0.95),
    (0.85, 0.55, 0.25),
    (0.70, 0.40, 0.85),
    (0.90, 0.75, 0.30),
    (0.45, 0.80, 0.80),
    (0.85, 0.45, 0.45),
    (0.55, 0.55, 0.55),
]


def ensure_bookmark_plugin():
    """timeSliderBookmarkプラグインをロードする"""
    try:
        if not cmds.pluginInfo("timeSliderBookmark", q=True, loaded=True):
            cmds.loadPlugin("timeSliderBookmark", quiet=True)
        return True
    except Exception:
        return False


def create_bookmarks_from_targets(metadata_targets, template=None, existing_bookmarks=None):
    """
    生成メタデータからコントローラーごとのTime Slider Bookmarkを作成する。

    Args:
        metadata_targets: build_animationが返すtargetsリスト
        template: 未使用
        existing_bookmarks: 既存Bookmarkノード名リスト

    Returns:
        list: 作成したtimeSliderBookmarkノード名
    """
    if not metadata_targets:
        return []

    if not ensure_bookmark_plugin():
        cmds.warning("defQA: Failed to load the timeSliderBookmark plugin")
        return []

    try:
        from maya.plugin.timeSliderBookmark.timeSliderBookmark import createBookmark
    except ImportError:
        cmds.warning("defQA: Failed to import the timeSliderBookmark API")
        return []

    bookmark_nodes = []
    used_names = _collect_used_bookmark_names(existing_bookmarks)

    for index, target in enumerate(metadata_targets):
        node = target.get("node", "")
        if not node:
            continue

        start_frame = target.get("start_frame", 0)
        end_frame = target.get("end_frame", start_frame)
        bookmark_name = _bookmark_name_for_node(node, used_names)
        color = _BOOKMARK_COLORS[index % len(_BOOKMARK_COLORS)]

        try:
            bm_node = createBookmark(
                name=bookmark_name,
                start=int(start_frame),
                stop=int(end_frame),
                color=color,
            )
            if bm_node:
                bookmark_nodes.append(bm_node)
        except Exception as exc:
            print(f"[defQA] Failed to create bookmark '{bookmark_name}': {exc}")

    return bookmark_nodes


def delete_bookmarks(bookmark_nodes):
    """指定したBookmarkノードを削除する"""
    if not bookmark_nodes:
        return
    existing = [node for node in bookmark_nodes if cmds.objExists(node)]
    if existing:
        cmds.delete(existing)


def delete_defqa_bookmarks(metadata=None):
    """defQAが作成したBookmarkを削除する"""
    if metadata:
        stored = metadata.get("bookmarks")
        if stored:
            delete_bookmarks(stored)
            return

    try:
        if not cmds.pluginInfo("timeSliderBookmark", q=True, loaded=True):
            return
    except Exception:
        return

    nodes = cmds.ls(type="timeSliderBookmark")
    for node in nodes:
        if not cmds.attributeQuery("name", node=node, exists=True):
            continue
        name = cmds.getAttr(f"{node}.name")
        if isinstance(name, str) and name.startswith(BOOKMARK_PREFIX):
            cmds.delete(node)


def _collect_used_bookmark_names(existing_bookmark_nodes):
    """既存Bookmark名から使用済み名辞書を作る"""
    used_names = {}
    for bm_node in existing_bookmark_nodes:
        if not cmds.objExists(bm_node):
            continue
        if not cmds.attributeQuery("name", node=bm_node, exists=True):
            continue
        name = cmds.getAttr(f"{bm_node}.name")
        if not isinstance(name, str):
            continue
        if not name.startswith(BOOKMARK_PREFIX):
            continue

        base_name = name
        tail = name[len(BOOKMARK_PREFIX):]
        parts = tail.rsplit("_", 1)
        if len(parts) == 2 and parts[1].isdigit():
            base_name = BOOKMARK_PREFIX + parts[0]
            suffix = int(parts[1])
            current = used_names.get(base_name, 0)
            if suffix > current:
                used_names[base_name] = suffix
            continue

        current = used_names.get(base_name, 0)
        if current < 1:
            used_names[base_name] = 1
    return used_names


def _bookmark_name_for_node(node, used_names):
    """コントローラー名から一意なBookmark名を作る"""
    short_name = node.split("|")[-1]
    base_name = f"{BOOKMARK_PREFIX}{short_name}"
    if base_name not in used_names:
        used_names[base_name] = 1
        return base_name

    used_names[base_name] += 1
    suffix = used_names[base_name]
    return f"{base_name}_{suffix}"
