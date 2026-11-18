from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Optional

import altair as alt
import pandas as pd
import streamlit as st

from services.db_service import DBConfig, DBService, DatabaseError
from services.parking_service import ParkingService, ValidationError


st.set_page_config(
    page_title="Smart Parking PTIT",
    page_icon="🅿️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .slot-card {
        border-radius: 10px;
        padding: 12px;
        margin-bottom: 10px;
        border: 1px solid rgba(128, 128, 128, 0.2);
    }
    .slot-free {
        background-color: rgba(16, 185, 129, 0.12);
        border-left: 5px solid #10b981;
    }
    .slot-busy {
        background-color: rgba(239, 68, 68, 0.12);
        border-left: 5px solid #ef4444;
    }
    .slot-title {
        font-weight: 700;
        font-size: 1rem;
        margin-bottom: 4px;
    }
    .slot-meta {
        font-size: 0.85rem;
        opacity: 0.85;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def _create_db_service() -> DBService:
    """Create DBService from environment variables or Streamlit secrets."""
    env_db = DBService.from_env()
    if env_db is not None:
        return env_db

    if "tidb" in st.secrets:
        cfg = st.secrets["tidb"]
        return DBService.from_config(
            DBConfig(
                host=str(cfg["host"]),
                port=int(cfg.get("port", 4000)),
                database=str(cfg["database"]),
                user=str(cfg["user"]),
                password=str(cfg["password"]),
            )
        )

    raise DatabaseError(
        "Chưa cấu hình kết nối database. Hãy thiết lập `.streamlit/secrets.toml` hoặc biến môi trường TIDB_*."
    )


def _format_vnd(amount: int) -> str:
    return f"{amount:,} đ".replace(",", ".")


def _render_overview_page(service: ParkingService) -> None:
    st.header("Tổng quan & Sơ đồ bãi xe")

    metrics = service.get_overview_metrics()
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Tổng vị trí", metrics.total_slots)
    col2.metric("Chỗ trống", metrics.available_slots)
    col3.metric("Xe đang gửi", metrics.active_vehicles)
    col4.metric("Doanh thu hôm nay", _format_vnd(metrics.today_revenue))
    col5.metric("Vé tháng hiệu lực", metrics.active_monthly_passes)

    st.divider()

    lots = service.get_parking_lots()
    st.subheader("Tình trạng các bãi đỗ")
    if lots:
        lots_df = pd.DataFrame(lots).rename(
            columns={
                "id": "Mã bãi",
                "tenbaido": "Tên bãi đỗ",
                "diadiem": "Địa điểm",
                "tong_cho": "Tổng chỗ",
                "cho_trong": "Còn trống",
                "dang_do": "Đang đỗ",
            }
        )
        st.dataframe(lots_df, use_container_width=True, hide_index=True)

    st.subheader("Sơ đồ vị trí đỗ trực quan")
    filter_col1, filter_col2 = st.columns(2)
    lot_options: dict[str, Optional[int]] = {"Tất cả bãi xe": None}
    for lot in lots:
        lot_options[f"{lot['tenbaido']} ({lot['diadiem']})"] = int(lot["id"])

    selected_lot_label = filter_col1.selectbox("Chọn bãi xe", list(lot_options.keys()))
    selected_lot_id = lot_options[selected_lot_label]

    zones = service.get_zones(selected_lot_id)
    zone_options: dict[str, Optional[int]] = {"Tất cả khu vực": None}
    for z in zones:
        zone_options[f"Khu {z['ten']} - {z['tenbaido']}"] = int(z["id"])

    selected_zone_label = filter_col2.selectbox("Chọn khu vực", list(zone_options.keys()))
    selected_zone_id = zone_options[selected_zone_label]

    slots = service.get_slots(lot_id=selected_lot_id, zone_id=selected_zone_id)
    if not slots:
        st.info("Khu vực này chưa có vị trí đỗ nào. Bạn có thể tạo thêm ở mục bên dưới.")
    else:
        cols_per_row = 5
        for idx in range(0, len(slots), cols_per_row):
            row_slots = slots[idx : idx + cols_per_row]
            cols = st.columns(cols_per_row)
            for col, slot in zip(cols, row_slots):
                is_free = int(slot["trangthai"] or 0) == 1
                css_cls = "slot-free" if is_free else "slot-busy"
                status_text = "🟢 Trống" if is_free else f"🔴 {slot.get('bienso') or 'Đang đỗ'}"
                detail = (
                    slot["tenbaido"]
                    if is_free
                    else f"{slot['tenbaido']} | {slot.get('loaiphuongtien') or ''} | Vào: {str(slot.get('giovao') or '')[:16]}"
                )
                col.markdown(
                    f"""
                    <div class="slot-card {css_cls}">
                        <div class="slot-title">Khu {slot['ten_khuvuc']}-{slot['sothutu']}</div>
                        <div class="slot-meta">{status_text}</div>
                        <div class="slot-meta">{detail}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    with st.expander("Mở rộng thêm vị trí đỗ cho khu vực"):
        if zones:
            z_map = {f"{z['tenbaido']} - Khu {z['ten']}": int(z["id"]) for z in zones}
            with st.form("add_slots_form"):
                c1, c2 = st.columns([3, 1])
                target_zone = c1.selectbox("Khu vực cần thêm", list(z_map.keys()))
                qty = c2.number_input("Số ô thêm", min_value=1, max_value=50, value=5)
                if st.form_submit_button("Thêm vị trí đỗ"):
                    try:
                        added = service.add_slots_to_zone(z_map[target_zone], int(qty))
                        st.success(f"Đã thêm {added} vị trí đỗ mới.")
                        st.rerun()
                    except (ValidationError, DatabaseError) as exc:
                        st.error(str(exc))

    st.subheader("Danh sách xe đang gửi trong bãi")
    active_turns = service.get_active_turns()
    if active_turns:
        active_df = pd.DataFrame(active_turns).rename(
            columns={
                "id_luotdo": "Mã lượt",
                "bienso": "Biển số",
                "loaiphuongtien": "Loại xe",
                "tenbaido": "Bãi đỗ",
                "khuvuc": "Khu",
                "vitri": "Ô số",
                "mathe": "Thẻ xe",
                "giovao": "Giờ vào",
                "nhanvien": "Nhân viên trực",
                "loaive": "Loại vé",
                "dongia": "Đơn giá",
            }
        )
        st.dataframe(active_df, use_container_width=True, hide_index=True)
    else:
        st.info("Hiện tại không có phương tiện nào đang gửi trong bãi.")


def _render_checkin_checkout_page(service: ParkingService) -> None:
    st.header("Quản lý Xe vào / Xe ra")

    employees = service.get_employees()
    if not employees:
        st.warning(
            "Chưa có dữ liệu nhân viên trong DB. Nhấn **Khởi tạo dữ liệu mẫu** ở thanh bên trái để tạo nhân viên và thẻ xe."
        )
        return

    emp_map = {f"{e['hoten']} ({e['chucvu']})": int(e["id"]) for e in employees}

    tab_in, tab_out = st.tabs(["🚘 Cho xe vào bãi (Check-in)", "🏁 Cho xe ra & Thanh toán (Check-out)"])

    with tab_in:
        vehicle_types = service.get_vehicle_types()
        vtype_map = {str(v["tenloai"]): int(v["id"]) for v in vehicle_types}

        free_slots = [s for s in service.get_slots() if int(s["trangthai"] or 0) == 1]
        free_cards = service.get_cards(only_available=True)

        if not free_slots:
            st.warning("Hiện không còn vị trí đỗ trống.")
        elif not free_cards:
            st.warning("Hiện không còn thẻ xe trống để phát hành.")
        else:
            slot_map = {
                f"{s['tenbaido']} | Khu {s['ten_khuvuc']}-{s['sothutu']}": int(s["id"])
                for s in free_slots
            }
            card_map = {str(c["maso"]): int(c["id"]) for c in free_cards}

            with st.form("checkin_form"):
                c1, c2 = st.columns(2)
                plate = c1.text_input("Biển số xe (tối đa 8 ký tự)", placeholder="VD: 29A12345", max_chars=8)
                vtype_label = c2.selectbox("Loại phương tiện", list(vtype_map.keys()))

                c3, c4, c5 = st.columns(3)
                slot_label = c3.selectbox("Vị trí đỗ trống", list(slot_map.keys()))
                card_label = c4.selectbox("Thẻ xe cấp phát", list(card_map.keys()))
                emp_label = c5.selectbox("Nhân viên tiếp nhận", list(emp_map.keys()))

                submitted = st.form_submit_button("Xác nhận xe vào bãi", type="primary")
                if submitted:
                    try:
                        turn_id = service.check_in_vehicle(
                            license_plate=plate,
                            vehicle_type_id=vtype_map[vtype_label],
                            slot_id=slot_map[slot_label],
                            card_id=card_map[card_label],
                            employee_id=emp_map[emp_label],
                        )
                        st.success(f"Đã ghi nhận xe vào bãi thành công (Mã lượt #{turn_id}).")
                        st.rerun()
                    except (ValidationError, DatabaseError) as exc:
                        st.error(str(exc))

    with tab_out:
        active_turns = service.get_active_turns()
        if not active_turns:
            st.info("Không có xe nào đang chờ ra bãi.")
        else:
            turn_map = {
                f"#{t['id_luotdo']} | {t['bienso']} ({t['loaiphuongtien']}) - {t['tenbaido']} Khu {t['khuvuc']}-{t['vitri']}": int(
                    t["id_luotdo"]
                )
                for t in active_turns
            }
            selected_turn_label = st.selectbox("Chọn phương tiện cần xuất bến", list(turn_map.keys()))
            selected_turn_id = turn_map[selected_turn_label]

            try:
                quote = service.get_fee_quote(selected_turn_id)
                q1, q2, q3, q4 = st.columns(4)
                q1.metric("Biển số", quote.license_plate)
                q2.metric("Hình thức vé", quote.ticket_type)
                q3.metric("Thời gian gửi", f"{quote.duration_hours} giờ")
                q4.metric("Phí thanh toán", _format_vnd(quote.amount))

                with st.form("checkout_form"):
                    cashier_label = st.selectbox("Nhân viên thu ngân", list(emp_map.keys()))
                    if st.form_submit_button("Xác nhận thanh toán & Cho xe ra", type="primary"):
                        done_quote = service.check_out_vehicle(selected_turn_id, emp_map[cashier_label])
                        st.success(
                            f"Đã hoàn tất thanh toán {_format_vnd(done_quote.amount)} cho xe {done_quote.license_plate}."
                        )
                        st.rerun()
            except (ValidationError, DatabaseError) as exc:
                st.error(str(exc))


def _render_transactions_page(service: ParkingService) -> None:
    st.header("Lịch sử giao dịch & Thanh toán")

    vtypes = service.get_vehicle_types()
    vtype_options: dict[str, Optional[int]] = {"Tất cả loại xe": None}
    for v in vtypes:
        vtype_options[str(v["tenloai"])] = int(v["id"])

    f1, f2, f3 = st.columns(3)
    date_from = f1.date_input("Từ ngày", value=date.today() - timedelta(days=30))
    date_to = f2.date_input("Đến ngày", value=date.today())
    vtype_label = f3.selectbox("Loại phương tiện", list(vtype_options.keys()))

    rows = service.get_transactions(
        date_from=date_from,
        date_to=date_to,
        vehicle_type_id=vtype_options[vtype_label],
    )

    if not rows:
        st.info("Không có giao dịch nào trong khoảng thời gian đã chọn.")
        return

    df = pd.DataFrame(rows)
    total_amount = int(df["chiphi"].sum())
    c1, c2 = st.columns(2)
    c1.metric("Số lượng giao dịch", len(df))
    c2.metric("Tổng doanh thu theo bộ lọc", _format_vnd(total_amount))

    display_df = df.rename(
        columns={
            "ma_gd": "Mã GD",
            "bienso": "Biển số",
            "loaiphuongtien": "Loại xe",
            "tenbaido": "Bãi đỗ",
            "vitri": "Vị trí",
            "giovao": "Giờ vào",
            "giora": "Giờ ra",
            "giothanhtoan": "Giờ thanh toán",
            "chiphi": "Chi phí (VNĐ)",
            "hinhthuc": "Hình thức",
            "trangthai": "Trạng thái",
            "nhanvien": "Nhân viên",
        }
    )
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    csv_data = display_df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        label="Tải xuống báo cáo CSV",
        data=csv_data,
        file_name=f"lich_su_giao_dich_{date_from}_{date_to}.csv",
        mime="text/csv",
    )


def _render_passes_and_tariffs_page(service: ParkingService) -> None:
    st.header("Vé tháng & Bảng giá niêm yết")

    tab_passes, tab_register, tab_tariffs = st.tabs(
        ["🎫 Danh sách vé tháng", "➕ Đăng ký vé tháng mới", "💰 Bảng giá"]
    )

    with tab_passes:
        passes = service.get_monthly_passes()
        if passes:
            pass_df = pd.DataFrame(passes).rename(
                columns={
                    "id": "Mã vé",
                    "hoten": "Khách hàng",
                    "sdt": "SĐT",
                    "cccd": "CCCD",
                    "loaikhachhang": "Đối tượng",
                    "bienso": "Biển số",
                    "loaiphuongtien": "Loại xe",
                    "mathe": "Thẻ xe",
                    "dongia": "Đơn giá/tháng",
                    "ngaybatdau": "Ngày bắt đầu",
                    "ngayketthuc": "Ngày hết hạn",
                    "trangthai": "Trạng thái",
                }
            )
            st.dataframe(pass_df, use_container_width=True, hide_index=True)
        else:
            st.info("Chưa có vé tháng nào được đăng ký.")

    with tab_register:
        ctypes = service.get_customer_types()
        vtypes = service.get_vehicle_types()
        cards = service.get_cards(only_available=False)

        if not cards:
            st.warning("Chưa có thẻ xe trong hệ thống. Hãy khởi tạo dữ liệu mẫu ở thanh bên.")
        else:
            ctype_map = {str(c["tenloai"]): int(c["id"]) for c in ctypes}
            vtype_map = {str(v["tenloai"]): int(v["id"]) for v in vtypes}
            card_map = {str(c["maso"]): int(c["id"]) for c in cards}

            with st.form("register_monthly_pass_form"):
                c1, c2, c3 = st.columns(3)
                hoten = c1.text_input("Họ tên khách hàng", max_chars=20)
                sdt = c2.text_input("Số điện thoại", max_chars=20)
                cccd = c3.text_input("Số CCCD", max_chars=15)

                c4, c5, c6, c7 = st.columns(4)
                ctype_label = c4.selectbox("Loại khách hàng", list(ctype_map.keys()))
                plate = c5.text_input("Biển số xe", max_chars=8, placeholder="VD: 29A12345")
                vtype_label = c6.selectbox("Loại phương tiện", list(vtype_map.keys()))
                months = c7.number_input("Số tháng", min_value=1, max_value=12, value=1)

                card_label = st.selectbox("Thẻ xe gán cho vé tháng", list(card_map.keys()))

                if st.form_submit_button("Đăng ký vé tháng", type="primary"):
                    try:
                        pass_id = service.register_monthly_pass(
                            hoten=hoten,
                            sdt=sdt,
                            cccd=cccd,
                            customer_type_id=ctype_map[ctype_label],
                            license_plate=plate,
                            vehicle_type_id=vtype_map[vtype_label],
                            card_id=card_map[card_label],
                            months=int(months),
                        )
                        st.success(f"Đăng ký vé tháng thành công (Mã vé #{pass_id}).")
                        st.rerun()
                    except (ValidationError, DatabaseError) as exc:
                        st.error(str(exc))

    with tab_tariffs:
        tariffs = service.get_tariffs()
        if tariffs:
            tariff_df = pd.DataFrame(tariffs)[
                ["id", "loaive", "loaiphuongtien", "loaikhachhang", "dongia"]
            ].rename(
                columns={
                    "id": "Mã giá",
                    "loaive": "Loại vé",
                    "loaiphuongtien": "Loại phương tiện",
                    "loaikhachhang": "Đối tượng",
                    "dongia": "Đơn giá (VNĐ)",
                }
            )
            st.dataframe(tariff_df, use_container_width=True, hide_index=True)


def _render_analytics_page(service: ParkingService) -> None:
    st.header("Thống kê doanh thu & Lưu lượng")

    days = st.slider("Khoảng thời gian thống kê (ngày gần nhất)", min_value=7, max_value=90, value=30)
    daily_rows = service.get_daily_revenue(days=days)
    vtype_rows = service.get_revenue_by_vehicle_type()

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Doanh thu theo ngày")
        if daily_rows:
            df_daily = pd.DataFrame(daily_rows)
            df_daily["ngay"] = pd.to_datetime(df_daily["ngay"]).dt.strftime("%Y-%m-%d")
            chart = (
                alt.Chart(df_daily)
                .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4, color="#2563eb")
                .encode(
                    x=alt.X("ngay:N", title="Ngày"),
                    y=alt.Y("doanh_thu:Q", title="Doanh thu (VNĐ)"),
                    tooltip=["ngay", "so_luot", "doanh_thu"],
                )
                .properties(height=320)
            )
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("Chưa có dữ liệu doanh thu theo ngày.")

    with c2:
        st.subheader("Doanh thu theo loại phương tiện")
        if vtype_rows:
            df_vt = pd.DataFrame(vtype_rows)
            chart_vt = (
                alt.Chart(df_vt)
                .mark_arc(innerRadius=50)
                .encode(
                    theta=alt.Theta("doanh_thu:Q", title="Doanh thu"),
                    color=alt.Color("loaiphuongtien:N", title="Loại xe"),
                    tooltip=["loaiphuongtien", "so_luot", "doanh_thu"],
                )
                .properties(height=320)
            )
            st.altair_chart(chart_vt, use_container_width=True)
        else:
            st.info("Chưa có dữ liệu phân bổ theo loại phương tiện.")


def main() -> None:
    with st.sidebar:
        st.title("🅿️ Smart Parking")
        st.caption("Hệ thống quản lý bãi đỗ xe PTIT")

    try:
        db = _create_db_service()
        ok, status_msg = db.test_connection()
        if not ok:
            st.error(f"Lỗi kết nối TiDB Cloud: {status_msg}")
            return
    except DatabaseError as exc:
        st.error(str(exc))
        return

    service = ParkingService(db)

    with st.sidebar:
        st.success("Đã kết nối TiDB Cloud (`dbptit`)")
        page = st.radio(
            "Điều hướng",
            [
                "📊 Tổng quan & Sơ đồ bãi",
                "🚗 Vào / Ra bãi xe",
                "💳 Lịch sử giao dịch",
                "🎫 Vé tháng & Bảng giá",
                "📈 Thống kê doanh thu",
            ],
        )
        st.divider()
        if st.button("🌱 Khởi tạo dữ liệu mẫu", use_container_width=True):
            try:
                summary = service.seed_demo_data()
                st.toast(
                    f"Đã tạo: {summary['slots_added']} ô đỗ, {summary['employees_added']} nhân viên, "
                    f"{summary['cards_added']} thẻ xe, {summary['turns_added']} lượt gửi."
                )
                st.rerun()
            except (ValidationError, DatabaseError) as exc:
                st.error(str(exc))

        if st.button("🔄 Làm mới dữ liệu", use_container_width=True):
            st.rerun()

    try:
        if page == "📊 Tổng quan & Sơ đồ bãi":
            _render_overview_page(service)
        elif page == "🚗 Vào / Ra bãi xe":
            _render_checkin_checkout_page(service)
        elif page == "💳 Lịch sử giao dịch":
            _render_transactions_page(service)
        elif page == "🎫 Vé tháng & Bảng giá":
            _render_passes_and_tariffs_page(service)
        elif page == "📈 Thống kê doanh thu":
            _render_analytics_page(service)
    except DatabaseError as exc:
        st.error(f"Lỗi thao tác cơ sở dữ liệu: {exc}")


if __name__ == "__main__":
    main()
