# Project Plan

## Giai đoạn 1: Chuẩn bị & Khởi tạo (Hoàn thành)
- [x] Thiết lập GitHub Repo (`Luffyreals/SmartParkingDemo`).
- [x] Khởi tạo cấu trúc thư mục (`src`, `docs`, `tests`).
- [x] Soạn thảo tài liệu nền tảng (`README`, `SPEC`, `LICENSE`, `architecture`, `setup-guide`).

## Giai đoạn 2: Phát triển Core Logic & Database (Hoàn thành)
- [x] Thiết lập kết nối TiDB Cloud / MySQL (`mysql-connector-python` qua SSL) trong `src/services/db_service.py`.
- [x] Xây dựng 12 dataclass ánh xạ schema `dbptit` trong `src/models/`.
- [x] Xây dựng nghiệp vụ bãi đỗ xe, transaction vào/ra, tính phí, vé tháng, thống kê và seed dữ liệu mẫu trong `src/services/parking_service.py`.

## Giai đoạn 3: Phát triển Giao diện Dashboard (Hoàn thành)
- [x] Trang 1: Tổng quan & Sơ đồ bãi (KPIs, tình trạng bãi đỗ & khu vực, lưới vị trí đỗ, thêm vị trí mới).
- [x] Trang 2: Vào / Ra bãi xe (Check-in, theo dõi xe đang gửi, ước tính phí và thanh toán check-out).
- [x] Trang 3: Lịch sử giao dịch (Tìm kiếm, lọc đa tiêu chí & xuất CSV).
- [x] Trang 4: Vé tháng & Bảng giá (Đăng ký vé tháng, tra cứu biểu phí).
- [x] Trang 5: Thống kê doanh thu (Biểu đồ doanh thu theo ngày, lưu lượng, loại phương tiện & theo bãi đỗ).
- [x] Trang 6: Nhân sự & Khách gửi xe (Nhân sự, Giảng viên/Sinh viên, Khách vãng lai, Kho thẻ xe, Danh bạ phương tiện).

## Giai đoạn 4: Kiểm thử & Hoàn thiện (Hoàn thành)
- [x] Unit Test (`unittest` — 20 test cases) cho `ParkingService` trong `tests/test_app.py`.
- [x] Nâng cấp UI/UX hiện đại (`src/ui/`, skeleton loading, modern HTML tables) và kiểm thử trực tiếp với TiDB Cloud.
- [x] Tạo trang web tĩnh giới thiệu dự án (`index.html` cho GitHub Pages) và đồng bộ hoàn thiện `README.md` cùng thư mục `docs/`.
