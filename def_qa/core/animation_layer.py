"""Animation Layer管理モジュール"""
from maya import cmds

_DEFAULT_LAYER_NAME = "defQA_anim_layer"


def get_animation_layer_name(options, existing_metadata=None):
    """
    使用するAnimation Layer名を返す。なかったらNone。

    Args:
        options: preset options dict
        existing_metadata: 既存メタデータ。同一レイヤー名を継続利用する
    """
    if not options.get("use_animation_layer", False):
        return None

    layer_name = options.get("animation_layer_name", _DEFAULT_LAYER_NAME)
    if not isinstance(layer_name, str):
        return None

    layer_name = layer_name.strip()
    if not layer_name:
        return None

    if existing_metadata:
        stored = existing_metadata.get("animation_layer")
        if isinstance(stored, str) and stored.strip():
            return stored.strip()

    return layer_name


def ensure_animation_layer(layer_name):
    """
    Animation Layerを取得または新規作成する。

    Returns:
        str or None: 用意できたレイヤー名
    """
    if not layer_name:
        return None

    if cmds.objExists(layer_name):
        node_type = cmds.nodeType(layer_name)
        if node_type == "animLayer":
            return layer_name
        cmds.warning(
            f"defQA: '{layer_name}' is not an animLayer ({node_type})"
        )
        return None

    try:
        cmds.animLayer(layer_name)
        return layer_name
    except Exception as exc:
        cmds.warning(
            f"defQA: Failed to create Animation Layer '{layer_name}': {exc}"
        )
        return None


def add_targets_to_layer(layer_name, targets):
    """targets内の全plugをAnimation Layerに登録する"""
    if not layer_name or not cmds.objExists(layer_name):
        return

    for node, attrs in targets.items():
        if not cmds.objExists(node):
            continue
        for attr in attrs:
            if not cmds.attributeQuery(attr, node=node, exists=True):
                continue
            plug = f"{node}.{attr}"
            try:
                cmds.animLayer(layer_name, edit=True, attribute=plug)
            except Exception:
                pass


def activate_animation_layer(layer_name):
    """指定Animation Layerをアクティブにする"""
    if not layer_name or not cmds.objExists(layer_name):
        return
    if cmds.nodeType(layer_name) != "animLayer":
        return
    try:
        cmds.animLayer(layer_name, edit=True, selected=True, preferred=True)
    except Exception:
        pass


def select_base_animation_layer():
    """ベースAnimation Layerを選択する"""
    try:
        root_layer = cmds.animLayer(query=True, root=True)
    except Exception:
        root_layer = None

    if root_layer:
        try:
            cmds.animLayer(
                root_layer,
                edit=True,
                selected=True,
                preferred=True,
            )
            return
        except Exception:
            pass

    try:
        cmds.animLayer(
            "baseAnimation",
            edit=True,
            selected=True,
            preferred=True,
        )
    except Exception:
        pass


def setup_generation_layer(options, existing_metadata, targets):
    """
    生成前にAnimation Layerを用意し、対象attrを登録する。

    Returns:
        str or None: 使用するAnimation Layer名
    """
    layer_name = get_animation_layer_name(options, existing_metadata)
    if not layer_name:
        return None

    layer = ensure_animation_layer(layer_name)
    if layer is None:
        return None

    add_targets_to_layer(layer, targets)
    activate_animation_layer(layer)
    return layer


def delete_animation_layer(layer_name):
    """Animation Layerノードを削除する"""
    if not layer_name or not cmds.objExists(layer_name):
        return False
    if cmds.nodeType(layer_name) != "animLayer":
        return False
    try:
        cmds.delete(layer_name)
        return True
    except Exception as exc:
        cmds.warning(
            f"defQA: Failed to delete Animation Layer '{layer_name}': {exc}"
        )
        return False
