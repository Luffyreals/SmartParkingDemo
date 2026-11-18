# Changelog

Tất cả các thay đổi đáng chú ý của dự án **Smart Parking System Demo (Nhóm 10 — PTIT)** được ghi lại tại đây theo chuẩn [Keep a Changelog](https://keepachangelog.com/vi/1.0.0/).

## [1.2.0] - 2026-11-19

### Added
- Trang web tĩnh giới thiệu dự án ([index.html](index.html)) phục vụ trên GitHub Pages.
- Tầng giao diện mới `src/ui/` (`icons.py`, `styles.py`) cùng logo thương hiệu `assets/logo.svg` và cấu hình theme `.streamlit/config.toml`.
- Trang 6 **Nhân sự & Khách gửi xe** với 5 tab chuyên sâu: Nhân sự vận hành (`nhanvien` kèm `cccd`), Giảng viên & Sinh viên (`khachhang`), Khách vãng lai, Kho thẻ xe RFID (`thexe`) và Danh bạ phương tiện (`phuongtien`).
- Thẻ công suất 3 bãi đỗ kèm địa điểm, bảng tỷ lệ lấp đầy từng khu vực (`get_zones_summary`), biểu đồ doanh thu theo bãi đỗ (`get_revenue_by_lot`), hiệu ứng skeleton loading và bộ nhớ đệm TTL.
- Hệ thống 11 bảng dữ liệu HTML hiện đại (`_render_modern_table`) với sticky header, badge biển số và pill trạng thái.
- Bổ sung 6 unit tests mới trong `tests/test_app.py` (tổng cộng 20 test cases).

### Fixed
- Khắc phục lỗi `ONLY_FULL_GROUP_BY` (1055) trong `get_zones_summary()`.
- Sửa điều kiện lọc lượt xe đang gửi trong `get_cards_detail()` và `get_vehicles_detail()` sang `NOT EXISTS (... thanhtoan)` thay cho `giora IS NULL`.
- Chuẩn hóa hiển thị `loaithanhtoan` (`Vé ngày` / `Vé tháng` / `Chưa thanh toán`) trong `get_walkin_visitors()`.
- Tự động `importlib.reload` các module dịch vụ khi Streamlit hot-reload `src/app.py`.

## [1.1.0] - 2026-11-18

### Fixed
- Ngăn chặn lượt đỗ đang hoạt động bị trùng lặp và loại bỏ nhân bản dòng trong truy vấn sơ đồ vị trí đỗ bằng `ROW_NUMBER() OVER (PARTITION BY ld.idvtd ...)`.
- Bổ sung khóa `SELECT ... FOR UPDATE` cho các luồng `check_in_vehicle`, `check_out_vehicle`, `register_monthly_pass`.

## [1.0.0] - 2026-11-18

### Added
- Khởi tạo cấu trúc dự án, schema `Dump20261118.sql` (`dbptit` 13 bảng) và 12 domain models trong `src/models/`.
- Xây dựng `DBService` (kết nối SSL TiDB Cloud / MySQL) và `ParkingService` (nghiệp vụ vào/ra bãi, tính phí, vé tháng, thống kê, seed demo).
- Ra mắt ứng dụng Streamlit đầu tiên cùng bộ tài liệu nền tảng trong `docs/` và unit tests ban đầu trong `tests/test_app.py`.
