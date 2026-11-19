# Tài liệu Dự án Nhóm 10

## Thông tin bài tập
- **Đơn vị:** Học viện Công nghệ Bưu chính Viễn thông (PTIT)
- **Lớp:** D24CQCE04-B
- **Học phần:** Cơ sở dữ liệu (Năm học 2026–2027)
- **Giảng viên hướng dẫn:** Nguyễn Trọng Khánh
- **Đề tài:** Hệ thống quản lý bãi đỗ xe thông minh (Smart Parking System Demo)

## Thành viên & Phân công công việc
1. **Nguyễn Hoàng Tùng (`B24DCCE284`)** — Trưởng nhóm, thiết kế kiến trúc 3 tầng, xây dựng `DBService` (`src/services/db_service.py`), cơ chế giao dịch khóa dòng (`SELECT ... FOR UPDATE` trong `check_in_vehicle`, `check_out_vehicle`, `register_monthly_pass`) và điều phối tổng thể dự án.
2. **Nguyễn Bá Minh Đức (`B24DCCE053`)** — Phụ trách phần SQL và cơ sở dữ liệu `dbptit`: thiết kế, chuẩn hóa lược đồ 13 bảng (`Dump20261118.sql`), ràng buộc khóa ngoại/độ dài, bộ dữ liệu mẫu chuẩn, các câu truy vấn SQL thống kê doanh thu/lưu lượng (`ONLY_FULL_GROUP_BY`) và bộ câu lệnh SQL đối chứng Web–SQL.
3. **Trần Anh Tú (`B24DCCE277`)** — Thiết kế và phát triển giao diện 6 trang Streamlit (`src/app.py`), hệ thống CSS/Design System (`src/ui/styles.py`, `src/ui/icons.py`), biểu đồ Altair và trang giới thiệu `index.html`.
4. **Bùi Minh Khang (`B24DCCE137`)** — Xây dựng các dataclass models (`src/models/`), bộ 29 unit tests (`tests/test_app.py`), kiểm thử tích hợp Web–SQL, viết tài liệu kỹ thuật và kịch bản demo.

## Mô tả hệ thống
Hệ thống demo trực quan hóa cơ sở dữ liệu `dbptit` sử dụng giao diện web với các chức năng chính:
- Giám sát trạng thái bãi xe thời gian thực.
- Quản lý lịch sử giao dịch.
- Báo cáo phân tích doanh thu.
