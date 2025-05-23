import json
from io import BytesIO
import requests
from bson import ObjectId
from PIL import Image
from flask import Blueprint, jsonify, render_template, request, make_response, flash, redirect, url_for, session, send_file
from flask_jwt_extended import get_jwt_identity, jwt_required
from services.account import change_password_exc
from services.account.account_exc import get_user_info, update_user_info
from services.account.address_exc import add_address_exc, delete_address_exc, get_addresses_exc, update_address_exc
from services.account.favourites_exc import add_to_favourites_exc, get_favorite_products_exc, remove_from_favorites_exc
from services.account.orders_exc import get_orders
from services.admin.product_exc import add_brand_exc, add_category_exc, add_product_exc, delete_brand_exc, delete_category_exc, delete_product_exc, get_all_brands_exc, get_all_categories_exc, get_all_products_exc, update_brand_exc, update_category_exc, update_product_exc
from services.admin.report_exc import export_revenue_report_to_excel, get_revenue_report
from services.admin.vouchers_exc import add_voucher_exc, delete_voucher_exc, get_all_vouchers, get_voucher_details, update_voucher_exc
from services.cart import add_to_cart, remove_cart, update_cart
from services.cart.cart import cart_exc
from services.cart.cart_count import cart_count_exc
from services.middleware import permission_required, role_required
from app import app, mongo, cache, mail
from services.auth.register_exc import register_exc
from services.auth.login_exc import login_exc
from flask_login import logout_user
from services.policy.news_exc import get_all_news, get_news_detail
from services.product.product_detail_exc import product_detail_exc
from services.product.search_exc import search_exc
from services.cart.checkout import apply_voucher_exc, checkout_exc, invoice_detail_exc, payment_return
from services.admin.customer_exc import delete_customer_exc, delete_role_exc, get_all_customers_exc, get_all_permissions_exc, update_customer_role_exc, get_all_roles_exc, add_role_exc, update_role_exc
from services.admin.dashboard_exc import get_dashboard_stats
from services.admin.orders_exc import get_all_orders, get_orders_by_status, get_order_details, update_order_status
from flask_mail import Message
from datetime import datetime

# User Routes
@app.route('/')
def home():
    # Lấy danh sách sản phẩm bán chạy từ collection products
    products = list(mongo.db.products.find(
        {},
        {"_id": 1, "name": 1, "brand_id": 1, "image": 1, "price": 1, "discount": 1, "discounted_price": 1}
    ).sort("_id", -1).limit(8))
    
    # Duyệt qua từng sản phẩm để lấy tên thương hiệu từ brand_id
    for product in products:
        product['_id'] = str(product['_id'])
        # Truy vấn collection brands để lấy tên thương hiệu
        if 'brand_id' in product and product['brand_id']:
            brand = mongo.db.brands.find_one({"_id": ObjectId(product['brand_id'])}, {"name": 1})
            product['brand'] = brand['name'] if brand else "Không xác định"
        else:
            product['brand'] = "Không xác định"
        # Đảm bảo price, discount và discounted_price có giá trị hợp lệ
        product['price'] = float(product.get('price', 0))
        product['discount'] = float(product.get('discount', 0))
        product['discounted_price'] = float(product.get('discounted_price', product['price']))

    # Lấy danh sách sản phẩm khuyến mãi từ collection products
    sale_products = list(mongo.db.products.find(
        {"discount": {"$exists": True, "$gt": 0}},
        {"_id": 1, "name": 1, "brand_id": 1, "image": 1, "price": 1, "discount": 1, "discounted_price": 1}
    ).sort("_id", -1).limit(8))
    
    for product in sale_products:
        product['_id'] = str(product['_id'])
        if 'brand_id' in product and product['brand_id']:
            brand = mongo.db.brands.find_one({"_id": ObjectId(product['brand_id'])}, {"name": 1})
            product['brand'] = brand['name'] if brand else "Không xác định"
        else:
            product['brand'] = "Không xác định"
        product['price'] = float(product.get('price', 0))
        product['discount'] = float(product.get('discount', 0))
        product['discounted_price'] = float(product.get('discounted_price', product['price']))
        product['discount_percent'] = int(product['discount'])

    try:
        from flask_jwt_extended import verify_jwt_in_request
        verify_jwt_in_request(optional=True)
    except Exception:
        pass

    return render_template("base.html", products=products, sale_products=sale_products)

