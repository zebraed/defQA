"""Controller Setからノードを収集し、keyable TRS attrを抽出するモジュール"""
from maya import cmds

from .attr_filter import filter_attrs, ALL_TRS_ATTRS


def get_nodes_from_set(set_name):
    """Controller Setからtransformノードを再帰的に収集する"""
    if not cmds.objExists(set_name):
        raise ValueError(f"Set not found: {set_name}")

    members = cmds.sets(set_name, query=True)
    nodes = []
    for member in members:
        if cmds.nodeType(member) == "objectSet":
            nodes.extend(get_nodes_from_set(member))
        elif cmds.nodeType(member) in ("transform", "joint"):
            long_names = cmds.ls(member, long=True) or [member]
            nodes.append(long_names[0])
    return nodes


def scan_controller_set(set_name, enable_translate=True, enable_rotate=True, enable_scale=False):
    """
    Controller Setをスキャンし、{node: [attrs]}のdictを返す。

    Args:
        set_name: Controller Set名
        enable_translate: 後方互換のため残す（keyableなtranslateは常に含まれる）
        enable_rotate: rotateX/Y/Zを対象にするか
        enable_scale: 後方互換のため残す（keyableなscaleは常に含まれる）

    Returns:
        dict: {node_name: [attr_name, ...]}
    """
    nodes = get_nodes_from_set(set_name)
    result = {}
    for node in nodes:
        attrs = filter_attrs(
            node,
            ALL_TRS_ATTRS,
            enable_translate=enable_translate,
            enable_rotate=enable_rotate,
            enable_scale=enable_scale,
        )
        if attrs:
            result[node] = attrs
    return result
