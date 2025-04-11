import json
from bson import ObjectId
from flask import jsonify, render_template, request, make_response, flash, redirect, url_for, session
from flask_jwt_extended import  get_jwt_identity, jwt_required
from services.account import change_password_exc
from services.account.account_exc import get_user_info, update_user_info
from services.account.address_exc import add_address_exc, delete_address_exc, get_addresses_exc, update_address_exc
from services.account.favourites_exc import add_to_favourites_exc, get_favorite_products_exc, remove_from_favorites_exc
from services.account.orders_exc import get_orders
from services.admin.product_exc import add_brand_exc, add_category_exc, add_product_exc, delete_brand_exc, delete_category_exc, delete_product_exc, get_all_brands_exc, get_all_categories_exc, get_all_products_exc, update_brand_exc, update_category_exc, update_product_exc
from services.admin.report_exc import get_revenue_report
from services.admin.vouchers_exc import add_voucher_exc, delete_voucher_exc, get_all_vouchers, get_voucher_details, update_voucher_exc
from services.cart import add_to_cart, remove_cart, update_cart
from services.cart.cart import cart_exc
from services.cart.cart_count import cart_count_exc
from services.cart.payment_exc import payment_return, process_payment
from services.middleware import role_required
from app import app, mongo
from services.auth.register_exc import register_exc
from services.auth.login_exc import login_exc
from flask_login import logout_user
from services.policy.news_exc import get_all_news, get_news_detail
from services.product.product_detail_exc import product_detail_exc
from services.product.search_exc import search_exc
from services.cart.checkout import apply_voucher_exc, checkout_exc, invoice_detail_exc
from services.admin.customer_exc import get_all_customers_exc, update_customer_role_exc, get_all_roles_exc, add_role_exc
from services.admin.dashboard_exc import get_dashboard_stats
from services.admin.orders_exc import get_all_orders, get_orders_by_status, get_order_details


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
        product['price'] = float(product.get('price', 0))  # Đảm bảo price là số, mặc định là 0 nếu không có
        product['discount'] = float(product.get('discount', 0))  # Đảm bảo discount là số
        product['discounted_price'] = float(product.get('discounted_price', product['price']))  # Đảm bảo discounted_price là số

    # Lấy danh sách sản phẩm khuyến mãi từ collection products (chỉ lấy các sản phẩm có discount > 0)
    sale_products = list(mongo.db.products.find(
        {"discount": {"$exists": True, "$gt": 0}},
        {"_id": 1, "name": 1, "brand_id": 1, "image": 1, "price": 1, "discount": 1, "discounted_price": 1}
    ).sort("_id", -1).limit(8))
    
    # Duyệt qua từng sản phẩm khuyến mãi để lấy tên thương hiệu và tính toán giá
    for product in sale_products:
        product['_id'] = str(product['_id'])
        # Truy vấn collection brands để lấy tên thương hiệu
        if 'brand_id' in product and product['brand_id']:
            brand = mongo.db.brands.find_one({"_id": ObjectId(product['brand_id'])}, {"name": 1})
            product['brand'] = brand['name'] if brand else "Không xác định"
        else:
            product['brand'] = "Không xác định"
        # Đảm bảo price, discount và discounted_price có giá trị hợp lệ
        product['price'] = float(product.get('price', 0))  # Đảm bảo price là số
        product['discount'] = float(product.get('discount', 0))  # Đảm bảo discount là số
        product['discounted_price'] = float(product.get('discounted_price', product['price']))  # Đảm bảo discounted_price là số
        # Gán discount_percent để hiển thị phần trăm giảm giá
        product['discount_percent'] = int(product['discount'])

    # Kiểm tra xem người dùng đã đăng nhập chưa trước khi render template
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
@jwt_required()
def orders():
    if not session.get("user_id"):
        return redirect(url_for('auth.login'))

    orders = get_orders()  # Hàm này đã xử lý ObjectId chuyển thành chuỗi
    if not orders:
        flash("Không có đơn hàng nào", "danger")
        orders = []  # Đảm bảo orders là một danh sách trống nếu không có đơn hàng
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
    
    # Đảm bảo success_message và error_message là chuỗi rỗng nếu None
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
    
# @app.route('/payments', methods=['GET', 'POST'])
# @jwt_required()
# def payments_route():
#     from services.cart.payment_exc import process_payment
#     return process_payment()

@app.route('/payment_return', methods=['GET'])
@jwt_required()
def payment_return_route():
    return payment_return()

