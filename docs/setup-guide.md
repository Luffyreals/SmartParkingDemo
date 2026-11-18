# Setup Guide

## 1. Yêu cầu hệ thống
- Python 3.10 trở lên
- Kết nối tới TiDB Cloud (`dbptit`) hoặc MySQL Server 8.x

## 2. Các bước cài đặt và chạy ứng dụng

1. **Clone repository:**
   ```bash
   git clone https://github.com/Luffyreals/SmartParkingDemo.git
   cd SmartParkingDemo
   ```

2. **Tạo và kích hoạt môi trường ảo:**
   ```powershell
   python -m venv .venv
   # Windows PowerShell:
   .\.venv\Scripts\Activate.ps1
   # Linux / macOS:
   # source .venv/bin/activate
   ```

3. **Cài đặt dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Khởi tạo Database (nếu dùng database mới):**
   - Nạp file `Dump20261118.sql` vào TiDB Cloud hoặc MySQL Server để tạo schema `dbptit` cùng dữ liệu danh mục nền (`baidoxe`, `khuvucdo`, `vitrido`, `banggia`, `loaikhachhang`, `loaiphuongtien`).

5. **Cấu hình thông tin kết nối:**
   Ứng dụng ưu tiên đọc biến môi trường `TIDB_*`, nếu không có sẽ đọc `.streamlit/secrets.toml`.

   - **Cách 1 (Khuyên dùng cho local):** Tạo file `.streamlit/secrets.toml`:
     ```toml
     [tidb]
     host = "gateway01.ap-northeast-1.prod.aws.tidbcloud.com"
     port = 4000
     database = "dbptit"
     user = "<your_username>"
     password = "<your_password>"
     ```
   - **Cách 2:** Thiết lập biến môi trường:
     ```powershell
     $env:TIDB_HOST = "gateway01.ap-northeast-1.prod.aws.tidbcloud.com"
     $env:TIDB_PORT = "4000"
     $env:TIDB_DATABASE = "dbptit"
     $env:TIDB_USER = "<your_username>"
     $env:TIDB_PASSWORD = "<your_password>"
     ```

6. **Chạy ứng dụng Streamlit:**
   ```bash
   streamlit run src/app.py
   ```
   Mở trình duyệt tại `http://localhost:8501`. Nếu các bảng giao dịch còn trống, bấm **Khởi tạo dữ liệu mẫu** ở thanh sidebar để nạp nhanh nhân viên, thẻ xe, khách hàng, vé tháng và lượt đỗ mẫu.

7. **Chạy Unit Tests:**
   ```bash
   python -m unittest discover -s tests -v
   ```
