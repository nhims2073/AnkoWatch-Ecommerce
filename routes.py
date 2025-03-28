import json
from bson import ObjectId
from flask import render_template, request, make_response, flash, redirect, url_for, session
from flask_jwt_extended import  get_jwt_identity, jwt_required
from services.account import change_password_exc
from services.account.account_exc import get_user_info, update_user_info
from services.account.address_exc import add_address_exc, delete_address_exc, get_addresses_exc, update_address_exc
from services.account.favourites_exc import get_favorite_products_exc, remove_from_favorites_exc
from services.account.orders_exc import get_orders
from services.admin.product_exc import add_brand_exc, add_category_exc, add_product_exc, delete_brand_exc, delete_category_exc, delete_product_exc, get_all_brands_exc, get_all_categories_exc, get_all_products_exc, update_brand_exc, update_category_exc, update_product_exc
from services.cart import add_to_cart, remove_cart, update_cart
from services.cart.cart import cart_exc
from services.cart.cart_count import cart_count_exc
from services.middleware import role_required
from app import app, mongo
from services.auth.register_exc import register_exc
from services.auth.login_exc import login_exc
from flask_login import logout_user
from services.product.product_detail_exc import product_detail_exc
from services.product.search_exc import search_exc
from services.cart.checkout import checkout_exc, payments_exc, invoice_detail_exc

# User Routes
@app.route('/')
def home():
    # Lấy danh sách sản phẩm bán chạy
    products = list(mongo.db.products.find({}, {"_id": 1, "name": 1, "brand": 1, "image": 1, "price": 1})
                    .sort("_id", -1) 
                    .limit(8))
    for product in products:
        product['_id'] = str(product['_id'])

    # Lấy danh sách sản phẩm khuyến mãi
    sale_products = list(mongo.db.products.find({"discount_percent": {"$exists": True, "$gt": 0}}, 
                                                {"_id": 1, "name": 1, "brand": 1, "image": 1, "price": 1, "discount_percent": 1})
                        .sort("_id", -1)
                        .limit(8))
    for product in sale_products:
        product['_id'] = str(product['_id'])
        product['original_price'] = product['price']
        product['discounted_price'] = product['price'] * (1 - product['discount_percent'] / 100)

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

    orders = get_orders()
    return render_template('account/list-orders.html', current_user=get_user_info(), orders=orders)

@app.route('/favourites', methods=['GET', 'POST'])
@jwt_required()
def favourites():
    if not session.get("user_id"):
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        product_id = request.form.get("product_id")
        result = remove_from_favorites_exc(product_id)
        # Sau khi xóa, tải lại danh sách sản phẩm yêu thích
        favorite_products = get_favorite_products_exc()
        return render_template('account/favourites.html', current_user=get_user_info(), favorite_products=favorite_products, **result)

    favorite_products = get_favorite_products_exc()
    return render_template('account/favourites.html', current_user=get_user_info(), favorite_products=favorite_products)

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
    
@app.route('/payments')
@jwt_required()
def payments_route():
    return payments_exc()

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
    return render_template('policy/news.html')

@app.route('/news-detail')
def news_detail():
    return render_template('policy/news-detail.html')

@app.route('/cart')
@jwt_required()
def cart():
    return cart_exc()
    
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
    products = search_exc()
    # Lấy các tham số để hiển thị lại trên giao diện
    query = request.args.get('q', '')
    category = request.args.get('category', '')
    sort = request.args.get('sort', 'relevance')
    brands = request.args.getlist('brand')
    price_ranges = request.args.getlist('price_range')

    return render_template('product/search.html', 
                          products=products, 
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
    return render_template('admin/dashboard.html')

@app.route('/admin/orders')
@jwt_required()
@role_required('admin')
def admin_orders():
    return render_template('admin/orders.html')

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
    if "success" in result:
        flash(result["success"], "success")
    else:
        flash(result.get("error", "Có lỗi xảy ra!"), "danger")
    return redirect(url_for('admin_products'))

@app.route('/admin/update_product/<product_id>', methods=['POST'])
@role_required("admin")
def admin_update_product(product_id):
    data = request.form
    file = request.files.get('image')
    result = update_product_exc(product_id, data, file)
    if "success" in result:
        flash(result["success"], "success")
    else:
        flash(result.get("error", "Có lỗi xảy ra!"), "danger")
    return redirect(url_for('admin_products'))

@app.route('/admin/delete_product/<product_id>', methods=['POST'])
@role_required("admin")
def admin_delete_product(product_id):
    result = delete_product_exc(product_id)
    if "success" in result:
        flash(result["success"], "success")
    else:
        flash(result.get("error", "Có lỗi xảy ra!"), "danger")
    return redirect(url_for('admin_products'))

@app.route('/admin/add_category', methods=['POST'])
@role_required("admin")
def admin_add_category():
    data = request.form
    result = add_category_exc(data)
    if "success" in result:
        flash(result["success"], "success")
    else:
        flash(result.get("error", "Có lỗi xảy ra!"), "danger")
    return redirect(url_for('admin_products'))

@app.route('/admin/update_category/<category_id>', methods=['POST'])
@role_required("admin")
def admin_update_category(category_id):
    data = request.form
    result = update_category_exc(category_id, data)
    if "success" in result:
        flash(result["success"], "success")
    else:
        flash(result.get("error", "Có lỗi xảy ra!"), "danger")
    return redirect(url_for('admin_products'))

@app.route('/admin/delete_category/<category_id>', methods=['POST'])
@role_required("admin")
def admin_delete_category(category_id):
    result = delete_category_exc(category_id)
    if "success" in result:
        flash(result["success"], "success")
    else:
        flash(result.get("error", "Có lỗi xảy ra!"), "danger")
    return redirect(url_for('admin_products'))

@app.route('/admin/add_brand', methods=['POST'])
@role_required("admin")
def admin_add_brand():
    data = request.form
    result = add_brand_exc(data)
    if "success" in result:
        flash(result["success"], "success")
    else:
        flash(result.get("error", "Có lỗi xảy ra!"), "danger")
    return redirect(url_for('admin_products'))

@app.route('/admin/update_brand/<brand_id>', methods=['POST'])
@role_required("admin")
def admin_update_brand(brand_id):
    data = request.form
    result = update_brand_exc(brand_id, data)
    if "success" in result:
        flash(result["success"], "success")
    else:
        flash(result.get("error", "Có lỗi xảy ra!"), "danger")
    return redirect(url_for('admin_products'))

@app.route('/admin/delete_brand/<brand_id>', methods=['POST'])
@role_required("admin")
def admin_delete_brand(brand_id):
    result = delete_brand_exc(brand_id)
    if "success" in result:
        flash(result["success"], "success")
    else:
        flash(result.get("error", "Có lỗi xảy ra!"), "danger")
    return redirect(url_for('admin_products'))

@app.route('/admin/customers')
@jwt_required()
@role_required('admin')
def customers():
    return render_template('admin/customers.html')

@app.route('/admin/reports')
@jwt_required()
@role_required('admin')
def reports():
    return render_template('admin/reports.html')

@app.route('/admin/integrations')
@jwt_required()
@role_required('admin')
def integrations():
    return render_template('admin/integrations.html')

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


@app.route('/cart/payment-status')
def payment_status():
    return render_template('cart/payment-status.html')