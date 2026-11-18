# Setup Guide

## 1. Yêu cầu hệ thống
- Python 3.x
- MySQL Database

## 2. Các bước cài đặt
1. **Clone repo:** `git clone https://github.com/Luffyreals/SmartParkingDemo.git`
2. **Cấu hình môi trường:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Hoặc venv\Scripts\activate trên Windows
   pip install -r requirements.txt
   ```
3. **Cấu hình Database:**
   - Chạy script `dbptit` trong MySQL.
   - Cập nhật thông tin kết nối trong `src/services/db_service.py`.

4. **Chạy ứng dụng:**
   ```bash
   streamlit run src/app.py
   ```
