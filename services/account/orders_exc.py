from flask import session
from app import mongo
from bson import ObjectId
from datetime import datetime
import pytz

def jsonify_objectid(obj):
    """
    Hàm để chuyển ObjectId thành chuỗi.
    """
    if isinstance(obj, ObjectId):
        return str(obj)
    raise TypeError("Object of type ObjectId is not JSON serializable")

def convert_objectid(data):
    """
    Hàm đệ quy để chuyển tất cả ObjectId thành chuỗi trong một dictionary hoặc list.
    """
    if isinstance(data, ObjectId):
        return str(data)
    if isinstance(data, dict):
        return {key: convert_objectid(value) for key, value in data.items()}
    if isinstance(data, list):
        return [convert_objectid(item) for item in data]
    return data

def get_orders():
    """
    Lấy danh sách đơn hàng của người dùng, đồng bộ trạng thái với phía admin và tính tổng tiền từ items nếu cần.
    """
    user_id = session.get("user_id")
    if not user_id:
        return []

    orders = list(mongo.db.orders.find({"user_id": ObjectId(user_id)}))
    for i in range(len(orders)):
        # Chuyển đổi tất cả ObjectId thành chuỗi
        orders[i] = convert_objectid(orders[i])

        # Gán mã đơn hàng (dùng _id nếu không có order_id)
        orders[i]['id'] = orders[i].get('order_id', orders[i]['_id'])

        # Chuyển đổi ngày đặt hàng sang giờ Việt Nam
        if orders[i].get('order_date'):
            try:
                date = orders[i]['order_date']
                if isinstance(date, str):
                    date = datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
                date = date.replace(tzinfo=pytz.UTC).astimezone(pytz.timezone('Asia/Ho_Chi_Minh'))
                orders[i]['date'] = date.strftime('%Y-%m-%d %H:%M:%S')
            except:
                orders[i]['date'] = 'Không xác định'
        else:
            orders[i]['date'] = 'Không xác định'

        # Tính tổng tiền từ items nếu total_amount không tồn tại
        total_amount = orders[i].get('total_amount', 0)
        if not total_amount and 'items' in orders[i] and isinstance(orders[i]['items'], list):
            total = 0
            for item in orders[i]['items']:
                price = float(item.get('price', 0))  # Giá sản phẩm, mặc định 0 nếu không có
                quantity = int(item.get('quantity', 0))  # Số lượng, mặc định 0 nếu không có
                total += price * quantity
            total_amount = total

        # Định dạng tổng tiền
        orders[i]['total'] = "{:,.0f}".format(total_amount)

        # Ánh xạ trạng thái giao hàng từ admin sang tiếng Việt
        delivery_status = orders[i].get('delivery_status', 'pending')
        status_map = {
            "pending": "Đang chuẩn bị",
            "waiting_for_shipping": "Chờ vận chuyển",
            "waiting_for_delivery": "Chờ giao hàng",
            "completed": "Hoàn thành",
            "cancelled": "Đã hủy",
            "returned": "Hoàn hàng"
        }
        orders[i]['status'] = status_map.get(delivery_status, "Không xác định")

        # Đảm bảo order['items'] là danh sách và không chứa ObjectId
        if 'items' in orders[i]:
            orders[i]['items'] = convert_objectid(orders[i]['items'])
        else:
            orders[i]['items'] = []

        # Bổ sung các trường cần thiết cho modal (đồng bộ với admin)
        orders[i]['receiver_name'] = orders[i].get('receiver_name', 'Không xác định')
        orders[i]['receiver_phone'] = orders[i].get('receiver_phone', 'Không xác định')
        orders[i]['receiver_email'] = orders[i].get('receiver_email', 'Không xác định')
        orders[i]['receiver_address'] = orders[i].get('receiver_address', 'Không xác định')
        orders[i]['payment_method'] = orders[i].get('payment_method', 'Không xác định')
        orders[i]['payment_status'] = orders[i].get('payment_status', 'Không xác định')

    return orders