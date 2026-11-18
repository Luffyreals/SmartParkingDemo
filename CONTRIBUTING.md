# Hướng dẫn đóng góp (Contributing)

Cảm ơn bạn đã quan tâm và đóng góp cho **Smart Parking System Demo (Nhóm 10 — PTIT)**. Tài liệu này mô tả quy trình làm việc và các tiêu chuẩn kỹ thuật cần tuân thủ khi gửi thay đổi.

## 1. Thiết lập môi trường phát triển

```powershell
git clone https://github.com/Luffyreals/SmartParkingDemo.git
cd SmartParkingDemo
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Tạo tệp cấu hình cục bộ `.streamlit/secrets.toml` (tệp này đã được bỏ qua trong `.gitignore`, **tuyệt đối không commit** thông tin kết nối cơ sở dữ liệu lên Git).

## 2. Quy chuẩn kiến trúc & mã nguồn

- **Tách lớp rõ ràng:**
  - `src/app.py` và `src/ui/`: chỉ xử lý giao diện Streamlit, CSS, icon SVG và biểu đồ Altair; không viết câu lệnh SQL trực tiếp tại đây.
  - `src/services/parking_service.py`: chứa toàn bộ logic nghiệp vụ và truy vấn SQL tham số hóa (`%s`).
  - `src/services/db_service.py`: quản lý kết nối SSL, `fetch_all`, `fetch_one` và `transaction()`.
  - `src/models/`: các `@dataclass` ánh xạ schema `dbptit`.
- **An toàn giao dịch & SQL:**
  - Mọi thao tác thay đổi trạng thái nhiều bảng phải chạy trong `with self.db.transaction() as cursor:` kèm `SELECT ... FOR UPDATE`.
  - Các truy vấn có `GROUP BY` phải tuân thủ `sql_mode=only_full_group_by` của TiDB / MySQL 8.x.
  - Truy vấn lượt xe đang gửi xác định qua `NOT EXISTS (SELECT 1 FROM thanhtoan tt WHERE tt.idld = ld.id)` (không dựa vào `luotdo.giora IS NULL`).

## 3. Quy trình Commit & Pull Request

1. Tạo nhánh mới từ `main`: `git checkout -b feat/<ten-tinh-nang>` hoặc `fix/<ten-loi>`.
2. Viết commit message theo chuẩn **Conventional Commits**:
   - `feat(ui): ...` — thêm tính năng giao diện
   - `fix(parking): ...` — sửa lỗi nghiệp vụ / SQL
   - `docs: ...` — cập nhật tài liệu
   - `test: ...` — bổ sung hoặc chỉnh sửa kiểm thử
3. Chạy kiểm tra cú pháp và toàn bộ unit test trước khi đẩy code:

```powershell
.venv\Scripts\python.exe -m py_compile src/app.py src/services/parking_service.py src/services/db_service.py
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

4. Mở Pull Request vào nhánh `main`, mô tả rõ phạm vi thay đổi và kết quả kiểm thử.
