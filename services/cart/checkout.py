from flask import jsonify, render_template, flash, redirect, url_for, session, request, current_app
from flask_jwt_extended import get_jwt_identity, get_jwt, jwt_required
from app import mongo
from bson import ObjectId
from datetime import datetime, timedelta
import random
import string
import requests
import json
import hmac
import hashlib
from urllib.parse import urlencode

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
        if not cart or 'products' not in cart:
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
                    price = float(product['price']) if isinstance(product['price'], (str, int)) else product['price']
                    subtotal += price * item['quantity']
                    cart_items.append(product)
                    break

        if not cart_items:
            flash("Không có sản phẩm hợp lệ trong giỏ hàng.", "warning")
            return redirect(url_for('cart'))

        # Áp dụng voucher nếu có
        voucher_code = request.args.get('voucher_code') or session.get('voucher_code')
        voucher_discount = 0
        if voucher_code:
            discount_amount, message = apply_voucher(voucher_code, subtotal)
            if discount_amount:
                voucher_discount = discount_amount
                session['voucher_code'] = voucher_code
                session['voucher_discount'] = voucher_discount
            else:
                session.pop('voucher_code', None)
                session.pop('voucher_discount', None)

        total = subtotal - (float(discount_amount) + voucher_discount)

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
                return redirect(url_for('checkout'))

            selected_address_id = request.form.get('selected_address')
            if selected_address_id:
                selected_address = next((addr for addr in addresses if addr['_id'] == selected_address_id), None)
                if not selected_address:
                    flash("Địa chỉ không hợp lệ.", "danger")
                    return redirect(url_for('checkout'))
                address = selected_address['street']
                phone = selected_address['phone']
            else:
                address = request.form.get('address')
                phone = request.form.get('phone')
                address_type = request.form.get('addressType')
                set_default = request.form.get('setDefault') == 'on'

                if not address or not phone or not address_type:
                    flash("Vui lòng điền đầy đủ thông tin địa chỉ.", "danger")
                    return redirect(url_for('checkout'))

                if address_type not in ["Nhà riêng", "Văn phòng"]:
                    flash("Loại địa chỉ không hợp lệ.", "danger")
                    return redirect(url_for('checkout'))

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

            # Tạo đơn hàng
            order = {
                "order_id": generate_order_id(),
                "user_id": str(user_id),  # Lưu user_id dưới dạng string
                "receiver_name": receiver_name,
                "receiver_phone": phone,
                "receiver_email": email,
                "receiver_address": address,
                "payment_method": payment_method,
                "items": [{
                    "name": item.get('name'),
                    "price": float(item.get('price', 0)),
                    "quantity": int(item.get('quantity', 1)),
                    "image": item.get('image', '')
                } for item in cart_items],
                "subtotal": float(subtotal),
                "discount": float(discount_amount) if discount_amount else 0,
                "total": float(total),
                "order_date": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "payment_status": "pending",
                "delivery_status": "pending"
            }

            if payment_method == "COD":
                # Xử lý thanh toán COD
                order['user_id'] = ObjectId(user_id)  # Chuyển về ObjectId cho MongoDB
                mongo.db.orders.insert_one(order)
                mongo.db.carts.delete_one({"user_id": ObjectId(user_id)})
                return render_template('cart/order-complete.html', order=order)

            elif payment_method == "vnpay":
                try:
                    # Kiểm tra các giá trị cấu hình VNPay
                    if not current_app.config["VNPAY_URL"]:
                        raise ValueError("VNPAY_URL không được thiết lập trong cấu hình.")
                    if not current_app.config["VNPAY_TMN_CODE"]:
                        raise ValueError("VNPAY_TMN_CODE không được thiết lập trong cấu hình.")
                    if not current_app.config["VNPAY_HASH_SECRET"]:
                        raise ValueError("VNPAY_HASH_SECRET không được thiết lập trong cấu hình.")
                    if not current_app.config["VNPAY_RETURN_URL"]:
                        raise ValueError("VNPAY_RETURN_URL không được thiết lập trong cấu hình.")

                    # Chuẩn bị dữ liệu gửi đến VNPay
                    amount = int(float(order["total"]) * 100)  # VNPay yêu cầu số tiền tính bằng VND, nhân 100
                    order_code = order["order_id"]
                    ip_addr = request.remote_addr  # Lấy địa chỉ IP của client

                    vnpay_params = {
                        "vnp_Version": "2.1.0",
                        "vnp_Command": "pay",
                        "vnp_TmnCode": current_app.config["VNPAY_TMN_CODE"],
                        "vnp_Amount": amount,
                        "vnp_CurrCode": "VND",
                        "vnp_TxnRef": order_code,
                        "vnp_OrderInfo": f"Thanh toan don hang {order_code}",
                        "vnp_OrderType": "250000",  # Loại hàng hóa (tùy chọn, ví dụ: 250000 - Thời trang)
                        "vnp_Locale": "vn",
                        "vnp_ReturnUrl": current_app.config["VNPAY_RETURN_URL"],
                        "vnp_IpAddr": ip_addr,
                        "vnp_CreateDate": datetime.now().strftime("%Y%m%d%H%M%S"),
                    }

                    # Sắp xếp các tham số theo thứ tự khóa và tạo chữ ký
                    sorted_params = sorted(vnpay_params.items())
                    sign_data = "&".join(f"{k}={v}" for k, v in sorted_params)
                    vnp_hash_secret = current_app.config["VNPAY_HASH_SECRET"].encode("utf-8")
                    signature = hmac.new(
                        vnp_hash_secret,
                        sign_data.encode("utf-8"),
                        hashlib.sha512
                    ).hexdigest()
                    vnpay_params["vnp_SecureHash"] = signature

                    # Tạo URL thanh toán
                    vnpay_url = current_app.config["VNPAY_URL"] + "?" + urlencode(vnpay_params)
                    print("VNPay URL:", vnpay_url)

                    # Lưu đơn hàng vào session trước khi redirect
                    session["pending_order"] = order
                    return redirect(vnpay_url)

                except Exception as e:
                    print(f"Error in VNPay payment processing: {str(e)}")
                    flash(f"Lỗi khi xử lý thanh toán VNPay: {str(e)}", "danger")
                    return redirect(url_for('checkout'))

        return render_template('cart/checkout.html', cart_items=cart_items, subtotal=subtotal, total=total, addresses=addresses, default_address=default_address)

    except Exception as e:
        print(f"Error in checkout_exc: {str(e)}")
        flash(f"Đã xảy ra lỗi: {str(e)}", "danger")
        return render_template('cart/checkout.html', cart_items=[], subtotal=0, total=0, addresses=[], default_address=None)

