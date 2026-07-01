"""UIデータクラス"""
from dataclasses import dataclass, field
from typing import List


@dataclass
class AttrItem:
    """テーブルビュー用のattrデータ"""
    attr: str
    enabled: bool = True
    part: str = ""
    side: str = ""
    values: List[float] = field(default_factory=list)
    pair_mode: str = "single"


@dataclass
class ControllerItem:
    """ツリービュー用のコントローラーデータ"""
    node: str
    enabled: bool = True
    muted: bool = False
    attrs: List[AttrItem] = field(default_factory=list)
