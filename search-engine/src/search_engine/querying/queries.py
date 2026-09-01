from typing import Protocol
from search_engine.documents import DocumentRef

class QueryVisitor(Protocol):
    def visit_term(self, query: "TermQuery") -> set[DocumentRef]:
        ...

    def visit_and(self, query: "AndQuery") -> set[DocumentRef]:
            ...

    def visit_or(self, query: "OrQuery") -> set[DocumentRef]:
            ...

    def visit_not(self, query: "NotQuery") -> set[DocumentRef]:
            ...

    def visit_prefix(self, query: "PrefixQuery") -> set[DocumentRef]:
            ...

    def visit_phrase(self, query: "PhraseQuery") -> set[DocumentRef]:
            ...

class Query:
    def accept(self, visitor: QueryVisitor) -> set[DocumentRef]:
        raise NotImplementedError

class TermQuery(Query):
    def __init__(self, term: str):
        self.term = term

    def accept(self, visitor: QueryVisitor) -> set[DocumentRef]:
        return visitor.visit_term(self)

class AndQuery(Query):
    def __init__(self, *children: Query):
        self.children = children

    def accept(self, visitor: QueryVisitor) -> set[DocumentRef]:
            return visitor.visit_and(self)

class OrQuery(Query):
    def __init__(self, *children: Query):
        self.children = children

    def accept(self, visitor: QueryVisitor) -> set[DocumentRef]:
            return visitor.visit_or(self)

class NotQuery(Query):
    def __init__(self, child: Query):
        self.child = child

    def accept(self, visitor: QueryVisitor) -> set[DocumentRef]:
            return visitor.visit_not(self)

class PrefixQuery(Query):
    def __init__(self, prefix: str):
         self.prefix = prefix

    def accept(self, visitor: QueryVisitor) -> set[DocumentRef]:
        return visitor.visit_prefix(self)

class PhraseQuery(Query):
    def __init__(self, phrase: str):
        self.phrase = phrase

    def accept(self, visitor: QueryVisitor) -> set[DocumentRef]:
        return visitor.visit_phrase(self)
