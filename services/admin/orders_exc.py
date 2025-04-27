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

def update_order_status(order_id, delivery_status, payment_status):
    try:
        # Danh sách trạng thái hợp lệ
        valid_delivery_statuses = ["pending", "waiting_for_shipping", "waiting_for_delivery", 
                                  "completed", "cancelled", "returned"]
        valid_payment_statuses = ["pending", "processing", "paid", "failed", "refunded", "partially_paid", "unpaid"]

        # Kiểm tra order_id hợp lệ
        if not order_id:
            return {"success": False, "message": "Thiếu order_id"}

        # Kiểm tra trạng thái hợp lệ
        if delivery_status and delivery_status not in valid_delivery_statuses:
            return {"success": False, "message": "Trạng thái giao hàng không hợp lệ"}
        if payment_status and payment_status not in valid_payment_statuses:
            return {"success": False, "message": "Trạng thái thanh toán không hợp lệ"}

        # Tìm đơn hàng
        order = mongo.db.orders.find_one({"_id": ObjectId(order_id)})
        if not order:
            return {"success": False, "message": "Không tìm thấy đơn hàng"}

        # Chuẩn bị dữ liệu cập nhật
        update_data = {}
        current_time = datetime.utcnow()

        # Cập nhật trạng thái giao hàng
        if delivery_status:
            update_data["delivery_status"] = delivery_status
            # Thêm vào lịch sử trạng thái giao hàng
            delivery_status_history = order.get("delivery_status_history", [])
            delivery_status_history.append({
                "status": delivery_status,
                "updated_at": current_time
            })
            update_data["delivery_status_history"] = delivery_status_history

            # Nếu trạng thái giao hàng là "cancelled", đặt trạng thái thanh toán thành "unpaid"
            if delivery_status == "cancelled":
                update_data["payment_status"] = "unpaid"
                payment_status_history = order.get("payment_status_history", [])
                payment_status_history.append({
                    "status": "unpaid",
                    "updated_at": current_time
                })
                update_data["payment_status_history"] = payment_status_history

        # Cập nhật trạng thái thanh toán (nếu có và không bị ghi đè bởi điều kiện cancelled)
        if payment_status and (not delivery_status or delivery_status != "cancelled"):
            update_data["payment_status"] = payment_status
            # Thêm vào lịch sử trạng thái thanh toán
            payment_status_history = order.get("payment_status_history", [])
            payment_status_history.append({
                "status": payment_status,
                "updated_at": current_time
            })
            update_data["payment_status_history"] = payment_status_history

        # Thực hiện cập nhật trong database
        if update_data:
            result = mongo.db.orders.update_one(
                {"_id": ObjectId(order_id)},
                {"$set": update_data}
            )
            if result.modified_count > 0:
                return {"success": True, "message": "Cập nhật trạng thái thành công"}
            else:
                return {"success": False, "message": "Không có thay đổi nào được thực hiện"}
        else:
            return {"success": False, "message": "Không có dữ liệu để cập nhật"}

    except Exception as e:
        print(f"Error in update_order_status: {str(e)}")
        return {"success": False, "message": f"Lỗi server: {str(e)}"}

def get_order_details(order_id):
    """
    Lấy chi tiết một đơn hàng theo order_id.
    """
    try:
        order = mongo.db.orders.find_one({"_id": ObjectId(order_id)})
        if order:
            # Thêm mapping cho trạng thái thanh toán
            payment_status_map = {
                "pending": "Chờ thanh toán",
                "processing": "Đang xử lý",
                "paid": "Đã thanh toán",
                "failed": "Thanh toán thất bại",
                "refunded": "Đã hoàn tiền",
                "partially_paid": "Thanh toán một phần"
            }
            delivery_status_map = {
                "pending": "Đang chuẩn bị",
                "waiting_for_shipping": "Chờ vận chuyển",
                "waiting_for_delivery": "Chờ giao hàng",
                "completed": "Hoàn thành",
                "cancelled": "Đã huỷ",
                "returned": "Hoàn hàng"
            }
            
            # Cập nhật thông tin hiển thị trạng thái
            order['payment_status_display'] = payment_status_map.get(
                order.get('payment_status', 'pending'),
                "Không xác định"
            )
            order['delivery_status_display'] = delivery_status_map.get(
                order.get('delivery_status', 'pending'),
                "Không xác định"
            )
            
            # Thêm lịch sử trạng thái nếu có
            if 'payment_status_history' in order:
                for history in order['payment_status_history']:
                    history['status_display'] = payment_status_map.get(
                        history['status'],
                        "Không xác định"
                    )
            if 'delivery_status_history' in order:
                for history in order['delivery_status_history']:
                    history['status_display'] = delivery_status_map.get(
                        history['status'],
                        "Không xác định"
                    )
                    
            if 'items' in order:
                for item in order['items']:
                    # Giả sử item có trường product_id để liên kết với products
                    product_id = item.get('product_id')
                    if product_id:
                        try:
                            product = mongo.db.products.find_one(
                                {"_id": ObjectId(product_id)},
                                {"image": 1}
                            )
                            # Nếu tìm thấy sản phẩm, gán đường link hình ảnh; nếu không, dùng placeholder
                            item['image'] = product['image'] if product and product.get('image') else '/static/images/placeholder.jpg'
                        except Exception as e:
                            print(f"Error fetching product image for product_id {product_id}: {str(e)}")
                            item['image'] = '/static/images/placeholder.jpg'
                    else:
                        item['image'] = '/static/images/placeholder.jpg'
        
        return order
    except Exception as e:
        print(f"Error in get_order_details: {str(e)}")
        return None

def get_orders_by_payment_status(payment_status):
    """
    Lấy các đơn hàng theo trạng thái thanh toán.
    """
    try:
        if payment_status == "pending":
            orders = mongo.db.orders.find({
                "$or": [
                    {"payment_status": payment_status},
                    {"payment_status": {"$exists": False}}
                ]
            })
        else:
            orders = mongo.db.orders.find({"payment_status": payment_status})
        return list(orders)
    except Exception as e:
        print(f"Error in get_orders_by_payment_status: {str(e)}")
        return []

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

    # Thêm thống kê thanh toán vào báo cáo
    payment_status_counts = defaultdict(int)
    total_paid_amount = 0

    for order in orders:
        payment_status = order.get('payment_status', 'pending')
        payment_status_counts[payment_status] += 1
        
        if payment_status == 'paid':
            total_amount = order.get('total', 0)
            if not total_amount and 'items' in order:
                total_amount = sum(float(item.get('price', 0)) * int(item.get('quantity', 0)) for item in order['items'])
            total_paid_amount += total_amount

    # Thêm thông tin thanh toán vào dữ liệu báo cáo
    payment_chart_data = {
        'labels': ['Đã thanh toán', 'Chờ thanh toán', 'Đang xử lý', 'Thất bại', 'Hoàn tiền', 'Thanh toán một phần'],
        'data': [
            payment_status_counts['paid'],
            payment_status_counts['pending'],
            payment_status_counts['processing'],
            payment_status_counts['failed'],
            payment_status_counts['refunded'],
            payment_status_counts['partially_paid']
        ]
    }

    # Tổng hợp dữ liệu trả về
    report_data = {
        'time_frame': time_frame,
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'status_chart': status_chart_data,
        'revenue_chart': revenue_chart_data,
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d'),
        'payment_chart': payment_chart_data,
        'total_paid_amount': total_paid_amount,
        'payment_status_counts': dict(payment_status_counts)
    }

    print(f"Report data: {report_data}")  # Debug
    return report_data