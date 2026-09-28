import sqlite3
from datetime import datetime, date
import streamlit as st
import pandas as pd
import plotly.express as px

# ---------------------------------------------------------
# SETUP TRANG & CẤU HÌNH GIAO DIỆN
# ---------------------------------------------------------
st.set_page_config(
    page_title="Hệ Thống Quản Lý Khách Sạn",
    page_icon="🏨",
    layout="wide"
)

# ---------------------------------------------------------
# KẾT NỐI VÀ KHỞI TẠO CƠ SỞ DỮ LIỆU SQLITE
# ---------------------------------------------------------
def get_connection():
    conn = sqlite3.connect('hotel_management.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    c = conn.cursor()
    
    # Bảng Quản lý Phòng
    c.execute('''
        CREATE TABLE IF NOT EXISTS rooms (
            room_number TEXT PRIMARY KEY,
            room_type TEXT NOT NULL,
            price REAL NOT NULL,
            status TEXT NOT NULL,          -- 'Trống', 'Đang ở', 'Bảo trì'
            cleaning_status TEXT NOT NULL  -- 'Sạch', 'Chưa dọn'
        )
    ''')
    
    # Bảng Đặt Phòng
    c.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            booking_id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_number TEXT NOT NULL,
            guest_name TEXT NOT NULL,
            guest_phone TEXT NOT NULL,
            check_in TEXT NOT NULL,
            check_out TEXT NOT NULL,
            total_amount REAL NOT NULL,
            booking_status TEXT NOT NULL,  -- 'Đã đặt', 'Đang ở', 'Đã trả phòng', 'Đã hủy'
            FOREIGN KEY (room_number) REFERENCES rooms (room_number)
        )
    ''')
    
    # Thêm dữ liệu mẫu nếu bảng phòng còn trống
    c.execute("SELECT COUNT(*) FROM rooms")
    if c.fetchone()[0] == 0:
        sample_rooms = [
            ('101', 'Standard Single', 500000, 'Trống', 'Sạch'),
            ('102', 'Standard Single', 500000, 'Trống', 'Chưa dọn'),
            ('201', 'Deluxe Double', 800000, 'Trống', 'Sạch'),
            ('202', 'Deluxe Double', 800000, 'Trống', 'Sạch'),
            ('301', 'VIP Suite', 1500000, 'Trống', 'Sạch'),
            ('302', 'VIP Suite', 1500000, 'Bảo trì', 'Sạch')
        ]
        c.executemany("INSERT INTO rooms VALUES (?, ?, ?, ?, ?)", sample_rooms)
    
    conn.commit()
    conn.close()

init_db()

# ---------------------------------------------------------
# TRUY VẤN DỮ LIỆU HỖ TRỢ
# ---------------------------------------------------------
def fetch_dataframe(query, params=()):
    conn = get_connection()
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def execute_query(query, params=()):
    conn = get_connection()
    c = conn.cursor()
    c.execute(query, params)
    conn.commit()
    conn.close()

# ---------------------------------------------------------
# THANH ĐIỀU HƯỚNG (SIDEBAR)
# ---------------------------------------------------------
st.sidebar.title("🏨 Khách Sạn Management")
st.sidebar.markdown("---")

menu = st.sidebar.radio(
    "Danh mục quản lý:",
    ["📊 Sơ Đồ Phòng Real-time", "📝 Đặt Phòng / Check-in", "🛎️ Quản Lý Đặt Phòng", "🧹 Trạng Thái Buồng Phòng", "📈 Báo Cáo & Thống Kê"]
)

# ---------------------------------------------------------
# MODULE 1: SƠ ĐỒ PHÒNG REAL-TIME
# ---------------------------------------------------------
if menu == "📊 Sơ Đồ Phòng Real-time":
    st.header("📊 Sơ Đồ Phòng Theo Thời Gian Thực")
    
    df_rooms = fetch_dataframe("SELECT * FROM rooms ORDER BY room_number")
    
    # Bộ lọc
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        type_filter = st.multiselect("Lọc loại phòng:", df_rooms['room_type'].unique(), default=df_rooms['room_type'].unique())
    with col_f2:
        status_filter = st.multiselect("Lọc trạng thái:", df_rooms['status'].unique(), default=df_rooms['status'].unique())
    
    filtered_rooms = df_rooms[
        (df_rooms['room_type'].isin(type_filter)) & 
        (df_rooms['status'].isin(status_filter))
    ]
    
    st.markdown("---")
    
    # Hiển thị dạng lưới (Grid)
    cols = st.columns(4)
    for idx, room in filtered_rooms.iterrows():
        col = cols[idx % 4]
        
        # Mã màu cho trạng thái
        status_color = "🟢" if room['status'] == 'Trống' else ("🔴" if room['status'] == 'Đang ở' else "🟡")
        clean_badge = "✨ Sạch" if room['cleaning_status'] == 'Sạch' else "🧹 Chưa dọn"
        
        with col:
            st.markdown(
                f"""
                <div style="border: 1px solid #ddd; padding: 15px; border-radius: 10px; background-color: #f9f9f9; margin-bottom: 15px;">
                    <h3 style="margin:0; color:#333;">Phòng {room['room_number']}</h3>
                    <p style="margin:5px 0;"><b>Loại:</b> {room['room_type']}</p>
                    <p style="margin:5px 0;"><b>Giá:</b> {room['price']:,.0f} VNĐ/đêm</p>
                    <p style="margin:5px 0;"><b>Trạng thái:</b> {status_color} {room['status']}</p>
                    <p style="margin:5px 0;"><b>Vệ sinh:</b> {clean_badge}</p>
                </div>
                """,
                unsafe_allow_html=True
            )

# ---------------------------------------------------------
# MODULE 2: ĐẶT PHÒNG / CHECK-IN
# ---------------------------------------------------------
elif menu == "📝 Đặt Phòng / Check-in":
    st.header("📝 Đặt Phòng Mới & Check-in")
    
    df_rooms = fetch_dataframe("SELECT * FROM rooms WHERE status = 'Trống'")
    
    if df_rooms.empty:
        st.warning("Hiện tại không có phòng nào trống!")
    else:
        with st.form("booking_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                guest_name = st.text_input("Họ và tên khách hàng *")
                guest_phone = st.text_input("Số điện thoại *")
                selected_room = st.selectbox("Chọn phòng trống *", df_rooms['room_number'].tolist())
            
            with col2:
                check_in_date = st.date_input("Ngày nhận phòng", min_value=date.today())
                check_out_date = st.date_input("Ngày trả phòng (dự kiến)", min_value=check_in_date)
                action_type = st.radio("Hành động:", ["Đặt trước (Chưa nhận phòng)", "Check-in ngay"])
            
            # Tính toán tổng tiền dự kiến
            num_nights = (check_out_date - check_in_date).days
            num_nights = max(num_nights, 1)
            
            room_price = df_rooms[df_rooms['room_number'] == selected_room]['price'].values[0]
            total_price = room_price * num_nights
            
            st.info(f"Số đêm: **{num_nights}** | Dự tính tổng tiền: **{total_price:,.0f} VNĐ**")
            
            submitted = st.form_submit_button("Xác Nhận Đặt Phòng")
            
            if submitted:
                if not guest_name or not guest_phone:
                    st.error("Vui lòng điền đầy đủ thông tin khách hàng!")
                else:
                    b_status = "Đang ở" if action_type == "Check-in ngay" else "Đã đặt"
                    
                    # Thêm lượt đặt phòng
                    execute_query(
                        """
                        INSERT INTO bookings (room_number, guest_name, guest_phone, check_in, check_out, total_amount, booking_status)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (selected_room, guest_name, guest_phone, str(check_in_date), str(check_out_date), total_price, b_status)
                    )
                    
                    # Cập nhật trạng thái phòng nếu check-in ngay
                    if action_type == "Check-in ngay":
                        execute_query("UPDATE rooms SET status = 'Đang ở' WHERE room_number = ?", (selected_room,))
                    
                    st.success(f"Thành công! Đã ghi nhận thông tin cho phòng {selected_room}.")
                    st.rerun()

# ---------------------------------------------------------
# MODULE 3: QUẢN LÝ ĐẶT PHÒNG & TRẢ PHÒNG
# ---------------------------------------------------------
elif menu == "🛎️ Quản Lý Đặt Phòng":
    st.header("🛎️ Quản Lý Lượt Đặt & Trả Phòng")
    
    df_bookings = fetch_dataframe("""
        SELECT b.booking_id, b.room_number, b.guest_name, b.guest_phone, 
               b.check_in, b.check_out, b.total_amount, b.booking_status
        FROM bookings b
        WHERE b.booking_status IN ('Đã đặt', 'Đang ở')
        ORDER BY b.booking_id DESC
    """)
    
    if df_bookings.empty:
        st.info("Hiện không có lượt đặt phòng hoặc nhận phòng nào đang hoạt động.")
    else:
        st.dataframe(df_bookings, use_container_width=True)
        st.markdown("---")
        
        col_act1, col_act2 = st.columns(2)
        
        with col_act1:
            st.subheader("Nhận phòng (Dành cho đơn Đặt trước)")
            pre_bookings = df_bookings[df_bookings['booking_status'] == 'Đã đặt']
            if not pre_bookings.empty:
                selected_pre_id = st.selectbox("Chọn Mã đơn đặt:", pre_bookings['booking_id'].tolist(), key="checkin_select")
                if st.button("Xác Nhận Check-In"):
                    room_num = pre_bookings[pre_bookings['booking_id'] == selected_pre_id]['room_number'].values[0]
                    execute_query("UPDATE bookings SET booking_status = 'Đang ở' WHERE booking_id = ?", (selected_pre_id,))
                    execute_query("UPDATE rooms SET status = 'Đang ở' WHERE room_number = ?", (room_num,))
                    st.success(f"Đã Check-in thành công cho đơn #{selected_pre_id}!")
                    st.rerun()
            else:
                st.caption("Không có đơn đặt trước chờ nhận phòng.")

        with col_act2:
            st.subheader("Trả phòng & Thanh toán")
            active_stay = df_bookings[df_bookings['booking_status'] == 'Đang ở']
            if not active_stay.empty:
                selected_stay_id = st.selectbox("Chọn Mã đơn trả phòng:", active_stay['booking_id'].tolist(), key="checkout_select")
                booking_info = active_stay[active_stay['booking_id'] == selected_stay_id].iloc[0]
                
                st.write(f"Khách: **{booking_info['guest_name']}** - Phòng: **{booking_info['room_number']}**")
                st.write(f"Thành tiền: **{booking_info['total_amount']:,.0f} VNĐ**")
                
                if st.button("Thanh Toán & Check-Out"):
                    # Cập nhật trạng thái lượt đặt
                    execute_query("UPDATE bookings SET booking_status = 'Đã trả phòng' WHERE booking_id = ?", (selected_stay_id,))
                    # Cập nhật phòng thành Trống và Đánh dấu Cần dọn dẹp
                    execute_query("UPDATE rooms SET status = 'Trống', cleaning_status = 'Chưa dọn' WHERE room_number = ?", (booking_info['room_number'],))
                    st.success(f"Thanh toán thành công đơn #{selected_stay_id}. Trạng thái phòng đã chuyển về 'Chưa dọn'.")
                    st.rerun()
            else:
                st.caption("Không có khách đang ở để trả phòng.")

# ---------------------------------------------------------
# MODULE 4: QUẢN LÝ BUỒNG PHÒNG
# ---------------------------------------------------------
elif menu == "🧹 Trạng Thái Buồng Phòng":
    st.header("🧹 Quản Lý Dọn Phòng & Bảo Trì")
    
    df_rooms = fetch_dataframe("SELECT room_number, room_type, status, cleaning_status FROM rooms ORDER BY room_number")
    
    col_t1, col_t2 = st.columns([2, 1])
    
    with col_t1:
        st.subheader("Danh sách phòng")
        st.dataframe(df_rooms, use_container_width=True)
        
    with col_t2:
        st.subheader("Cập nhật trạng thái")
        selected_room_edit = st.selectbox("Chọn phòng:", df_rooms['room_number'].tolist())
        
        current_room_info = df_rooms[df_rooms['room_number'] == selected_room_edit].iloc[0]
        
        new_clean_status = st.selectbox(
            "Trạng thái vệ sinh:", 
            ["Sạch", "Chưa dọn"], 
            index=0 if current_room_info['cleaning_status'] == 'Sạch' else 1
        )
        
        new_room_status = st.selectbox(
            "Trạng thái vận hành:", 
            ["Trống", "Đang ở", "Bảo trì"], 
            index=["Trống", "Đang ở", "Bảo trì"].index(current_room_info['status'])
        )
        
        if st.button("Lưu Thay Đổi"):
            execute_query(
                "UPDATE rooms SET cleaning_status = ?, status = ? WHERE room_number = ?",
                (new_clean_status, new_room_status, selected_room_edit)
            )
            st.success(f"Cập nhật trạng thái phòng {selected_room_edit} thành công!")
            st.rerun()

# ---------------------------------------------------------
# MODULE 5: BÁO CÁO & THỐNG KÊ
# ---------------------------------------------------------
elif menu == "📈 Báo Cáo & Thống Kê":
    st.header("📈 Báo Cáo Doanh Thu & Công Suất Phòng")
    
    # Chỉ tính các đơn đã hoàn tất thanh toán (Đã trả phòng)
    df_paid = fetch_dataframe("SELECT * FROM bookings WHERE booking_status = 'Đã trả phòng'")
    
    # Chỉ số KPI
    m1, m2, m3 = st.columns(3)
    
    total_revenue = df_paid['total_amount'].sum() if not df_paid.empty else 0
    total_completed_bookings = len(df_paid)
    
    df_all_rooms = fetch_dataframe("SELECT COUNT(*) as total FROM rooms")
    total_rooms_count = df_all_rooms['total'].values[0]
    occupied_rooms_count = len(fetch_dataframe("SELECT * FROM rooms WHERE status = 'Đang ở'"))
    occupancy_rate = (occupied_rooms_count / total_rooms_count * 100) if total_rooms_count > 0 else 0
    
    m1.metric("Tổng Doanh Thu", f"{total_revenue:,.0f} VNĐ")
    m2.metric("Số Lượt Trả Phòng", f"{total_completed_bookings} đơn")
    m3.metric("Công Suất Phòng Hiện Tại", f"{occupancy_rate:.1f}%")
    
    st.markdown("---")
    
    if not df_paid.empty:
        col_g1, col_g2 = st.columns(2)
        
        with col_g1:
            st.subheader("Doanh thu theo Loại Phòng")
            df_room_rev = fetch_dataframe("""
                SELECT r.room_type, SUM(b.total_amount) as revenue
                FROM bookings b
                JOIN rooms r ON b.room_number = r.room_number
                WHERE b.booking_status = 'Đã trả phòng'
                GROUP BY r.room_type
            """)
            fig_pie = px.pie(df_room_rev, values='revenue', names='room_type', hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig_pie, use_container_width=True)
            
        with col_g2:
            st.subheader("Lịch Sử Thanh Toán")
            st.dataframe(df_paid[['booking_id', 'room_number', 'guest_name', 'check_in', 'check_out', 'total_amount']], use_container_width=True)
    else:
        st.info("Chưa có dữ liệu thanh toán để hiển thị biểu đồ.")

