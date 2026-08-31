from collections import defaultdict
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import AbstractSet, Mapping, Optional, Protocol, runtime_checkable

from document_ref import DocumentRef


@runtime_checkable
class Posting(Protocol):
    """Read-only operations needed by query evaluation."""

    def document_refs(self) -> set[DocumentRef]: ...

    def positions(self, document_ref: DocumentRef) -> AbstractSet[int]: ...

    def frequency(self, document_ref: DocumentRef) -> int: ...

    def document_frequency(self) -> int: ...


@runtime_checkable
class StoredPosting(Posting, Protocol):
    """Posting stored in a buffer or segment, capable of views and snapshots."""

    def view(self) -> Posting: ...

    def freeze(self) -> "FrozenPosting": ...


@dataclass(frozen=True)
class PostingView(Posting):
    """Read-only live view; subsequent source writes are visible through reads."""

    _source: Posting = field(repr=False)

    def document_refs(self) -> set[DocumentRef]:
        return self._source.document_refs()

    def positions(self, document_ref: DocumentRef) -> frozenset[int]:
        return frozenset(self._source.positions(document_ref))

    def frequency(self, document_ref: DocumentRef) -> int:
        return self._source.frequency(document_ref)

    def document_frequency(self) -> int:
        return self._source.document_frequency()


class _PostingReads:
    """Shared reads over mutable or frozen position collections."""

    _positions: Mapping[DocumentRef, AbstractSet[int]]

    def document_refs(self) -> set[DocumentRef]:
        return set(self._positions)

    def positions(self, document_ref: DocumentRef) -> frozenset[int]:
        return frozenset(self._positions.get(document_ref, ()))

    def frequency(self, document_ref: DocumentRef) -> int:
        return len(self._positions.get(document_ref, ()))

    def document_frequency(self) -> int:
        return len(self._positions)


class MutablePosting(_PostingReads, StoredPosting):
    def __init__(self, term: str):
        self.term = term
        self._positions: dict[DocumentRef, set[int]] = defaultdict(set)

    def add(self, document_ref: DocumentRef, index: int) -> None:
        self._positions[document_ref].add(index)

    def add_positions(self, document_ref: DocumentRef, positions: AbstractSet[int]) -> None:
        if document_ref in self._positions:
            raise ValueError(f"Document Id {document_ref.external_id} shouldn't be in different segments")

        self._positions[document_ref] = set(positions)

    def view(self) -> Posting:
        return PostingView(self)

    def freeze(self) -> "FrozenPosting":
        return FrozenPosting(self.term, self._positions)


@dataclass(frozen=True, eq=False, init=False)
class FrozenPosting(_PostingReads, StoredPosting):
    term: str
    _positions: Mapping[DocumentRef, frozenset[int]]

    def __init__(
        self,
        term: str,
        positions: Optional[Mapping[DocumentRef, AbstractSet[int]]] = None,
    ):
        snapshot = {
            ref: frozenset(values)
            for ref, values in (positions if positions is not None else {}).items()
        }
        object.__setattr__(self, "term", term)
        object.__setattr__(self, "_positions", MappingProxyType(snapshot))

    def view(self) -> Posting:
        return self

    def freeze(self) -> "FrozenPosting":
        return self
