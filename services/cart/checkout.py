from flask import jsonify, render_template, flash, redirect, url_for, session, request, current_app
from flask_jwt_extended import get_jwt_identity, get_jwt, jwt_required
from flask_mail import Message
from app import mongo, mail
from bson import ObjectId
from datetime import datetime, timedelta
import random
import string
import requests
import json
import hmac
import hashlib
from urllib.parse import urlencode, quote_plus

def generate_order_id():
    """Tạo mã đơn hàng với định dạng DH + 15 ký tự số ngẫu nhiên."""
    prefix = "DH"
    random_digits = ''.join(random.choices(string.digits, k=15))
    return prefix + random_digits

def apply_voucher(voucher_code, subtotal):
    """Kiểm tra và áp dụng voucher."""
    try:
        voucher = mongo.db.vouchers.find_one({"code": voucher_code})
        if not voucher:
            return None, "Mã voucher không hợp lệ!"
        if voucher["quantity"] <= 0:
            return None, "Mã voucher đã hết lượt sử dụng!"
        if datetime.strptime(voucher["expiry_date"], '%Y-%m-%d') < datetime.now():
            return None, "Mã voucher đã hết hạn!"

        discount_percent = float(voucher["discount"])
        discount_amount = subtotal * (discount_percent / 100)
        return discount_amount, f"Áp dụng voucher thành công!"
    except Exception as e:
        return None, f"Lỗi khi áp dụng voucher: {str(e)}"

def apply_voucher_exc():
    """Xử lý AJAX request để áp dụng voucher."""
    try:
        data = request.get_json()
        voucher_code = data.get('voucher_code')
        subtotal = float(data.get('subtotal'))

        discount_amount, message = apply_voucher(voucher_code, subtotal)
        if discount_amount:
            new_total = subtotal - discount_amount
            return jsonify({
                "success": True,
                "message": message,
                "discount_amount": discount_amount,
                "new_total": new_total
            })
        return jsonify({"success": False, "error": message})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