def payment_return():
    """Xử lý phản hồi từ VNPay sau khi thanh toán."""
    try:
        user_id = get_jwt_identity()
        if not user_id:
            flash("Vui lòng đăng nhập để tiếp tục.", "danger")
            return redirect(url_for("login"))

        # Lấy dữ liệu phản hồi từ VNPay
        vnpay_response = request.args.to_dict()
        print("VNPay Response:", vnpay_response)

        vnp_transaction_no = vnpay_response.get("vnp_TransactionNo")
        vnp_response_code = vnpay_response.get("vnp_ResponseCode")
        vnp_txn_ref = vnpay_response.get("vnp_TxnRef")
        vnp_secure_hash = vnpay_response.get("vnp_SecureHash")

        if not vnp_txn_ref or not vnp_secure_hash:
            flash("Không tìm thấy thông tin thanh toán từ VNPay.", "danger")
            session.pop("pending_order", None)
            return redirect(url_for("orders"))

        # Lấy đơn hàng từ session
        order_data = session.get("pending_order")
        if not order_data or order_data.get("order_id") != vnp_txn_ref:
            flash("Thông tin đơn hàng không hợp lệ.", "danger")
            session.pop("pending_order", None)
            return redirect(url_for("orders"))

        # Kiểm tra chữ ký từ VNPay
        vnp_hash_secret = current_app.config["VNPAY_HASH_SECRET"].encode("utf-8")
        input_data = {k: v for k, v in vnpay_response.items() if k != "vnp_SecureHash"}
        sorted_params = sorted(input_data.items())
        sign_data = "&".join(f"{k}={v}" for k, v in sorted_params)
        signature = hmac.new(
            vnp_hash_secret,
            sign_data.encode("utf-8"),
            hashlib.sha512
        ).hexdigest()

        if signature != vnp_secure_hash:
            flash("Chữ ký không hợp lệ từ VNPay.", "danger")
            session.pop("pending_order", None)
            return redirect(url_for("checkout"))

        if vnp_response_code == "00":
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
                "method": "vnpay",
                "status": "paid",
                "transaction_no": vnp_transaction_no,
                "amount": float(vnpay_response.get("vnp_Amount")) / 100,  # Chia 100 để về VND
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

        else:
            # Thanh toán thất bại
            flash(f"Thanh toán thất bại. Mã lỗi: {vnp_response_code}", "danger")
            session.pop("pending_order", None)
            return redirect(url_for("checkout"))

    except Exception as e:
        print(f"Error in payment_return: {str(e)}")
        flash(f"Đã xảy ra lỗi khi xử lý phản hồi thanh toán: {str(e)}", "danger")
        session.pop("pending_order", None)
        return redirect(url_for("checkout"))

def invoice_detail_exc(order_id):
    # Lấy user_id từ JWT
    user_id = get_jwt_identity()
    if not user_id:
        return redirect(url_for('login'))

    # Tìm đơn hàng trong database
    order = mongo.db.orders.find_one({"order_id": order_id, "user_id": ObjectId(user_id)})
    if not order:
        flash("Không tìm thấy đơn hàng.", "danger")
        return redirect(url_for('orders'))

    # Chuyển đổi ObjectId thành string
    order['_id'] = str(order['_id'])
    order['user_id'] = str(order['user_id'])

    # Kiểm tra và đảm bảo order['items'] là danh sách
    if 'items' not in order or not isinstance(order['items'], list):
        print(f"Invalid items data for order {order_id}: {order.get('items')}")
        order['items'] = []  # Gán mặc định là danh sách rỗng để tránh lỗi

    return render_template('cart/invoice-detail.html', order=order)