@app.route("/login", methods=["GET", "POST"])
def login():
    return login_exc()

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        return register_exc()
    return render_template('auth/register.html')

@app.route('/forgot-password')
def forgot_password():
    return render_template('auth/forgot-password.html')

@app.route('/reset-password')
def reset_password():
    return render_template('auth/reset-password.html')

@app.route('/product/<product_id>')
def product_detail(product_id):
    return product_detail_exc(product_id)

@app.route('/cart-count', methods=['GET'])
@jwt_required()
def cart_count():
    return cart_count_exc()

@app.route('/account', methods=['GET', 'POST'])
@jwt_required()
def account():
    if not session.get("user_id"):
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        result = update_user_info()
        user = get_user_info()
        return render_template('account/account.html', current_user=user, **result)

    user = get_user_info()
    return render_template('account/account.html', current_user=user)

@app.route('/orders')
def orders():
    if not session.get("user_id"):
        return redirect(url_for('auth.login'))

    orders = get_orders()
    if not orders:
        flash("Không có đơn hàng nào", "danger")
        orders = []
    return render_template('account/list-orders.html', current_user=get_user_info(), orders=orders) 

@app.route('/favourites', methods=['GET', 'POST'])
@jwt_required()
def favourites():
    if not session.get("user_id"):
        return redirect(url_for('login'))

    if request.method == 'POST':
        product_id = request.form.get("product_id")
        remove_from_favorites_exc(product_id)
        favorite_products = get_favorite_products_exc()
        return render_template('account/favourites.html', current_user=get_user_info(), favorite_products=favorite_products)

    favorite_products = get_favorite_products_exc()
    return render_template('account/favourites.html', current_user=get_user_info(), favorite_products=favorite_products)   

@app.route('/add_to_favourites/<product_id>', methods=['POST'])
@jwt_required()
def add_to_favourites(product_id):
    result = add_to_favourites_exc(product_id)
    return jsonify(result)

@app.route('/address', methods=['GET', 'POST'])
@jwt_required()
def address():
    if not session.get("user_id"):
        return redirect(url_for('login'))

    addresses = get_addresses_exc()
    success_message = session.pop('success_message', None)
    error_message = session.pop('error_message', None)
    
    success_message = success_message if success_message else ''
    error_message = error_message if error_message else ''
    
    return render_template('account/address.html',
                         current_user=get_user_info(),
                         addresses=addresses,
                         success_message=success_message,
                         error_message=error_message)

@app.route('/add_address', methods=['POST'])
@jwt_required()
def add_address():
    if not session.get("user_id"):
        return redirect(url_for('login'))

    result = add_address_exc()
    if "success" in result:
        session['success_message'] = result["success"]
    elif "error" in result:
        session['error_message'] = result["error"]
    return redirect(url_for('address'))

@app.route('/update_address/<address_id>', methods=['POST'])
@jwt_required()
def update_address(address_id):
    if not session.get("user_id"):
        return redirect(url_for('login'))

    result = update_address_exc(address_id)
    if "success" in result:
        session['success_message'] = result["success"]
    elif "error" in result:
        session['error_message'] = result["error"]
    return redirect(url_for('address'))

@app.route('/delete_address/<address_id>', methods=['POST'])
@jwt_required()
def delete_address(address_id):
    if not session.get("user_id"):
        return redirect(url_for('login'))

    result = delete_address_exc(address_id)
    if "success" in result:
        session['success_message'] = result["success"]
    elif "error" in result:
        session['error_message'] = result["error"]
    return redirect(url_for('address'))

@app.route('/change-password')
@jwt_required()
def change_password():
    if not session.get("user_id"):
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        result = change_password_exc()
        return render_template('account/change-password.html', current_user=get_user_info(), **result)

    return render_template('account/change-password.html', current_user=get_user_info())

