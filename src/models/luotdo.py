from dataclasses import dataclass
from typing import Optional

@dataclass
class LuotDo:
    id: Optional[int] = None
    idvtd: int = 0
    giovao: str = ""
    giora: Optional[str] = None
    idnv: int = 0
    idpt: Optional[int] = None
    idtx: Optional[int] = None
    idbg: Optional[int] = None