def checkout_exc():
    try:
        user_id = get_jwt_identity()
        if not user_id:
            flash("Vui lòng đăng nhập để tiếp tục thanh toán.", "danger")
            return redirect(url_for('login'))

        claims = get_jwt()
        discount_amount = claims.get('discount_amount', 0)

        cart = mongo.db.carts.find_one({"user_id": ObjectId(user_id)})
        if not cart or 'products' not in cart or not cart['products']:
            flash("Giỏ hàng của bạn đang trống.", "warning")
            return render_template('cart/checkout.html', cart_items=[], subtotal=0, total=0, addresses=[], default_address=None)

        product_ids = [item['product_id'] for item in cart['products']]
        valid_product_ids = []
        for pid in product_ids:
            try:
                valid_product_ids.append(ObjectId(pid))
            except:
                continue

        products = mongo.db.products.find({"_id": {"$in": valid_product_ids}})
        products_list = list(products)

        cart_items = []
        subtotal = 0
        for product in products_list:
            product['_id'] = str(product['_id'])
            for item in cart['products']:
                if str(item['product_id']) == product['_id']:
                    product['quantity'] = item['quantity']
                    # Ưu tiên sử dụng discounted_price nếu tồn tại, nếu không thì dùng price
                    price = float(product.get('discounted_price', product.get('price', 0)))
                    product['discounted_price'] = price  # Đảm bảo cart_items chứa discounted_price
                    subtotal += price * item['quantity']
                    cart_items.append(product)
                    break

        if not cart_items:
            flash("Không có sản phẩm hợp lệ trong giỏ hàng.", "warning")
            return render_template('cart/checkout.html', cart_items=[], subtotal=0, total=0, addresses=[], default_address=None)

        voucher_code = request.args.get('voucher_code') or session.get('voucher_code')
        voucher_discount = 0
        if voucher_code:
            discount_amount, message = apply_voucher(voucher_code, subtotal)
            if discount_amount:
                voucher_discount = discount_amount
                session['voucher_code'] = voucher_code
                session['voucher_discount'] = voucher_discount
                flash(message, "success")
            else:
                session.pop('voucher_code', None)
                session.pop('voucher_discount', None)
                flash(message, "danger")

        # Tính total trước khi cộng VAT
        total = subtotal - (float(discount_amount) if discount_amount else 0) - voucher_discount
        if total < 0:
            total = 0  # Đảm bảo tổng không âm

        # Tính VAT và cập nhật total
        vat = subtotal * 0.1  # VAT 10%
        total = total + vat  # Cộng VAT vào total

        addresses = list(mongo.db.list_address.find({"user_id": ObjectId(user_id)}))
        for address in addresses:
            address['_id'] = str(address['_id'])
            address['user_id'] = str(address['user_id'])

        default_address = next((addr for addr in addresses if addr.get('is_default', False)), None)

        if request.method == 'POST':
            receiver_name = request.form.get('receiverName')
            email = request.form.get('email')
            payment_method = request.form.get('paymentMethod')

            if not receiver_name or not email or not payment_method:
                flash("Vui lòng điền đầy đủ thông tin.", "danger")
                return render_template('cart/checkout.html', cart_items=cart_items, subtotal=subtotal, total=total, addresses=addresses, default_address=default_address, voucher_code=voucher_code)

            selected_address_id = request.form.get('selected_address')
            if selected_address_id:
                selected_address = next((addr for addr in addresses if addr['_id'] == selected_address_id), None)
                if not selected_address:
                    flash("Địa chỉ không hợp lệ.", "danger")
                    return render_template('cart/checkout.html', cart_items=cart_items, subtotal=subtotal, total=total, addresses=addresses, default_address=default_address, voucher_code=voucher_code)
                address = selected_address['street']
                phone = selected_address['phone']
            else:
                address = request.form.get('address')
                phone = request.form.get('phone')
                address_type = request.form.get('addressType')
                set_default = request.form.get('setDefault') == 'on'

                if not address or not phone or not address_type:
                    flash("Vui lòng điền đầy đủ thông tin địa chỉ.", "danger")
                    return render_template('cart/checkout.html', cart_items=cart_items, subtotal=subtotal, total=total, addresses=addresses, default_address=default_address, voucher_code=voucher_code)

                if address_type not in ["Nhà riêng", "Văn phòng"]:
                    flash("Loại địa chỉ không hợp lệ.", "danger")
                    return render_template('cart/checkout.html', cart_items=cart_items, subtotal=subtotal, total=total, addresses=addresses, default_address=default_address, voucher_code=voucher_code)

                new_address = {
                    "user_id": ObjectId(user_id),
                    "name": address_type,
                    "street": address,
                    "phone": phone,
                    "is_default": set_default
                }
                if set_default:
                    mongo.db.list_address.update_many(
                        {"user_id": ObjectId(user_id), "is_default": True},
                        {"$set": {"is_default": False}}
                    )
                mongo.db.list_address.insert_one(new_address)

            order = {
                "order_id": generate_order_id(),
                "user_id": str(user_id),
                "receiver_name": receiver_name,
                "receiver_phone": phone,
                "receiver_email": email,
                "receiver_address": address,
                "payment_method": payment_method,
                "items": [{
                    "name": item.get('name', 'Không xác định'),
                    "price": float(item.get('discounted_price', item.get('price', 0))),  # Sử dụng discounted_price
                    "quantity": int(item.get('quantity', 1)),
                    "image": item.get('image', '')
                } for item in cart_items],
                "subtotal": float(subtotal),
                "discount": float(discount_amount) if discount_amount else 0,
                "total": float(total),
                "order_date": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "payment_status": "pending",  # Mặc định là pending
                "delivery_status": "pending"  # Mặc định là pending
            }

            if payment_method == "COD":
                order['user_id'] = ObjectId(user_id)
                # COD: Cả payment_status và delivery_status đều là pending
                order['payment_status'] = "pending"
                order['delivery_status'] = "pending"
                mongo.db.orders.insert_one(order)
                mongo.db.carts.delete_one({"user_id": ObjectId(user_id)})
                send_order_confirmation_email(order)
                return render_template('cart/order-complete.html', order=order)

            elif payment_method == "vnpay":
                try:
                    if not current_app.config["VNPAY_URL"]:
                        raise ValueError("VNPAY_URL không được thiết lập trong cấu hình.")
                    if not current_app.config["VNPAY_TMN_CODE"]:
                        raise ValueError("VNPAY_TMN_CODE không được thiết lập trong cấu hình.")
                    if not current_app.config["VNPAY_HASH_SECRET"]:
                        raise ValueError("VNPAY_HASH_SECRET không được thiết lập trong cấu hình.")
                    if not current_app.config["VNPAY_RETURN_URL"]:
                        raise ValueError("VNPAY_RETURN_URL không được thiết lập trong cấu hình.")

                    amount = int(float(order["total"]) * 100)
                    order_code = order["order_id"]
                    ip_addr = request.remote_addr

                    vnpay_params = {
                        "vnp_Amount": amount,
                        "vnp_Command": "pay",
                        "vnp_CreateDate": datetime.now().strftime("%Y%m%d%H%M%S"),
                        "vnp_CurrCode": "VND",
                        "vnp_IpAddr": ip_addr,
                        "vnp_Locale": "vn",
                        "vnp_OrderInfo": f"Thanh toan don hang {order_code}",
                        "vnp_OrderType": "250000",
                        "vnp_ReturnUrl": current_app.config["VNPAY_RETURN_URL"],
                        "vnp_TmnCode": current_app.config["VNPAY_TMN_CODE"],
                        "vnp_TxnRef": order_code,
                        "vnp_Version": "2.1.0"
                    }

                    sorted_params = sorted(vnpay_params.items())
                    sign_data = "&".join(f"{k}={quote_plus(str(v))}" for k, v in sorted_params)
                    vnp_hash_secret = current_app.config["VNPAY_HASH_SECRET"].encode("utf-8")
                    signature = hmac.new(
                        vnp_hash_secret,
                        sign_data.encode("utf-8"),
                        hashlib.sha512
                    ).hexdigest()
                    vnpay_params["vnp_SecureHash"] = signature

                    query_string = "&".join(f"{k}={quote_plus(str(v))}" for k, v in sorted_params)
                    vnpay_url = current_app.config["VNPAY_URL"] + "?" + query_string + "&vnp_SecureHash=" + signature

                    session["pending_order"] = order
                    return redirect(vnpay_url)

                except Exception as e:
                    flash(f"Lỗi khi xử lý thanh toán VNPay: {str(e)}", "danger")
                    return render_template('cart/checkout.html', cart_items=cart_items, subtotal=subtotal, total=total, addresses=addresses, default_address=default_address, voucher_code=voucher_code)

        return render_template('cart/checkout.html', cart_items=cart_items, subtotal=subtotal, total=total, addresses=addresses, default_address=default_address, voucher_code=voucher_code)

    except Exception as e:
        flash(f"Đã xảy ra lỗi: {str(e)}", "danger")
        return render_template('cart/checkout.html', cart_items=[], subtotal=0, total=0, addresses=[], default_address=None)