@app.route('/payment_return', methods=['GET'])
def payment_return_route():
    print(f"Reached /payment_return route with args: {request.args.to_dict()}")
    print(f"Request headers: {request.headers}")
    
    result = payment_return()
    
    if isinstance(result, tuple) and result[0].status_code in (301, 302):
        return result
    
    order = session.get('order')
    vnp_response_code = session.get('vnp_response_code', '')
    vnp_error_code = session.get('vnp_error_code', 'N/A')
    vnp_error_message = session.get('vnp_error_message', 'Đã xảy ra lỗi không xác định trong quá trình thanh toán.')
    
    session.pop('order', None)
    session.pop('vnp_response_code', None)
    session.pop('vnp_error_code', None)
    session.pop('vnp_error_message', None)

    if not order:
        flash("Không tìm thấy thông tin đơn hàng. Vui lòng thử lại.", "danger")
        return redirect(url_for('checkout'))
    
    return render_template('cart/payment_return.html',
                         order=order,
                         vnp_response_code=vnp_response_code,
                         vnp_error_code=vnp_error_code,
                         vnp_error_message=vnp_error_message)

@app.route('/invoice/<order_id>')
def invoice_detail(order_id):
    return invoice_detail_exc(order_id)

# Error Routes
@app.route('/404')
def error_404():
    return render_template('error/404.html')

@app.route('/info')
def info():
    return render_template('policy/info.html')

@app.route('/news')
def news():
    news_data = get_all_news()
    return render_template('news.html', news=news_data)

@app.route('/news/<news_id>')
def news_detail(news_id):
    article = get_news_detail(news_id)
    return render_template('news-detail.html', article=article)
    
@app.route('/cart')
@jwt_required()
def cart():
    return cart_exc()

@app.route('/apply_voucher', methods=['POST'])
@jwt_required()
def apply_voucher_route():
    return apply_voucher_exc()
    
@app.route('/add_to_cart/<product_id>', methods=['POST'])
def add_to_cart_route(product_id):
    return add_to_cart.add_to_cart_exc(product_id)

@app.route('/cart/update_quantity/<product_id>/<action>', methods=['POST'])
def update_cart_route(product_id, action):
    return update_cart.update_cart_exc(product_id, action)

@app.route('/cart/remove/<product_id>', methods=['POST'])
def remove_from_cart_route(product_id):
    return remove_cart.remove_cart_exc(product_id)

@app.route('/search')
@cache.cached(timeout=300, query_string=True)  # Cache 5 phút, bao gồm query parameters
def search():
    product_list, category_mapping, message = search_exc()
    query = request.args.get('q', '')
    category = request.args.get('category', '')
    sort = request.args.get('sort', 'relevance')
    brands = request.args.getlist('brand')
    price_ranges = request.args.getlist('price_range')

    return render_template('product/search.html', 
                          products=product_list, 
                          category_mapping=category_mapping,
                          message=message,
                          query=query, 
                          category=category, 
                          sort=sort, 
                          brands=brands, 
                          price_ranges=price_ranges)

@app.route('/checkout', methods=['GET', 'POST'])
@jwt_required()
def checkout():
    return checkout_exc()

@app.route('/order-complete')
def order_complete():
    order = session.get("order")
    if not order:
        return redirect(url_for("home"))
    return render_template("cart/order-complete.html", order=order)


@app.route('/policy')
def policy():
    return render_template('policy/policy.html')

# Admin Routes
@app.route('/admin/dashboard')
@jwt_required()
@role_required('admin')
@permission_required('MANAGE_DASHBOARD')
def dashboard():
    return get_dashboard_stats()    

