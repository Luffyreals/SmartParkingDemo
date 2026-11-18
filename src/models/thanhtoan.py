from dataclasses import dataclass
from typing import Optional

@dataclass
class ThanhToan:
    id: Optional[int] = None
    idld: int = 0
    chiphi: int = 0
    giothanhtoan: str = ""
    trangthai: str = ""
    idnv: int = 0
    loaithanhtoan: Optional[bool] = None
    idvt: Optional[int] = None