@app.route('/cart/order-complete')
@jwt_required()
def order_complete():
    # Lấy user_id từ JWT
    user_id = get_jwt_identity()
    if not user_id:
        return redirect(url_for('login'))

    # Lấy thông tin đơn hàng từ session (nếu có)
    order = session.get('pending_order')
    if not order:
        # Nếu không có trong session, thử lấy đơn hàng gần nhất của người dùng từ database
        order = mongo.db.orders.find_one(
            {"user_id": ObjectId(user_id)},
            sort=[("order_date", -1)]  # Sắp xếp theo ngày đặt hàng, lấy đơn hàng mới nhất
        )
        if not order:
            flash("Không tìm thấy đơn hàng.", "danger")
            return redirect(url_for('orders'))

    # Chuyển đổi ObjectId thành string nếu lấy từ database
    if '_id' in order:
        order['_id'] = str(order['_id'])
        order['user_id'] = str(order['user_id'])

    return render_template('cart/order-complete.html', order=order)

@app.route('/invoice/<order_id>')
@jwt_required()
def invoice_detail(order_id):
    return invoice_detail_exc(order_id)

#Error Routes
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
def search():
    product_list, category_mapping, message = search_exc()
    # Lấy các tham số để hiển thị lại trên giao diện
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

@app.route('/policy')
def policy():
    return render_template('policy/policy.html')

# Admin Routes
@app.route('/admin/dashboard')
@jwt_required()
@role_required('admin')
def dashboard():
    return get_dashboard_stats()    