@app.route('/admin/orders')
@jwt_required()
@permission_required('MANAGE_ORDERS')
@cache.cached(timeout=300)  # Cache 5 phút
def admin_orders():
    all_orders = get_all_orders()
    for order in all_orders:
        order['_id'] = str(order['_id'])
        order['items'] = order.get('items', [])
        order['customer_name'] = order.get('customer_name', order.get('receiver_name', 'Không xác định'))
        order['status'] = order.get('status', order.get('delivery_status', 'Không xác định'))

    waiting_for_shipping = get_orders_by_status("waiting_for_shipping")
    for order in waiting_for_shipping:
        order['_id'] = str(order['_id'])
        order['items'] = order.get('items', [])
        order['customer_name'] = order.get('customer_name', order.get('receiver_name', 'Không xác định'))
        order['status'] = order.get('status', order.get('delivery_status', 'Không xác định'))

    waiting_for_delivery = get_orders_by_status("waiting_for_delivery")
    for order in waiting_for_delivery:
        order['_id'] = str(order['_id'])
        order['items'] = order.get('items', [])
        order['customer_name'] = order.get('customer_name', order.get('receiver_name', 'Không xác định'))
        order['status'] = order.get('status', order.get('delivery_status', 'Không xác định'))

    completed = get_orders_by_status("completed")
    for order in completed:
        order['_id'] = str(order['_id'])
        order['items'] = order.get('items', [])
        order['customer_name'] = order.get('customer_name', order.get('receiver_name', 'Không xác định'))
        order['status'] = order.get('status', order.get('delivery_status', 'Không xác định'))

    cancelled = get_orders_by_status("cancelled")
    for order in cancelled:
        order['_id'] = str(order['_id'])
        order['items'] = order.get('items', [])
        order['customer_name'] = order.get('customer_name', order.get('receiver_name', 'Không xác định'))
        order['status'] = order.get('status', order.get('delivery_status', 'Không xác định'))

    returned = get_orders_by_status("returned")
    for order in returned:
        order['_id'] = str(order['_id'])
        order['items'] = order.get('items', [])
        order['customer_name'] = order.get('customer_name', order.get('receiver_name', 'Không xác định'))
        order['status'] = order.get('status', order.get('delivery_status', 'Không xác định'))

    return render_template('admin/orders.html', 
                           all_orders=all_orders, 
                           waiting_for_shipping=waiting_for_shipping,
                           waiting_for_delivery=waiting_for_delivery,
                           completed=completed, 
                           cancelled=cancelled, 
                           returned=returned)

