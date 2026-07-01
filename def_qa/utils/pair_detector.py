"""L/Rペア推定ユーティリティ"""


def leaf_name(node):
    """DAGパスを除いたノード名を返す"""
    return node.split("|")[-1]


def split_namespace(name):
    """namespaceとベース名を返す"""
    if ":" in name:
        namespace, base = name.rsplit(":", 1)
        return namespace + ":", base
    return "", name


def build_node_lookup(nodes):
    """leaf名をキーにしたノード辞書を返す"""
    lookup = {}
    for node in nodes:
        lookup[leaf_name(node)] = node
    return lookup


def find_pair_node(node, known_nodes, pair_rules):
    """
    pair_rulesに基づいて左右ペアノードを探す。

    Args:
        node: 対象ノード
        known_nodes: 検索対象ノードリスト
        pair_rules: [{"left": "_L_", "right": "_R_"}, ...]

    Returns:
        str or None: ペアノード
    """
    if not pair_rules:
        return None

    name = leaf_name(node)
    namespace, base = split_namespace(name)
    lookup = build_node_lookup(known_nodes)

    for rule in pair_rules:
        left = rule.get("left", "")
        right = rule.get("right", "")
        if not left or not right:
            continue

        pair_base = None
        if left in base:
            pair_base = base.replace(left, right, 1)
        elif right in base:
            pair_base = base.replace(right, left, 1)

        if not pair_base:
            continue

        pair_leaf = namespace + pair_base
        if pair_leaf in lookup:
            pair_node = lookup[pair_leaf]
            if pair_node != node:
                return pair_node

    return None
