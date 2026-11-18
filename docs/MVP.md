# MVP (Minimum Viable Product) Định nghĩa

Mục tiêu: Xây dựng Dashboard web kết nối trực tiếp tới `dbptit`, đáp ứng đầy đủ luồng giám sát, giao dịch vào/ra và thống kê doanh thu.

## 1. Phạm vi MVP (Đã hoàn thành)
- [x] **Kết nối Database**: Truy vấn và thực thi transaction ổn định với `dbptit` trên TiDB Cloud / MySQL.
- [x] **View Trạng thái**: Hiển thị KPI tổng quan, sơ đồ trực quan các vị trí đỗ trống/đang sử dụng và danh sách xe đang gửi.
- [x] **Nghiệp vụ Vào / Ra & Vé tháng**: Hỗ trợ check-in/check-out, tính phí tự động và đăng ký vé tháng.
- [x] **View Giao dịch**: Bảng lịch sử các lượt đỗ xe kèm bộ lọc theo thời gian, bãi đỗ, biển số và trạng thái thanh toán.
- [x] **View Thống kê**: Doanh thu hôm nay, biểu đồ doanh thu theo ngày và cơ cấu theo loại phương tiện.

## 2. Ngoài phạm vi MVP (Hướng phát triển tiếp theo)
- Tích hợp camera AI nhận diện biển số (ALPR).
- Hệ thống cảnh báo tự động qua email/SMS.
- Quản lý phân quyền phức tạp (User Roles) và đăng nhập/đăng ký người dùng.
