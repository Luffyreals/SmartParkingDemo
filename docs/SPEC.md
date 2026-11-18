# Technical Specification

## 1. Tổng quan dự án
Ứng dụng dashboard web quản lý bãi xe, trực quan hóa dữ liệu từ database `dbptit`.

## 2. Kiến trúc hệ thống
- **Frontend**: Streamlit (Python).
- **Backend**: Python scripts xử lý logic nghiệp vụ và truy vấn DB.
- **Database**: MySQL (local hoặc remote), sử dụng `mysql-connector-python`.

## 3. Các thành phần chính
- **Parking Monitor**: Theo dõi trạng thái xe vào/ra, slot trống (Real-time).
- **Transaction Manager**: Quản lý lịch sử vé, tính phí, tìm kiếm theo thời gian.
- **Analytics Dashboard**: Biểu đồ doanh thu theo ngày/tháng, lưu lượng khách.

## 4. Database Schema (dbptit)
- **Tables**: `baidoxe`, `banggia`, `khachhang`, `khuvucdo`, `loaikhachhang`, `loaiphuongtien`, `luotdo`, `nhanvien`, `phuongtien`, `thanhtoan`, `thexe`, `vethang`, `vitrido`.
- **Primary/Foreign Keys**: Đảm bảo toàn vẹn dữ liệu cho các giao dịch đỗ xe.

## 5. Môi trường triển khai
- OS: Windows/Linux
- Python 3.x
- Dependencies: `streamlit`, `mysql-connector-python`, `pandas`, `plotly`.
