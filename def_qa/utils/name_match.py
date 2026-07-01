"""名前パターンマッチングユーティリティ"""
import fnmatch


def match_pattern(name, pattern):
    """
    ワイルドカードパターンでノード名にマッチする。
    DAGパス全体ではなく末尾ノード名だけを対象にする。

    Args:
        name: Mayaノード名（namespace・DAGパス含む可能性あり）
        pattern: fnmatch形式のワイルドカードパターン

    Returns:
        bool
    """
    dag_leaf_name = name.split("|")[-1]
    short_name = dag_leaf_name.split(":")[-1]
    return (
        fnmatch.fnmatch(dag_leaf_name, pattern)
        or fnmatch.fnmatch(short_name, pattern)
    )


def match_any_pattern(name, patterns):
    """
    いずれかのパターンにマッチするか確認する。

    Args:
        name: Mayaノード名
        patterns: パターンリスト

    Returns:
        bool
    """
    return any(match_pattern(name, p) for p in patterns)


def find_matching_nodes(nodes, patterns):
    """
    パターンリストにマッチするノードのリストを返す。

    Args:
        nodes: ノード名リスト
        patterns: パターンリスト

    Returns:
        list: マッチしたノード名リスト
    """
    matched = []
    for node in nodes:
        if match_any_pattern(node, patterns):
            matched.append(node)
    return matched
