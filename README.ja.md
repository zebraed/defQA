<p align="center">
  <img src="def_qa/ui/icons/defqa_icon.svg" alt="defQA" width="96">
</p>

# defQA

[English version](README.md)

Maya上でキャラクターリグのスキニング・可動範囲・リグ挙動を目視確認するためのチェック用アニメーション自動生成ツールです。

<img src="docs/src/defQA_ui_01.png" alt="defQA UI" width="50%">

## 説明

defQAは、Controller Set内のtransformノードを収集し、keyable TRS attrに対してテストアニメーションを自動生成します。各attrには `neutral → +値 → neutral → -値 → neutral` のキーシーケンスを設定し、コントローラーごとにフレームをずらして生成します。生成したキーはメタデータに基づいて安全に削除できます。コントローラー部位分類とテスト値はYAMLプリセットで管理します。

## インストール

AまたはBどちらかでインストールしてください。

### A.Mayaモジュール

1. このリポジトリをMayaのmodulesディレクトリへ `defQA` という名前で配置します。

   - Windows: `%USERPROFILE%\Documents\maya\modules\defQA`
   - macOS: `~/Library/Preferences/Autodesk/maya/modules/defQA`
   - Linux: `~/maya/modules/defQA`

2. リポジトリ内の `defQA.mod` を、同じ `modules` ディレクトリ（`defQA` フォルダの隣）へコピーします。

3. Mayaを再起動します。

再起動後は `sys.path` を変更せずに `import def_qa` できます。

### B.ドラッグ&ドロップ

リポジトリを任意の場所に配置し、`drag-and-drop-install.mel` をMayaのビューポートにドラッグ&ドロップします。現在のシェルフにdefQAを起動するシェルフボタンが追加されます。

### 手動でインポートする場合

単純にリポジトリのディレクトリをPythonパスに追加し、パッケージをimportします。

```python
import sys
sys.path.insert(0, r"/path/to/defQA")

import def_qa
def_qa.showUI()
```

## 依存関係

### Pythonパッケージ

| パッケージ | 必須 | 備考 |
| --- | --- | --- |
| **PyYAML** | 必須 | `def_qa/vendor/` に同梱。システムにインストール済みの場合はそちらを優先します。 |
| **Qt.py** | GUI利用時は必須 | `def_qa/vendor/` に同梱。システムにインストール済みの場合はそちらを優先します。 |

## 使い方

### GUI

```python
import def_qa
def_qa.showUI()
```

### スクリプト

```python
import def_qa

# デフォルト設定で生成（全keyable rotate/translateを対象）
def_qa.generate("controllers_set")

# mGear biped プリセットを使用
def_qa.generate("controllers_set", preset_name="biped_mgear")

# オプションを上書き
def_qa.generate("controllers_set", preset_name="biped_common", start_frame=101, default_span=10)

# 生成したキーを削除
def_qa.delete()

# 利用可能なプリセットを確認
print(def_qa.list_presets())
```

## プリセット

YAMLファイルで部位ごとのコントローラーパターンとテスト値を定義できます。

```yaml
template: biped_mgear
timeline:
  start_frame: 1
  default_span: 8
  gap_frame: 4
  part_gap_frame: 10
  return_to_neutral: true
options:
  enable_translate: true
  enable_rotate: true
  enable_scale: false
parts:
  spine:
    patterns:
      - "*spine_C*_ctl"
    tests:
      rotateX:
        values: [0, 30, 0, -30, 0]
        span: 8
```

独自プリセットは `def_qa/presets/` に配置されます。
