# Tài liệu Dự án Nhóm 10

## Thông tin bài tập
- **Đơn vị:** Học viện Công nghệ Bưu chính Viễn thông (PTIT)
- **Lớp:** D24CQCE04-B
- **Học phần:** Cơ sở dữ liệu (Năm học 2026–2027)
- **Giảng viên hướng dẫn:** Nguyễn Trọng Khánh
- **Đề tài:** Hệ thống quản lý bãi đỗ xe thông minh (Smart Parking System Demo)

## Thành viên & Phân công công việc
1. **Nguyễn Hoàng Tùng (`B24DCCE284`)** — Trưởng nhóm, thiết kế kiến trúc hệ thống, thiết kế CSDL `dbptit` (`Dump20261118.sql`), xây dựng `DBService` và logic giao dịch (`check_in_vehicle`, `check_out_vehicle`, `register_monthly_pass`).
2. **Nguyễn Bá Minh Đức (`B24DCCE053`)** — Phát triển tầng nghiệp vụ `ParkingService`, truy vấn thống kê doanh thu/lưu lượng, đồng bộ ràng buộc schema và dữ liệu mẫu.
3. **Trần Anh Tú (`B24DCCE277`)** — Thiết kế và phát triển giao diện 6 trang Streamlit (`src/app.py`), hệ thống CSS/Design System (`src/ui/styles.py`, `src/ui/icons.py`), biểu đồ Altair và trang giới thiệu `index.html`.
4. **Bùi Minh Khang (`B24DCCE137`)** — Xây dựng các dataclass models (`src/models/`), bộ kiểm thử đơn vị (`tests/test_app.py`), kiểm thử tích hợp Web–SQL, viết tài liệu kỹ thuật và kịch bản demo.

## Mô tả hệ thống
Hệ thống demo trực quan hóa cơ sở dữ liệu `dbptit` sử dụng giao diện web với các chức năng chính:
- Giám sát trạng thái bãi xe thời gian thực.
- Quản lý lịch sử giao dịch.
- Báo cáo phân tích doanh thu.
