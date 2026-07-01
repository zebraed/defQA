"""TRS attrフィルタリングモジュール"""
from maya import cmds


ALL_TRS_ATTRS = [
    "translateX", "translateY", "translateZ",
    "rotateX", "rotateY", "rotateZ",
    "scaleX", "scaleY", "scaleZ",
]

_TRANSLATE_ATTRS = frozenset(["translateX", "translateY", "translateZ"])
_ROTATE_ATTRS = frozenset(["rotateX", "rotateY", "rotateZ"])
_SCALE_ATTRS = frozenset(["scaleX", "scaleY", "scaleZ"])


def exclude_scale_attrs(targets):
    """targetsからscale attrを除いたコピーを返す"""
    result = {}
    for node, attrs in targets.items():
        filtered = [attr for attr in attrs if attr not in _SCALE_ATTRS]
        if filtered:
            result[node] = filtered
    return result


def exclude_translate_attrs(targets):
    """targetsからtranslate attrを除いたコピーを返す"""
    result = {}
    for node, attrs in targets.items():
        filtered = [attr for attr in attrs if attr not in _TRANSLATE_ATTRS]
        if filtered:
            result[node] = filtered
    return result


def is_attr_keyable(node, attr):
    """アトリビュートがキー設定可能かを確認する"""
    plug = f"{node}.{attr}"
    if not cmds.attributeQuery(attr, node=node, exists=True):
        return False
    if not cmds.getAttr(plug, keyable=True):
        return False
    if cmds.getAttr(plug, lock=True):
        return False
    if not cmds.getAttr(plug, settable=True):
        return False
    return True


def filter_attrs(node, attrs, enable_translate=True, enable_rotate=True, enable_scale=False):
    """
    アトリビュートリストからkeyable TRS attrのみを返す。

    Translate/Scaleはkeyableならenable_translate/enable_scaleに関わらず常に含める。
    各フラグは生成時の対象フィルタ用（scan結果の除外は呼び出し側で行う）。

    Args:
        node: Mayaノード名
        attrs: フィルタ対象のattr名リスト
        enable_translate: 未使用（後方互換のため残す）
        enable_rotate: rotateを対象にするか
        enable_scale: 未使用（後方互換のため残す）

    Returns:
        list: keyableなattr名リスト
    """
    result = []
    for attr in attrs:
        if attr in _SCALE_ATTRS:
            if is_attr_keyable(node, attr):
                result.append(attr)
            continue
        if attr in _TRANSLATE_ATTRS:
            if is_attr_keyable(node, attr):
                result.append(attr)
            continue
        if attr in _ROTATE_ATTRS and not enable_rotate:
            continue
        if is_attr_keyable(node, attr):
            result.append(attr)
    return result
