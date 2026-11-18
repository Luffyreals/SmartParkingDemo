# Technical Specification

## 1. Tổng quan dự án
Ứng dụng dashboard web quản lý bãi đỗ xe thông minh, trực quan hóa và thao tác trực tiếp trên cơ sở dữ liệu `dbptit`.

## 2. Kiến trúc hệ thống
- **Frontend (`src/app.py`, `src/ui/`):** Streamlit (Python) với Design System CSS (`styles.py`), SVG icon tối giản (`icons.py`), bảng dữ liệu HTML hiện đại, biểu đồ Altair và xử lý dữ liệu Pandas.
- **Business Logic (`src/services/parking_service.py`):** Xử lý nghiệp vụ vào/ra bãi, tính phí, quản lý vé tháng, quản lý nhân sự/khách hàng/thẻ xe/phương tiện, thống kê doanh thu và khởi tạo dữ liệu mẫu.
- **Data Access (`src/services/db_service.py`):** Đóng gói kết nối TiDB Cloud / MySQL qua `mysql-connector-python` (hỗ trợ SSL, truy vấn đơn và transaction đa câu lệnh).
- **Domain Models (`src/models/`):** Các Python `@dataclass` ánh xạ từng bảng của `dbptit`.
- **Database:** TiDB Cloud Serverless hoặc MySQL 8.x (`dbptit`).

## 3. Các phân hệ chức năng đã triển khai
- **Tổng quan & Sơ đồ bãi:** Theo dõi 5 KPI tổng quan, thẻ công suất từng bãi đỗ kèm địa điểm, tỷ lệ lấp đầy từng khu vực, lưới trạng thái ô đỗ theo bãi/khu vực và thêm mới vị trí đỗ.
- **Vào / Ra bãi xe:** Check-in xe mới (cấp thẻ, gán vị trí đỗ), theo dõi xe đang gửi, ước tính phí theo bảng giá và check-out thanh toán.
- **Lịch sử giao dịch:** Lọc lịch sử lượt đỗ theo ngày, loại xe, biển số, mã thẻ hoặc nhân viên và xuất báo cáo CSV.
- **Vé tháng & Bảng giá:** Đăng ký vé tháng kèm ước tính chi phí, theo dõi thời hạn hiệu lực và tra cứu bảng giá dịch vụ.
- **Thống kê doanh thu:** Biểu đồ doanh thu theo ngày, lưu lượng lượt xe, cơ cấu theo loại phương tiện và doanh thu theo từng bãi đỗ.
- **Nhân sự & Khách gửi xe:** Quản lý nhân sự (`nhanvien`), giảng viên/sinh viên (`khachhang`), khách vãng lai, kho thẻ xe (`thexe`) và danh bạ phương tiện (`phuongtien`).

## 4. Database Schema (`dbptit`)
- **13 bảng chính:** `baidoxe`, `banggia`, `khachhang`, `khuvucdo`, `loaikhachhang`, `loaiphuongtien`, `luotdo`, `nhanvien`, `phuongtien`, `thanhtoan`, `thexe`, `vethang`, `vitrido`.
- **Script khởi tạo:** `Dump20261118.sql`.
- **Khóa chính / Khóa ngoại & Ràng buộc:** Đảm bảo toàn vẹn tham chiếu cho toàn bộ luồng gửi xe, thẻ xe, vị trí đỗ và thanh toán.

## 5. Môi trường triển khai
- **OS:** Windows / Linux / macOS
- **Python:** 3.10+ (đã kiểm chứng trên Python 3.14)
- **Dependencies (`requirements.txt`):** `streamlit`, `pandas`, `mysql-connector-python`
