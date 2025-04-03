from app import mongo
from bson import ObjectId
from datetime import datetime, timedelta
import pytz
from collections import defaultdict

def get_all_orders():
    """
    Lấy tất cả đơn hàng từ collection orders.
    """
    try:
        orders = mongo.db.orders.find()
        return list(orders)
    except Exception as e:
        print(f"Error in get_all_orders: {str(e)}")
        return []

def get_orders_by_status(status):
    """
    Lấy các đơn hàng theo trạng thái (delivery_status).
    """
    try:
        if status == "Đang chuẩn bị":
            orders = mongo.db.orders.find({
                "$or": [
                    {"delivery_status": status},
                    {"delivery_status": {"$exists": False}}
                ]
            })
        else:
            orders = mongo.db.orders.find({"delivery_status": status})
        return list(orders)
    except Exception as e:
        print(f"Error in get_orders_by_status: {str(e)}")
        return []

def get_order_details(order_id):
    """
    Lấy chi tiết một đơn hàng theo order_id.
    """
    try:
        order = mongo.db.orders.find_one({"_id": ObjectId(order_id)})
        return order
    except Exception as e:
        print(f"Error in get_order_details: {str(e)}")
        return None

def get_orders_report(time_frame='month'):
    """
    Lấy dữ liệu báo cáo đơn hàng theo khung thời gian: week, month, quarter, year.
    Trả về dữ liệu cho biểu đồ và tổng số liệu.
    """
    # Xác định khung thời gian
    now = datetime.now(pytz.timezone('Asia/Ho_Chi_Minh'))
    if time_frame == 'week':
        start_date = now - timedelta(days=now.weekday())  # Bắt đầu từ thứ Hai
        end_date = start_date + timedelta(days=6)  # Kết thúc vào Chủ Nhật
    elif time_frame == 'month':
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = (start_date.replace(month=start_date.month % 12 + 1, year=start_date.year + start_date.month // 12) - timedelta(days=1)) if start_date.month < 12 else start_date.replace(year=start_date.year + 1, month=1, day=1) - timedelta(days=1)
    elif time_frame == 'quarter':
        quarter_start_month = ((now.month - 1) // 3) * 3 + 1
        start_date = now.replace(month=quarter_start_month, day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = (start_date.replace(month=start_date.month + 3) - timedelta(days=1)) if start_date.month <= 9 else start_date.replace(year=start_date.year + 1, month=1, day=1) - timedelta(days=1)
    elif time_frame == 'year':
        start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = now.replace(month=12, day=31, hour=23, minute=59, second=59, microsecond=999999)
    else:
        raise ValueError("Invalid time_frame. Use 'week', 'month', 'quarter', or 'year'.")

    # Chuyển start_date và end_date thành chuỗi để so sánh với order_date
    start_date_str = start_date.strftime('%Y-%m-%d %H:%M:%S')
    end_date_str = end_date.strftime('%Y-%m-%d %H:%M:%S')

    # Truy vấn tất cả đơn hàng trong khung thời gian
    try:
        orders = list(mongo.db.orders.find({
            "order_date": {
                "$gte": start_date_str,
                "$lte": end_date_str
            }
        }))
        print(f"Orders found: {orders}")  # Debug
    except Exception as e:
        print(f"Error querying orders: {str(e)}")
        orders = []

    # Khởi tạo biến đếm trạng thái
    total_orders = len(orders)
    status_counts = defaultdict(int)
    total_revenue = 0

    # Tính toán số liệu
    for order in orders:
        # Chuyển đổi order_date từ chuỗi thành datetime để sử dụng sau này
        order_date = order.get('order_date')
        if isinstance(order_date, str):
            order['order_date'] = datetime.strptime(order_date, '%Y-%m-%d %H:%M:%S')

        status = order.get('delivery_status', 'pending')
        status_counts[status] += 1
        
        # Tính tổng doanh thu từ total hoặc items
        total_amount = order.get('total', 0)
        if not total_amount and 'items' in order:
            total_amount = sum(float(item.get('price', 0)) * int(item.get('quantity', 0)) for item in order['items'])
        total_revenue += total_amount

    # Tính phần trăm trạng thái
    if total_orders > 0:
        success_rate = (status_counts['completed'] / total_orders) * 100
        cancel_rate = (status_counts['cancelled'] / total_orders) * 100
        return_rate = (status_counts['returned'] / total_orders) * 100
    else:
        success_rate = cancel_rate = return_rate = 0

    # Chuẩn bị dữ liệu cho biểu đồ trạng thái đơn hàng
    status_chart_data = {
        'labels': ['Thành công', 'Hủy bỏ', 'Hoàn hàng', 'Khác'],
        'data': [
            status_counts['completed'],
            status_counts['cancelled'],
            status_counts['returned'],
            total_orders - (status_counts['completed'] + status_counts['cancelled'] + status_counts['returned'])
        ],
        'percentages': [success_rate, cancel_rate, return_rate, 100 - (success_rate + cancel_rate + return_rate)]
    }

    # Chuẩn bị dữ liệu cho biểu đồ doanh thu theo ngày
    revenue_by_date = defaultdict(float)
    for order in orders:
        order_date = order['order_date'].strftime('%Y-%m-%d')
        total_amount = order.get('total', 0)
        if not total_amount and 'items' in order:
            total_amount = sum(float(item.get('price', 0)) * int(item.get('quantity', 0)) for item in order['items'])
        revenue_by_date[order_date] += total_amount

    revenue_chart_data = {
        'labels': sorted(revenue_by_date.keys()),
        'data': [revenue_by_date[date] for date in sorted(revenue_by_date.keys())]
    }

    # Tổng hợp dữ liệu trả về
    report_data = {
        'time_frame': time_frame,
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'status_chart': status_chart_data,
        'revenue_chart': revenue_chart_data,
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d')
    }

    print(f"Report data: {report_data}")  # Debug
    return report_data
