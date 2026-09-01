from search_engine.config import Configuration

class TrieNode:
    def __init__(
            self,
            is_terminal: bool = False
        ):
        self.children: dict[str, TrieNode] = {}
        self.is_terminal: bool = is_terminal

class TrieIndex:
    def __init__(self):
        self._root: TrieNode = TrieNode()

    def prefix_term(self, term: str):
        if len(term) < Configuration.MINIMUM_TERM_LENGHT_TO_PREFIX:
            return

        cur_node: TrieNode = self._root
        for char in term:
            if char not in cur_node.children:
                cur_node.children[char] = TrieNode()
            cur_node = cur_node.children[char]

        cur_node.is_terminal = True

    def terms_with_prefix(self, prefix: str) -> list[str]:
        if len(prefix) < Configuration.MINIMUM_TERM_LENGHT_TO_PREFIX:
            return []

        cur_node: TrieNode = self._root
        for char in prefix:
            if char not in cur_node.children:
                return []
            cur_node = cur_node.children[char]

        suffixs = self._get_suffixs_at(cur_node)

        terms: list[str] = []
        for suffix in suffixs:
            term = prefix + suffix
            terms.append(term)

        return terms

    def merge(self, trie_index: "TrieIndex") -> None:
        my_root = self._root
        other_root = trie_index._root

        stack: list[tuple[TrieNode, TrieNode]] = [(my_root, other_root)]

        while stack:
            cur_node, other_node = stack.pop()

            if other_node.is_terminal:
                cur_node.is_terminal = True

            for char, child in other_node.children.items():
                if char not in cur_node.children:
                    cur_node.children[char] = TrieNode()
                stack.append((cur_node.children[char], child))

    def delete_terms(self, terms: list[str]) -> None:
        for term in terms:
            self.delete_term(term)

    def delete_term(self, term: str) -> None:
        node = self._root
        path: list[tuple[TrieNode, str]] = []

        for char in term:
            child = node.children.get(char)
            if child is None:
                return

            path.append((node, char))
            node = child

        if not node.is_terminal:
            return

        node.is_terminal = False

        for parent, char in reversed(path):
            child = parent.children.get(char)

            if child.is_terminal or child.children:
                return

            del parent.children[char]


    def _get_suffixs_at(self, start_node: TrieNode) -> list[str]:
        suffixes: list[str] = []
        stack: list[tuple[TrieNode, str]] = [(start_node, "")]

        while stack:
            node, suffix = stack.pop()

            if node.is_terminal:
                suffixes.append(suffix)

            for char, child in node.children.items():
                stack.append((child, suffix + char))

        return suffixes
