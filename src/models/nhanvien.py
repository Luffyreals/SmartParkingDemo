from dataclasses import dataclass
from typing import Optional

@dataclass
class NhanVien:
    id: Optional[int] = None
    idbdx: Optional[int] = None
    hoten: str = ""
    diachi: Optional[str] = None
    ngaysinh: Optional[str] = None
    chucvu: str = ""
    sdt: str = ""
    ngaybatdau: Optional[str] = None
    email: Optional[str] = None
    cccd: Optional[str] = None