@app.route('/admin/order/<order_id>')
@jwt_required()
@permission_required('MANAGE_ORDERS')
@cache.cached(timeout=300)  # Cache 5 phút
def admin_order_details(order_id):
    try:
        order = get_order_details(order_id)
        if order:
            order['_id'] = str(order['_id'])
            order['order_id'] = order['_id']
            order['receiver_name'] = order.get('receiver_name', 'Không xác định')
            order['delivery_status'] = order.get('delivery_status', order.get('status', 'Không xác định'))
            order['receiver_address'] = order.get('receiver_address', 'Không xác định')
            order['payment_method'] = order.get('payment_method', 'Không xác định')
            order['items'] = order.get('items', [])

            total_amount = 0
            for item in order['items']:
                quantity = item.get('quantity', 0)
                price = item.get('price', 0)
                total_amount += quantity * price
            order['total_amount'] = total_amount

            for item in order['items']:
                item['name'] = item.get('name', 'Không xác định')
                item['quantity'] = item.get('quantity', 0)
                item['price'] = item.get('price', 0)

            return jsonify(order)
        else:
            return jsonify({"error": "Order not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/admin/update-order-status', methods=['POST'])
@jwt_required()
@permission_required('MANAGE_ORDERS')
def admin_update_order_status():
    try:
        order_id = request.form.get('order_id')
        delivery_status = request.form.get('delivery_status')
        payment_status = request.form.get('payment_status')

        if not order_id:
            return jsonify({"success": False, "message": "Thiếu order_id"}), 400

        result = update_order_status(order_id, delivery_status, payment_status)
        if result['success']:
            cache.delete_memoized(admin_orders)  # Xóa cache của /admin/orders
            cache.delete_memoized(admin_order_details, order_id)  # Xóa cache của chi tiết đơn hàng
        return jsonify(result), 200 if result['success'] else 400

    except Exception as e:
        print(f"Error in admin_update_order_status: {str(e)}")
        return jsonify({"success": False, "message": f"Lỗi server: {str(e)}"}), 500

@app.route('/admin/delete-order/<order_id>', methods=['DELETE'])
@jwt_required()
@permission_required('MANAGE_ORDERS')
def delete_order(order_id):
    try:
        result = mongo.db.orders.delete_one({"_id": ObjectId(order_id)})
        if result.deleted_count > 0:
            cache.delete_memoized(admin_orders)  # Xóa cache của /admin/orders
            cache.delete_memoized(admin_order_details, order_id)  # Xóa cache của chi tiết đơn hàng
            return jsonify({"success": True, "message": "Đơn hàng đã được xóa."})
        else:
            return jsonify({"success": False, "message": "Không tìm thấy đơn hàng."}), 404
    except Exception as e:
        return jsonify({"success": False, "message": f"Lỗi server: {str(e)}"}), 500

@app.route('/admin/products')
@jwt_required()
@permission_required('MANAGE_PRODUCTS')
@cache.cached(timeout=300)  # Cache 5 phút
def products():
    products = get_all_products_exc()
    categories = get_all_categories_exc()
    brands = get_all_brands_exc()
    return render_template('admin/products.html', products=products, categories=categories, brands=brands)

@app.route('/admin/add_product', methods=['POST'])
@jwt_required()
@permission_required('MANAGE_PRODUCTS')
def admin_add_product():
    data = request.form
    file = request.files.get('image')
    result = add_product_exc(data, file)
    if result.get("success"):
        cache.delete_memoized(products)  # Xóa cache của /admin/products
        cache.delete_memoized(home)  # Xóa cache của trang chủ
    response = make_response(redirect(url_for('products')))
    if "success" in result:
        response.headers['HX-Trigger'] = json.dumps({
            'showAlert': {
                'title': 'Thành công!',
                'message': result["success"],
                'icon': 'success'
            }
        })
    else:
        response.headers['HX-Trigger'] = json.dumps({
            'showAlert': {
                'title': 'Lỗi!',
                'message': result.get("error", "Có lỗi xảy ra!"),
                'icon': 'error'
            }
        })
    return response

@app.route('/admin/update_product/<product_id>', methods=['POST'])
@jwt_required()
@permission_required('MANAGE_PRODUCTS')
def admin_update_product(product_id):
    data = request.form
    file = request.files.get('image')
    result = update_product_exc(product_id, data, file)
    if result.get("success"):
        cache.delete_memoized(products)  # Xóa cache của /admin/products
        cache.delete_memoized(home)  # Xóa cache của trang chủ
    response = make_response(redirect(url_for('products')))
    if "success" in result:
        response.headers['HX-Trigger'] = json.dumps({
            'showAlert': {
                'title': 'Thành công!',
                'message': result["success"],
                'icon': 'success'
            }
        })
    else:
        response.headers['HX-Trigger'] = json.dumps({
            'showAlert': {
                'title': 'Lỗi!',
                'message': result.get("error", "Có lỗi xảy ra!"),
                'icon': 'error'
            }
        })
    return response

@app.route('/admin/delete_product/<product_id>', methods=['POST'])
@jwt_required()
@permission_required('MANAGE_PRODUCTS')
def admin_delete_product(product_id):
    result = delete_product_exc(product_id)
    if result.get("success"):
        cache.delete_memoized(products)  # Xóa cache của /admin/products
        cache.delete_memoized(home)  # Xóa cache của trang chủ
    response = make_response(redirect(url_for('products')))
    if "success" in result:
        response.headers['HX-Trigger'] = json.dumps({
            'showAlert': {
                'title': 'Thành công!',
                'message': result["success"],
                'icon': 'success'
            }
        })
    else:
        response.headers['HX-Trigger'] = json.dumps({
            'showAlert': {
                'title': 'Lỗi!',
                'message': result.get("error", "Có lỗi xảy ra!"),
                'icon': 'error'
            }
        })
    return response

@app.route('/admin/add_category', methods=['POST'])
@jwt_required()
@permission_required('MANAGE_PRODUCTS')
def admin_add_category():
    data = request.form
    result = add_category_exc(data)
    if result.get("success"):
        cache.delete_memoized(products)  # Xóa cache của /admin/products
    response = make_response(redirect(url_for('products')))
    if "success" in result:
        response.headers['HX-Trigger'] = json.dumps({
            'showAlert': {
                'title': 'Thành công!',
                'message': result["success"],
                'icon': 'success'
            }
        })
    else:
        response.headers['HX-Trigger'] = json.dumps({
            'showAlert': {
                'title': 'Lỗi!',
                'message': result.get("error", "Có lỗi xảy ra!"),
                'icon': 'error'
            }
        })
    return response

@app.route('/admin/update_category/<category_id>', methods=['POST'])
@jwt_required()
@permission_required('MANAGE_PRODUCTS')
def admin_update_category(category_id):
    data = request.form
    result = update_category_exc(category_id, data)
    if result.get("success"):
        cache.delete_memoized(products)  # Xóa cache của /admin/products
    response = make_response(redirect(url_for('products')))
    if "success" in result:
        response.headers['HX-Trigger'] = json.dumps({
            'showAlert': {
                'title': 'Thành công!',
                'message': result["success"],
                'icon': 'success'
            }
        })
    else:
        response.headers['HX-Trigger'] = json.dumps({
            'showAlert': {
                'title': 'Lỗi!',
                'message': result.get("error", "Có lỗi xảy ra!"),
                'icon': 'error'
            }
        })
    return response

@app.route('/admin/delete_category/<category_id>', methods=['POST'])
@jwt_required()
@permission_required('MANAGE_PRODUCTS')
def admin_delete_category(category_id):
    result = delete_category_exc(category_id)
    if result.get("success"):
        cache.delete_memoized(products)  # Xóa cache của /admin/products
    response = make_response(redirect(url_for('products')))
    if "success" in result:
        response.headers['HX-Trigger'] = json.dumps({
            'showAlert': {
                'title': 'Thành công!',
                'message': result["success"],
                'icon': 'success'
            }
        })
    else:
        response.headers['HX-Trigger'] = json.dumps({
            'showAlert': {
                'title': 'Lỗi!',
                'message': result.get("error", "Có lỗi xảy ra!"),
                'icon': 'error'
            }
        })
    return response

@app.route('/admin/add_brand', methods=['POST'])
@jwt_required()
@permission_required('MANAGE_PRODUCTS')
def admin_add_brand():
    data = request.form
    result = add_brand_exc(data)
    if result.get("success"):
        cache.delete_memoized(products)  # Xóa cache của /admin/products
        cache.delete_memoized(home)  # Xóa cache của trang chủ
    response = make_response(redirect(url_for('products')))
    if "success" in result:
        response.headers['HX-Trigger'] = json.dumps({
            'showAlert': {
                'title': 'Thành công!',
                'message': result["success"],
                'icon': 'success'
            }
        })
    else:
        response.headers['HX-Trigger'] = json.dumps({
            'showAlert': {
                'title': 'Lỗi!',
                'message': result.get("error", "Có lỗi xảy ra!"),
                'icon': 'error'
            }
        })
    return response

@app.route('/admin/update_brand/<brand_id>', methods=['POST'])
@jwt_required()
@permission_required('MANAGE_PRODUCTS')
def admin_update_brand(brand_id):
    data = request.form
    result = update_brand_exc(brand_id, data)
    if result.get("success"):
        cache.delete_memoized(products)  # Xóa cache của /admin/products
        cache.delete_memoized(home)  # Xóa cache của trang chủ
    response = make_response(redirect(url_for('products')))
    if "success" in result:
        response.headers['HX-Trigger'] = json.dumps({
            'showAlert': {
                'title': 'Thành công!',
                'message': result["success"],
                'icon': 'success'
            }
        })
    else:
        response.headers['HX-Trigger'] = json.dumps({
            'showAlert': {
                'title': 'Lỗi!',
                'message': result.get("error", "Có lỗi xảy ra!"),
                'icon': 'error'
            }
        })
    return response

@app.route('/admin/delete_brand/<brand_id>', methods=['POST'])
@jwt_required()
@permission_required('MANAGE_PRODUCTS')
def admin_delete_brand(brand_id):
    result = delete_brand_exc(brand_id)
    if result.get("success"):
        cache.delete_memoized(products)  # Xóa cache của /admin/products
        cache.delete_memoized(home)  # Xóa cache của trang chủ
    response = make_response(redirect(url_for('products')))
    if "success" in result:
        response.headers['HX-Trigger'] = json.dumps({
            'showAlert': {
                'title': 'Thành công!',
                'message': result["success"],
                'icon': 'success'
            }
        })
    else:
        response.headers['HX-Trigger'] = json.dumps({
            'showAlert': {
                'title': 'Lỗi!',
                'message': result.get("error", "Có lỗi xảy ra!"),
                'icon': 'error'
            }
        })
    return response

@app.route('/admin/customers')
@jwt_required()
@permission_required('MANAGE_USERS')
@cache.cached(timeout=300)  # Cache 5 phút
def customers():
    customers = get_all_customers_exc()
    roles = get_all_roles_exc()
    permissions = get_all_permissions_exc()
    return render_template('admin/customers.html', customers=customers, roles=roles, permissions=permissions)

@app.route('/admin/update_customer_role/<user_id>', methods=['POST'])
@jwt_required()
@permission_required('MANAGE_USERS')
def admin_update_customer_role(user_id):
    data = request.form
    result = update_customer_role_exc(user_id, data)
    if result.get("success"):
        cache.delete_memoized(customers)  # Xóa cache của /admin/customers
    response = make_response(redirect(url_for('customers')))
    if "success" in result:
        response.headers['HX-Trigger'] = json.dumps({
            'showAlert': {
                'title': 'Thành công!',
                'message': result["success"],
                'icon': 'success'
            }
        })
    else:
        response.headers['HX-Trigger'] = json.dumps({
            'showAlert': {
                'title': 'Lỗi!',
                'message': result.get("error", "Có lỗi xảy ra!"),
                'icon': 'error'
            }
        })
    return response

@app.route('/admin/add_role', methods=['POST'])
@jwt_required()
@permission_required('MANAGE_USERS')
def admin_add_role():
    data = request.form
    result = add_role_exc(data)
    if result.get("success"):
        cache.delete_memoized(customers)  # Xóa cache của /admin/customers
    response = make_response(redirect(url_for('customers')))
    if "success" in result:
        response.headers['HX-Trigger'] = json.dumps({
            'showAlert': {
                'title': 'Thành công!',
                'message': result["success"],
                'icon': 'success'
            }
        })
    else:
        response.headers['HX-Trigger'] = json.dumps({
            'showAlert': {
                'title': 'Lỗi!',
                'message': result.get("error", "Có lỗi xảy ra!"),
                'icon': 'error'
            }
        })
    return response

@app.route('/admin/update_role/<role_id>', methods=['POST'])
@jwt_required()
@permission_required('MANAGE_USERS')
def admin_update_role(role_id):
    data = request.form
    permission_ids = request.form.getlist('permission_ids')
    data = dict(data)
    data['permission_ids'] = permission_ids
    result = update_role_exc(role_id, data)
    if result.get("success"):
        cache.delete_memoized(customers)  # Xóa cache của /admin/customers
    response = make_response(redirect(url_for('customers')))
    if "success" in result:
        response.headers['HX-Trigger'] = json.dumps({
            'showAlert': {
                'title': 'Thành công!',
                'message': result["success"],
                'icon': 'success'
            }
        })
    else:
        response.headers['HX-Trigger'] = json.dumps({
            'showAlert': {
                'title': 'Lỗi!',
                'message': result.get("error", "Có lỗi xảy ra!"),
                'icon': 'error'
            }
        })
    return response

@app.route('/admin/delete_role/<role_id>', methods=['POST'])
@jwt_required()
@permission_required('MANAGE_USERS')
def admin_delete_role(role_id):
    result = delete_role_exc(role_id)
    if result.get("success"):
        cache.delete_memoized(customers)  # Xóa cache của /admin/customers
    return jsonify(result)

@app.route('/admin/delete_customer/<user_id>', methods=['POST'])
@jwt_required()
@permission_required('MANAGE_USERS')
def admin_delete_customer(user_id):
    result = delete_customer_exc(user_id)
    if result.get("success"):
        cache.delete_memoized(customers)  # Xóa cache của /admin/customers
    return jsonify(result)

@app.route('/admin/reports', methods=['GET', 'POST'])
@jwt_required()
@permission_required('MANAGE_REPORTS')
@cache.cached(timeout=300, query_string=True)  # Cache 5 phút
def reports():
    time_frame = request.args.get('time_frame', 'month')
    if time_frame not in ['week', 'month', 'quarter', 'year']:
        time_frame = 'month'

    report_data = get_revenue_report(time_frame)
    print("report_data:", report_data)
    return render_template('admin/reports.html', report_data=report_data)

@app.route('/admin/export_revenue_report')
@jwt_required()
@permission_required('MANAGE_REPORTS')
def export_revenue_report():
    return export_revenue_report_to_excel()

@app.route('/admin/vouchers', methods=['GET'])
@jwt_required()
@permission_required('MANAGE_VOUCHERS')
@cache.cached(timeout=300, query_string=True)  # Cache 5 phút
def vouchers():
    search_query = request.args.get('search', '')
    vouchers = get_all_vouchers(search_query)
    if request.headers.get('Content-Type') == 'application/json':
        return jsonify(vouchers)
    return render_template('admin/vouchers.html', vouchers=vouchers)

@app.route('/admin/voucher/<voucher_id>', methods=['GET'])
@jwt_required()
@permission_required('MANAGE_VOUCHERS')
@cache.cached(timeout=300)  # Cache 5 phút
def voucher_details(voucher_id):
    voucher = get_voucher_details(voucher_id)
    if voucher:
        return jsonify(voucher)
    return jsonify({"error": "Voucher not found"}), 404

@app.route('/admin/add_voucher', methods=['POST'])
@jwt_required()
@permission_required('MANAGE_VOUCHERS')
def admin_add_voucher():
    result = add_voucher_exc()
    if result.get("success"):
        cache.delete_memoized(vouchers)  # Xóa cache của /admin/vouchers
    return result

@app.route('/admin/update_voucher', methods=['POST'])
@jwt_required()
@permission_required('MANAGE_VOUCHERS')
def admin_update_voucher():
    result = update_voucher_exc()
    if result.get("success"):
        cache.delete_memoized(vouchers)  # Xóa cache của /admin/vouchers
    return result

@app.route('/admin/delete_voucher/<voucher_id>', methods=['POST'])
@jwt_required()
@permission_required('MANAGE_VOUCHERS')
def admin_delete_voucher(voucher_id):
    result = delete_voucher_exc(voucher_id)
    if result.get("success"):
        cache.delete_memoized(vouchers)  # Xóa cache của /admin/vouchers
    return result

# Routes Delivery
@app.route('/delivery/login', methods=['GET', 'POST'])
def delivery_login():
    return render_template('delivery/auth/login.html')
 
@app.route('/delivery')
def delivery():
    return render_template('delivery/index.html')

@app.route("/logout")
def logout():
    response = make_response(redirect(url_for('home')))
    response.set_cookie('access_token_cookie', '', expires=0)
    response.set_cookie('access_token', '', expires=0)
    response.headers['HX-Trigger'] = json.dumps({
        'clearToken': True,
        'showSuccessAlert': {
            'title': 'Thành công!',
            'message': 'Bạn đã đăng xuất thành công'
        }
    })
    try:
        logout_user()
    except Exception:
        pass
    session.clear()    
    return response

@app.route('/tracking_image/<order_id>')
def tracking_image(order_id):
    try:
        # URL của hình ảnh từ cms.123code.net
        image_url = "https://cms.123code.net/uploads/2024/12/06/2024-12-06__tableau-chat.webp"
        
        # Tải hình ảnh từ URL
        response = requests.get(image_url)
        if response.status_code != 200:
            # Nếu không tải được ảnh, trả về một ảnh placeholder 1x1
            img = Image.new('RGB', (1, 1), color='white')
            img_io = BytesIO()
            img.save(img_io, 'PNG')
            img_io.seek(0)
            print(f"Error: Could not download image from {image_url} for order {order_id}")
        else:
            img_io = BytesIO(response.content)

        # Cập nhật trạng thái read_at trong mail_tracking
        tracking = mongo.db.mail_tracking.find_one({"order_id": order_id})
        if tracking and not tracking.get('read_at'):
            result = mongo.db.mail_tracking.update_one(
                {"order_id": order_id},
                {"$set": {"read_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')}}
            )
            if result.modified_count > 0:
                print(f"Order {order_id} email marked as read via tracking image at {datetime.now()}")

        # Trả về hình ảnh
        return send_file(img_io, mimetype='image/webp')

    except Exception as e:
        print(f"Error in tracking_image for order {order_id}: {str(e)}")
        # Trả về ảnh placeholder nếu có lỗi
        img = Image.new('RGB', (1, 1), color='white')
        img_io = BytesIO()
        img.save(img_io, 'PNG')
        img_io.seek(0)
        return send_file(img_io, mimetype='image/png')
