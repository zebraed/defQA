"""生成メタ情報のMayaシーンへの保存・読み込みモジュール"""
import json

from maya import cmds


_META_NODE_NAME = "defQA_metadata"
_META_ATTR_NAME = "defQA_data"


def save_metadata(
    start_frame,
    end_frame,
    targets,
    animation_layer=None,
    template_name=None,
    bookmarks=None,
    initial_values=None,
):
    """
    生成メタ情報をMayaのnetworkノードに保存する。

    Args:
        start_frame: 生成アニメーションの開始フレーム
        end_frame: 生成アニメーションの終了フレーム
        targets: [{"node": str, "attrs": [str], "start_frame": int, "end_frame": int}]
        animation_layer: 使用したAnimation Layer名（Noneの場合は不使用）
        template_name: 使用したテンプレート名
        bookmarks: 作成したTime Slider Bookmarkノード名リスト
        initial_values: {node: {attr: value}} 生成前の初期値

    Returns:
        dict: 保存したメタデータ
    """
    data = {
        "generated_by": "defQA",
        "version": "0.1.0",
        "template": template_name,
        "animation_layer": animation_layer,
        "start_frame": start_frame,
        "end_frame": end_frame,
        "targets": targets,
        "bookmarks": list(bookmarks) if bookmarks else [],
        "initial_values": initial_values if initial_values else {},
    }

    node = _get_or_create_meta_node()
    cmds.setAttr(f"{node}.{_META_ATTR_NAME}", json.dumps(data), type="string")
    return data


def load_metadata():
    """
    保存されたメタ情報を読み込む。

    Returns:
        dict or None: メタデータ。未保存の場合はNone
    """
    if not cmds.objExists(_META_NODE_NAME):
        return None
    if not cmds.attributeQuery(_META_ATTR_NAME, node=_META_NODE_NAME, exists=True):
        return None
    json_str = cmds.getAttr(f"{_META_NODE_NAME}.{_META_ATTR_NAME}")
    if not json_str:
        return None
    return json.loads(json_str)


def clear_metadata():
    """メタ情報ノードをシーンから削除する"""
    if cmds.objExists(_META_NODE_NAME):
        cmds.delete(_META_NODE_NAME)


def get_generation_start_frame(existing_metadata, timeline):
    """
    次の生成開始フレームを返す。
    既存メタデータがある場合は末尾の次フレームから開始する。
    """
    if not existing_metadata:
        return timeline.get("start_frame", 1)

    part_gap = timeline.get("part_gap_frame", 10)
    end_frame = existing_metadata.get("end_frame")
    if end_frame is None:
        return timeline.get("start_frame", 1)
    return int(end_frame) + int(part_gap)


def merge_initial_values(existing_values, new_values):
    """初期値をマージする。既存の値は上書きしない"""
    merged = {}
    if existing_values:
        for node, attrs in existing_values.items():
            merged[node] = dict(attrs)

    if not new_values:
        return merged

    for node, attrs in new_values.items():
        if node not in merged:
            merged[node] = {}
        for attr, value in attrs.items():
            if attr not in merged[node]:
                merged[node][attr] = value
    return merged


def record_generation(
    existing_metadata,
    timeline,
    end_frame,
    new_targets,
    new_initial_values,
    new_bookmarks,
    template_name=None,
    animation_layer=None,
):
    """
    生成結果をメタデータに記録する。
    既存メタデータがある場合は追記マージする。
    """
    if existing_metadata is None:
        return save_metadata(
            start_frame=timeline.get("start_frame", 1),
            end_frame=end_frame,
            targets=list(new_targets),
            animation_layer=animation_layer,
            template_name=template_name,
            bookmarks=list(new_bookmarks) if new_bookmarks else [],
            initial_values=new_initial_values if new_initial_values else {},
        )

    start_frame = existing_metadata.get("start_frame", timeline.get("start_frame", 1))
    merged_targets = list(existing_metadata.get("targets", []))
    merged_targets.extend(new_targets)

    merged_bookmarks = list(existing_metadata.get("bookmarks", []))
    if new_bookmarks:
        merged_bookmarks.extend(new_bookmarks)

    merged_initial = merge_initial_values(
        existing_metadata.get("initial_values"),
        new_initial_values,
    )

    if animation_layer is None:
        animation_layer = existing_metadata.get("animation_layer")
    if template_name is None:
        template_name = existing_metadata.get("template")

    return save_metadata(
        start_frame=start_frame,
        end_frame=end_frame,
        targets=merged_targets,
        animation_layer=animation_layer,
        template_name=template_name,
        bookmarks=merged_bookmarks,
        initial_values=merged_initial,
    )


def _get_or_create_meta_node():
    """メタ情報用のnetworkノードを取得または新規作成する"""
    if cmds.objExists(_META_NODE_NAME):
        if not cmds.attributeQuery(_META_ATTR_NAME, node=_META_NODE_NAME, exists=True):
            cmds.addAttr(_META_NODE_NAME, longName=_META_ATTR_NAME, dataType="string")
    else:
        cmds.createNode("network", name=_META_NODE_NAME, ss=True)
        cmds.addAttr(_META_NODE_NAME, longName=_META_ATTR_NAME, dataType="string")
    return _META_NODE_NAME
