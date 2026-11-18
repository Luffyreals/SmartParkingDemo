# Smart Parking System Demo - Nhóm 10

[![Python Version](https://img.shields.io/badge/python-3.x-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 1. Giới thiệu
Dự án được thực hiện nhằm mục đích học tập môn Cơ sở dữ liệu, xây dựng hệ thống quản lý bãi đỗ xe thông minh. Ứng dụng cung cấp bảng điều khiển (Dashboard) trực quan để theo dõi trạng thái bãi xe, lịch sử giao dịch và doanh thu.

## 2. Các tính năng chính
- **Parking Monitor**: Giám sát thời gian thực trạng thái các vị trí đỗ.
- **Transaction History**: Quản lý và lọc dữ liệu giao dịch.
- **Analytics**: Biểu đồ phân tích doanh thu.

## 3. Cấu trúc dự án
```text
SmartParkingDemo/
├── .github/          # CI/CD workflows
├── docs/             # Tài liệu dự án
├── src/              # Mã nguồn chính
│   ├── api/          # Xử lý endpoint/controllers
│   ├── models/       # Định nghĩa dữ liệu (Entities)
│   ├── services/     # Logic nghiệp vụ & DB connector
│   └── utils/        # Hàm hỗ trợ
├── tests/            # Unit tests
├── README.md         # Tài liệu dự án
└── requirements.txt  # Thư viện yêu cầu
```

## 4. Hướng dẫn cài đặt
1. **Clone repository:**
   ```bash
   git clone https://github.com/Luffyreals/SmartParkingDemo.git
   cd SmartParkingDemo
   ```
2. **Thiết lập môi trường:**
   ```bash
   python -m venv venv
   # Windows:
   venv\Scripts\activate
   ```
3. **Cài đặt thư viện:**
   ```bash
   pip install -r requirements.txt
   ```
4. **Chạy ứng dụng:**
   ```bash
   streamlit run src/app.py
   ```

## 5. Thành viên nhóm 10
- Nguyễn Hoàng Tùng (Trưởng nhóm)
- Nguyễn Bá Minh Đức
- Bùi Minh Khang
- Trần Anh Tú
