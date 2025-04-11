from flask import current_app, request, redirect, session, flash, url_for
from flask_jwt_extended import get_jwt_identity, jwt_required
from app import mongo
from bson import ObjectId
import requests
import json
import hmac
import hashlib
from datetime import datetime

def process_payment():
    try:
        user_id = get_jwt_identity()
        if not user_id:
            flash("Vui lòng đăng nhập để tiếp tục thanh toán.", "danger")
            return redirect(url_for("login"))

        # Lấy đơn hàng từ session
        order_data = session.get("pending_order")
        if not order_data:
            flash("Không tìm thấy thông tin đơn hàng.", "danger")
            return redirect(url_for("checkout"))

        # Chuẩn bị dữ liệu gửi đến PayOS
        amount = int(float(order_data.get("total", 0)))
        order_code = order_data.get("order_id")

        payment_data = {
            "orderCode": order_code,
            "amount": amount,
            "description": f"Thanh toán đơn hàng {order_code}",
            "returnUrl": current_app.config["PAYOS_RETURN_URL"],
            "cancelUrl": current_app.config["PAYOS_CANCEL_URL"],
            "buyerName": order_data.get("receiver_name", ""),
            "buyerEmail": order_data.get("receiver_email", ""),
            "buyerPhone": order_data.get("receiver_phone", ""),
            "items": [
                {
                    "name": item.get("name", "Sản phẩm không xác định"),
                    "quantity": int(item.get("quantity", 1)),
                    "price": int(float(item.get("price", 0)))
                } for item in order_data.get("items", [])
            ]
        }

        # Tạo chữ ký (signature) cho PayOS
        checksum_key = current_app.config["PAYOS_CHECKSUM_KEY"].encode("utf-8")
        data_str = json.dumps(payment_data, sort_keys=True)
        signature = hmac.new(
            checksum_key,
            data_str.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        # Gửi yêu cầu đến PayOS API
        headers = {
            "x-client-id": current_app.config["PAYOS_CLIENT_ID"],
            "x-api-key": current_app.config["PAYOS_API_KEY"],
            "Content-Type": "application/json"
        }
        response = requests.post(
            current_app.config["PAYOS_API_URL"],
            headers=headers,
            json={**payment_data, "signature": signature}
        )

        # Kiểm tra phản hồi từ PayOS
        if response.status_code == 200:
            result = response.json()
            if result.get("code") == "00":
                payment_url = result["data"]["checkoutUrl"]
                # Không lưu đơn hàng vào CSDL tại đây, giữ trong session
                return redirect(payment_url)
            else:
                flash(f"Lỗi từ PayOS: {result.get('desc', 'Không rõ nguyên nhân')}", "danger")
        else:
            flash("Lỗi khi kết nối tới PayOS.", "danger")
        
        # Nếu có lỗi, xóa session và chuyển về checkout
        session.pop("pending_order", None)
        return redirect(url_for("checkout"))

    except Exception as e:
        print(f"Error in payment processing: {str(e)}")
        flash(f"Lỗi khi xử lý thanh toán PayOS: {str(e)}", "danger")
        session.pop("pending_order", None)
        return redirect(url_for("checkout"))

@jwt_required()
def payment_return():
    """Xử lý phản hồi từ PayOS sau khi thanh toán."""
    try:
        user_id = get_jwt_identity()
        if not user_id:
            flash("Vui lòng đăng nhập để tiếp tục.", "danger")
            return redirect(url_for("login"))

        # Lấy dữ liệu phản hồi từ PayOS
        order_code = request.args.get("orderCode")
        status = request.args.get("status")

        print("PayOS Response:", request.args.to_dict())

        if not order_code:
            flash("Không tìm thấy mã đơn hàng.", "danger")
            session.pop("pending_order", None)
            return redirect(url_for("orders"))

        # Lấy đơn hàng từ session
        order_data = session.get("pending_order")
        if not order_data or order_data.get("order_id") != order_code:
            flash("Thông tin đơn hàng không hợp lệ.", "danger")
            session.pop("pending_order", None)
            return redirect(url_for("orders"))

        if status == "PAID":
            # Thanh toán thành công, lưu đơn hàng vào CSDL
            order_for_db = order_data.copy()
            order_for_db["user_id"] = ObjectId(user_id)
            order_for_db["subtotal"] = float(order_for_db["subtotal"])
            order_for_db["total"] = float(order_for_db["total"])
            order_for_db["discount"] = float(order_for_db["discount"])
            for item in order_for_db["items"]:
                item["quantity"] = int(item["quantity"])
                item["price"] = float(item["price"])

            # Thêm thông tin thanh toán
            order_for_db["payment_details"] = {
                "method": "payos",
                "status": "paid",
                "orderCode": order_code,
                "amount": order_for_db["total"],
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            # Lưu vào database
            mongo.db.orders.insert_one(order_for_db)

            # Xóa giỏ hàng
            mongo.db.carts.delete_one({"user_id": ObjectId(user_id)})

            # Xóa session
            session.pop("pending_order", None)

            flash("Thanh toán thành công!", "success")
            return redirect(url_for("order_complete"))

        elif status == "CANCELLED":
            # Thanh toán bị hủy, không lưu đơn hàng
            flash("Thanh toán đã bị hủy.", "warning")
            session.pop("pending_order", None)
            return redirect(url_for("checkout"))

        else:
            # Trạng thái không xác định
            flash(f"Trạng thái thanh toán không xác định: {status}", "danger")
            session.pop("pending_order", None)
            return redirect(url_for("checkout"))

    except Exception as e:
        print(f"Error in payment_return: {str(e)}")
        flash(f"Đã xảy ra lỗi khi xử lý phản hồi thanh toán: {str(e)}", "danger")
        session.pop("pending_order", None)
        return redirect(url_for("checkout"))