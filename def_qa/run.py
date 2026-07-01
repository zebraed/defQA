"""defQA メイン実行モジュール"""
from maya import cmds

from .core.attr_filter import exclude_scale_attrs, exclude_translate_attrs
from .core.scanner import scan_controller_set
from .core.template_loader import load_preset, get_preset_path, get_override_path
from .core.animation_layer import setup_generation_layer
from .core.animation_builder import (
    capture_initial_values,
    restore_initial_values,
    build_animation,
    delete_generated_keys,
    restore_pose_from_metadata,
    expand_targets_for_pairs,
    infer_pair_modes,
)
from .core.bookmark import create_bookmarks_from_targets, delete_defqa_bookmarks
from .core.metadata import (
    load_metadata,
    clear_metadata,
    get_generation_start_frame,
    record_generation,
)


def generate(controller_set, preset_name=None, override_name=None, **overrides):
    """
    チェック用アニメーションを生成する。

    Args:
        controller_set: Controller Set名
        preset_name: プリセット名（Noneの場合はデフォルト設定を使用）
        override_name: キャラクターoverrideプリセット名
        **overrides: timelineまたはoptionsのキーを上書き可能
                     例: start_frame=101, default_span=10, enable_scale=True

    Returns:
        dict or None: 生成したメタデータ。対象が見つからない場合はNone
    """
    preset_path = get_preset_path(preset_name) if preset_name else None
    override_path = get_override_path(override_name) if override_name else None
    preset = load_preset(preset_path, override_path=override_path)

    timeline = preset["timeline"]
    options = preset["options"]

    # overridesでtimeline/optionsを上書き
    for key, val in overrides.items():
        if key in timeline:
            timeline[key] = val
        elif key in options:
            options[key] = val

    targets = scan_controller_set(
        controller_set,
        enable_rotate=options.get("enable_rotate", True),
    )

    if not options.get("enable_translate", True):
        targets = exclude_translate_attrs(targets)

    if not options.get("enable_scale", False):
        targets = exclude_scale_attrs(targets)

    if not targets:
        cmds.warning(f"defQA: No keyable TRS attrs found in set: {controller_set}")
        return None

    all_nodes = list(targets.keys())
    pair_rules = preset.get("pair_rules", [])
    pair_modes = infer_pair_modes(targets, preset)
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
        options,
        existing_metadata,
        expanded_targets,
    )
    if options.get("use_animation_layer") and animation_layer is None:
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
        pair_modes=pair_modes,
        pair_rules=pair_rules,
        all_nodes=all_nodes,
    )

    if options.get("return_to_neutral", timeline.get("return_to_neutral", True)):
        restore_initial_values(
            expanded_targets,
            initial_values,
            animation_layer=animation_layer,
        )

    bookmark_nodes = []
    if options.get("create_time_slider_bookmarks", False):
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
    print(
        f"[defQA] Generated: frame {start_frame} - {end_frame}  "
        f"(total {metadata['start_frame']}-{metadata['end_frame']})"
        f"{'' if not animation_layer else f'  layer={animation_layer}'}"
    )
    return metadata


def delete(metadata=None):
    """
    生成したアニメーションキーを削除する。

    Args:
        metadata: 削除対象のメタデータ。Noneの場合はシーンから読み込む
    """
    if metadata is None:
        metadata = load_metadata()

    if metadata is None:
        cmds.warning("defQA: No generated animation metadata found.")
        return

    delete_generated_keys(metadata)
    restore_pose_from_metadata(metadata)
    delete_defqa_bookmarks(metadata)
    clear_metadata()
    print("[defQA] Deleted generated animation.")