@app.route('/admin/orders')
@jwt_required()
@role_required('admin')
def admin_orders():
    # Lấy tất cả đơn hàng
    all_orders = get_all_orders()
    for order in all_orders:
        # Chuyển ObjectId thành chuỗi
        order['_id'] = str(order['_id'])
        # Đảm bảo trường items là danh sách
        order['items'] = order.get('items', [])
        # Đảm bảo các trường khác
        order['customer_name'] = order.get('customer_name', order.get('receiver_name', 'Không xác định'))
        order['status'] = order.get('status', order.get('delivery_status', 'Không xác định'))

    # Lấy các đơn hàng theo trạng thái
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
@role_required('admin')
def admin_order_details(order_id):
    try:
        # Lấy chi tiết đơn hàng từ database
        order = get_order_details(order_id)
        if order:
            # Chuyển ObjectId thành chuỗi để trả về JSON
            order['_id'] = str(order['_id'])
            
            # Đảm bảo các trường cần thiết cho JavaScript
            order['order_id'] = order['_id']
            
            # Đảm bảo các trường khác tồn tại, nếu không thì gán giá trị mặc định
            order['receiver_name'] = order.get('receiver_name', 'Không xác định')
            order['delivery_status'] = order.get('delivery_status', order.get('status', 'Không xác định'))
            order['receiver_address'] = order.get('receiver_address', 'Không xác định')
            order['payment_method'] = order.get('payment_method', 'Không xác định')
            order['items'] = order.get('items', [])

            # Tính toán total_amount dựa trên items
            total_amount = 0
            for item in order['items']:
                quantity = item.get('quantity', 0)
                price = item.get('price', 0)
                total_amount += quantity * price
            order['total_amount'] = total_amount

            # Định dạng lại items nếu cần
            for item in order['items']:
                item['name'] = item.get('name', 'Không xác định')
                item['quantity'] = item.get('quantity', 0)
                item['price'] = item.get('price', 0)

            return jsonify(order)
        else:
            return jsonify({"error": "Order not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/admin/update_order_status/<order_id>', methods=['POST'])
@jwt_required()
@role_required('admin')
def update_order_status(order_id):
    try:
        data = request.get_json()
        new_status = data.get('status')

        # Debug: In giá trị new_status
        print(f"Received status: {new_status}")

        if not new_status:
            return jsonify({"error": "Trạng thái không được cung cấp"}), 400

        # Danh sách trạng thái hợp lệ, khớp với database và dropdown
        valid_statuses = ["pending", "waiting_for_shipping", "waiting_for_delivery", 
                         "completed", "cancelled", "returned"]
        
        if new_status not in valid_statuses:
            print(f"Invalid status: {new_status} not in {valid_statuses}")
            return jsonify({"error": "Trạng thái không hợp lệ"}), 400

        # Cập nhật trạng thái trong database
        result = mongo.db.orders.update_one(
            {"_id": ObjectId(order_id)},
            {"$set": {"delivery_status": new_status}}
        )

        if result.modified_count > 0:
            return jsonify({"success": True})
        else:
            return jsonify({"error": "Không tìm thấy đơn hàng hoặc không có thay đổi"}), 404

    except Exception as e:
        print(f"Error in update_order_status: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/admin/products')
@jwt_required()
@role_required('admin')
def products():
    products = get_all_products_exc()
    categories = get_all_categories_exc()
    brands = get_all_brands_exc()
    return render_template('admin/products.html', products=products, categories=categories, brands=brands)

@app.route('/admin/add_product', methods=['POST'])
@role_required("admin")
def admin_add_product():
    data = request.form
    file = request.files.get('image')
    result = add_product_exc(data, file)
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
@role_required("admin")
def admin_update_product(product_id):
    data = request.form
    file = request.files.get('image')
    result = update_product_exc(product_id, data, file)
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
@role_required("admin")
def admin_delete_product(product_id):
    result = delete_product_exc(product_id)
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
@role_required("admin")
def admin_add_category():
    data = request.form
    result = add_category_exc(data)
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
@role_required("admin")
def admin_update_category(category_id):
    data = request.form
    result = update_category_exc(category_id, data)
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
@role_required("admin")
def admin_delete_category(category_id):
    result = delete_category_exc(category_id)
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
@role_required("admin")
def admin_add_brand():
    data = request.form
    result = add_brand_exc(data)
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
@role_required("admin")
def admin_update_brand(brand_id):
    data = request.form
    result = update_brand_exc(brand_id, data)
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
@role_required("admin")
def admin_delete_brand(brand_id):
    result = delete_brand_exc(brand_id)
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
@role_required('admin')
def customers():
    customers = get_all_customers_exc()
    roles = get_all_roles_exc()
    return render_template('admin/customers.html', customers=customers, roles=roles)

@app.route('/admin/update_customer_role/<user_id>', methods=['POST'])
@role_required("admin")
def admin_update_customer_role(user_id):
    data = request.form
    result = update_customer_role_exc(user_id, data)
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
@role_required("admin")
def admin_add_role():
    data = request.form
    result = add_role_exc(data)
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

@app.route('/admin/reports', methods=['GET', 'POST'])
@jwt_required()
@role_required('admin')
def reports():
    time_frame = request.args.get('time_frame', 'month')
    if time_frame not in ['week', 'month', 'quarter', 'year']:
        time_frame = 'month'

    report_data = get_revenue_report(time_frame)
    print("report_data:", report_data)  # Debug
    return render_template('admin/reports.html', report_data=report_data)

@app.route('/admin/vouchers', methods=['GET'])
@jwt_required()
@role_required('admin')
def vouchers():
    search_query = request.args.get('search', '')
    vouchers = get_all_vouchers(search_query)
    if request.headers.get('Content-Type') == 'application/json':
        return jsonify(vouchers)
    return render_template('admin/vouchers.html', vouchers=vouchers)

@app.route('/admin/voucher/<voucher_id>', methods=['GET'])
@jwt_required()
@role_required('admin')
def voucher_details(voucher_id):
    voucher = get_voucher_details(voucher_id)
    if voucher:
        return jsonify(voucher)
    return jsonify({"error": "Voucher not found"}), 404

@app.route('/admin/add_voucher', methods=['POST'])
@jwt_required()
@role_required('admin')
def admin_add_voucher():
    return add_voucher_exc()

@app.route('/admin/update_voucher', methods=['POST'])
@jwt_required()
@role_required('admin')
def admin_update_voucher():
    return update_voucher_exc()

@app.route('/admin/delete_voucher/<voucher_id>', methods=['POST'])
@jwt_required()
@role_required('admin')
def admin_delete_voucher(voucher_id):
    return delete_voucher_exc(voucher_id)

@app.route("/logout")
def logout():
    # Xóa token JWT
    response = make_response(redirect(url_for('home')))
    response.set_cookie('access_token_cookie', '', expires=0)  # Xóa cookie JWT
    response.set_cookie('access_token', '', expires=0)  # Xóa cookie access_token nếu có
    
    # Thêm script để xóa token từ localStorage
    response.headers['HX-Trigger'] = json.dumps({
        'clearToken': True,
        'showSuccessAlert': {
            'title': 'Thành công!',
            'message': 'Bạn đã đăng xuất thành công'
        }
    })

    # Đăng xuất người dùng hiện tại nếu đang sử dụng Flask-Login
    try:
        logout_user()
    except Exception:
        pass
    
    # Xóa session
    session.clear()    
    return response

