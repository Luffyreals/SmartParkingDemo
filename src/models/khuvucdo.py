from dataclasses import dataclass
from typing import Optional

@dataclass
class KhuVucDo:
    id: Optional[int] = None
    idbdx: Optional[int] = None
    ten: str = ""