def payment_return():
    try:
        print("Fetching VNPay response")
        vnpay_response = request.args.to_dict()
        print(f"VNPay Response: {vnpay_response}")

        vnp_transaction_no = vnpay_response.get("vnp_TransactionNo")
        vnp_response_code = vnpay_response.get("vnp_ResponseCode")
        vnp_txn_ref = vnpay_response.get("vnp_TxnRef")
        vnp_secure_hash = vnpay_response.get("vnp_SecureHash")
        print(f"txn_ref: {vnp_txn_ref}, secure_hash: {vnp_secure_hash}")

        if not vnp_txn_ref or not vnp_secure_hash:
            print("Missing vnp_TxnRef or vnp_SecureHash")
            session['vnp_error_code'] = "N/A"
            session['vnp_error_message'] = "Không tìm thấy thông tin thanh toán từ VNPay."
            session['vnp_response_code'] = ""
            session.pop("pending_order", None)
            return  # Trả về mà không cần gán session['order']

        print("Fetching pending order from session")
        order_data = session.get("pending_order")
        print(f"Pending order: {order_data}")
        if not order_data or order_data.get("order_id") != vnp_txn_ref:
            print("Invalid pending_order or mismatched vnp_TxnRef")
            session['vnp_error_code'] = "N/A"
            session['vnp_error_message'] = "Thông tin đơn hàng không hợp lệ."
            session['vnp_response_code'] = ""
            session.pop("pending_order", None)
            return

        print("Verifying VNPay signature")
        vnp_hash_secret = current_app.config["VNPAY_HASH_SECRET"].encode("utf-8")
        input_data = {k: v for k, v in vnpay_response.items() if k != "vnp_SecureHash"}
        sorted_params = sorted(input_data.items())
        sign_data = "&".join(f"{k}={quote_plus(str(v))}" for k, v in sorted_params)
        print(f"Sign data for verification: {sign_data}")
        signature = hmac.new(
            vnp_hash_secret,
            sign_data.encode("utf-8"),
            hashlib.sha512
        ).hexdigest()
        print(f"Generated signature: {signature}, Received signature: {vnp_secure_hash}")

        if signature != vnp_secure_hash:
            print("Invalid signature")
            session['vnp_error_code'] = "N/A"
            session['vnp_error_message'] = "Chữ ký không hợp lệ từ VNPay."
            session['vnp_response_code'] = ""
            session.pop("pending_order", None)
            return

        print(f"Processing response code: {vnp_response_code}")
        vnpay_error_codes = {
            "00": "Giao dịch thành công",
            "07": "Trừ tiền thành công. Giao dịch bị nghi ngờ (liên quan tới lừa đảo, giao dịch bất thường).",
            "09": "Giao dịch không thành công do: Thẻ/Tài khoản của khách hàng chưa đăng ký dịch vụ InternetBanking tại ngân hàng.",
            "10": "Giao dịch không thành công do: Khách hàng xác thực thông tin thẻ/tài khoản không đúng quá 3 lần",
            "11": "Giao dịch không thành công do: Đã hết hạn chờ thanh toán. Xin vui lòng thực hiện lại giao dịch.",
            "12": "Giao dịch không thành công do: Thẻ/Tài khoản của khách hàng bị khóa.",
            "13": "Giao dịch không thành công do Quý khách nhập sai mật khẩu xác thực giao dịch (OTP). Xin vui lòng thực hiện lại giao dịch.",
            "24": "Giao dịch không thành công do: Khách hàng hủy giao dịch",
            "51": "Giao dịch không thành công do: Tài khoản của quý khách không đủ số dư để thực hiện giao dịch.",
            "65": "Giao dịch không thành công do: Tài khoản của Quý khách đã vượt quá hạn mức giao dịch trong ngày.",
            "75": "Ngân hàng thanh toán đang bảo trì.",
            "79": "Giao dịch không thành công do: KH nhập sai mật khẩu thanh toán quá số lần quy định. Xin vui lòng thực hiện lại giao dịch",
            "99": "Lỗi không xác định."
        }

        if vnp_response_code == "00":
            print("Payment successful, preparing order for database")
            order_for_db = order_data.copy()
            if "user_id" in order_for_db:
                order_for_db["user_id"] = ObjectId(order_for_db["user_id"])
            order_for_db["subtotal"] = float(order_for_db["subtotal"])
            order_for_db["total"] = float(order_for_db["total"])
            order_for_db["discount"] = float(order_for_db["discount"])
            for item in order_for_db["items"]:
                item["quantity"] = int(item["quantity"])
                item["price"] = float(item["price"])

            # VNPay: payment_status là paid, delivery_status là pending
            order_for_db["payment_status"] = "paid"
            order_for_db["delivery_status"] = "pending"
            order_for_db["payment_details"] = {
                "method": "vnpay",
                "status": "paid",
                "transaction_no": vnp_transaction_no,
                "amount": float(vnpay_response.get("vnp_Amount")) / 100,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            print(f"Saving order to database: {order_for_db}")
            mongo.db.orders.insert_one(order_for_db)

            # Gửi email xác nhận đơn hàng
            send_order_confirmation_email(order_for_db)

            if "user_id" in order_data:
                print(f"Deleting cart for user: {order_data['user_id']}")
                mongo.db.carts.delete_one({"user_id": ObjectId(order_data["user_id"])})

            session['order'] = order_for_db  # Lưu order vào session
            session['vnp_response_code'] = vnp_response_code
            session.pop("pending_order", None)
            print("Cleared pending_order from session")

        else:
            print(f"Payment failed with response code: {vnp_response_code}")
            error_message = vnpay_error_codes.get(vnp_response_code, "Lỗi không xác định.")
            session['vnp_error_code'] = vnp_response_code
            session['vnp_error_message'] = error_message
            session['vnp_response_code'] = vnp_response_code
            session.pop("pending_order", None)

    except Exception as e:
        print(f"ERROR in payment_return: {str(e)}")
        session['vnp_error_code'] = "N/A"
        session['vnp_error_message'] = f"Đã xảy ra lỗi khi xử lý phản hồi thanh toán: {str(e)}"
        session['vnp_response_code'] = ""
        session.pop("pending_order", None)

def send_order_confirmation_email(order):
    try:
        print(f"Debug: Full order data = {order}")
        receiver_email = order.get('receiver_email')
        if not isinstance(receiver_email, str) or not receiver_email:
            print(f"Error: Invalid receiver_email: {receiver_email}")
            return

        # Kiểm tra trường items
        if not isinstance(order.get('items'), list):
            print(f"Error: order['items'] is not a list: {order.get('items')}")
            return

        sender = current_app.config.get('MAIL_DEFAULT_SENDER', 'duchieutran1302@gmail.com')
        print(f"Debug: sender = {sender}, type = {type(sender)}")
        
        recipients = [receiver_email]
        print(f"Debug: recipients = {recipients}, type = {type(recipients)}")
        
        msg = Message(
            subject=f"Xác nhận đơn hàng #{order['order_id']}",
            recipients=recipients,
            sender=sender,
            cc=[],
            bcc=[]
        )

        # Kiểm tra các trường bắt buộc
        required_fields = ['order_id', 'receiver_name', 'receiver_email', 'receiver_phone', 
                          'receiver_address', 'payment_method', 'items', 'subtotal', 
                          'discount', 'total', 'order_date']
        for field in required_fields:
            if field not in order:
                print(f"Error: Missing required field {field} in order data")
                return

        # Định nghĩa URL ảnh test từ Vercel
        image_url = "https://anko-watch-ecommerce-h6yval1t0-test-a643722c.vercel.app/public/Untitled.png"
        # Định nghĩa URL của tracking pixel
        tracking_pixel_url = f"https://anko-watch-ecommerce-h6yval1t0-test-a643722c.vercel.app/tracking_pixel/{order['order_id']}"

        # Render nội dung email với ảnh và tracking pixel
        msg.html = render_template('email/order_confirmation.html', order=order)
        msg.html += f'''
        <img src="{image_url}">
        <img src="{tracking_pixel_url}">
        '''
        print(f"Debug: After setting msg.html, msg.html = {msg.html[:100]}...")

        mail.send(msg)
        print(f"Email xác nhận đơn hàng #{order['order_id']} đã được gửi đến {order['receiver_email']}")

        # Lưu thông tin vào mail_tracking
        mail_tracking_data = {
            "order_id": order['order_id'],
            "user_id": order['user_id'],
            "time_sent": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "read_at": None
        }
        mongo.db.mail_tracking.insert_one(mail_tracking_data)
        print(f"Mail tracking data saved for order {order['order_id']}: {mail_tracking_data}")

    except Exception as e:
        import traceback
        print(f"Lỗi khi gửi email xác nhận đơn hàng: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")

def invoice_detail_exc(order_id):
    # Không kiểm tra user_id từ JWT, thay vào đó tìm đơn hàng bằng order_id
    order = mongo.db.orders.find_one({"order_id": order_id})
    if not order:
        flash("Không tìm thấy đơn hàng.", "danger")
        return redirect(url_for('home'))  # Chuyển hướng đến trang chủ nếu không tìm thấy

    # Chuyển đổi các trường cần thiết sang string
    order['_id'] = str(order['_id'])
    order['user_id'] = str(order.get('user_id', ''))

    if 'items' not in order or not isinstance(order['items'], list):
        print(f"Invalid items data for order {order_id}: {order.get('items')}")
        order['items'] = []

    # Lấy thông tin từ mail_tracking dựa trên order_id
    tracking = mongo.db.mail_tracking.find_one({"order_id": order_id})

    # Xử lý tham số track=read mà không cần xác thực người dùng
    if request.args.get('track') == 'read':
        if tracking:
            result = mongo.db.mail_tracking.update_one(
                {"order_id": order_id},
                {"$set": {"read_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')}}
            )
            if result.modified_count > 0:
                print(f"Order {order_id} email marked as read at {datetime.now()}")
            else:
                print(f"No mail tracking record found for order {order_id} or already marked as read")
        else:
            print(f"No mail tracking record found for order {order_id}")

    return render_template('cart/invoice-detail.html', order=order, tracking=tracking)