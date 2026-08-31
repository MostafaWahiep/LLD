from dataclasses import dataclass, field
from uuid import UUID


@dataclass(frozen=True, order=True)
class DocumentRef:
    internal_id: UUID 
    external_id: str = field(compare=False)