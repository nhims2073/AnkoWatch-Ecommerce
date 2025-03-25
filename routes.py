import json
from bson import ObjectId
from flask import render_template, request, make_response, flash, redirect, url_for, session
from flask_jwt_extended import get_jwt_identity, jwt_required
from services.cart import add_to_cart, remove_cart, update_cart
from services.cart.cart import cart_exc
from services.cart.cart_count import cart_count_exc
from services.middleware import role_required
from app import app, mongo
from services.auth.register_exc import register_exc
from services.auth.login_exc import login_exc
from flask_login import login_required, logout_user

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

@app.route('/product/<product_id>')  # Không ép kiểu int
def product_detail(product_id):
    try:
        product = mongo.db.products.find_one({"_id": ObjectId(product_id)})
        if product:
            product['_id'] = str(product['_id'])  # Chuyển ObjectId thành string để dùng trong template
            return render_template("product_detail.html", product=product)
        else:
            return "Sản phẩm không tồn tại", 404
    except:
        return "Lỗi truy vấn sản phẩm", 500

@app.route('/cart-count', methods=['GET'])
@jwt_required()
def cart_count():
    return cart_count_exc()

@app.route('/account')
@jwt_required()
def account():
    return render_template('account/account.html')

@app.route('/orders')
@jwt_required()
def orders():
    try:
        user_id = get_jwt_identity()  # user_id là chuỗi

        orders = list(mongo.db.orders.find({"user_id": ObjectId(user_id)}))
        for order in orders:
            order['_id'] = str(order['_id'])
            order['user_id'] = str(order['user_id'])
        return render_template('account/list-orders.html', orders=orders)
    except Exception as e:
        flash(f"Đã xảy ra lỗi khi tải danh sách đơn hàng: {str(e)}", "danger")
        return render_template('account/list-orders.html', orders=[])

@app.route('/favourites')
@jwt_required()
def favourites():
    try:
        current_user = get_jwt_identity()
        user_id = current_user['user_id']

        favorites = list(mongo.db.favorites.find({"user_id": ObjectId(user_id)}))
        product_ids = [item['product_id'] for item in favorites]
        valid_product_ids = [ObjectId(pid) for pid in product_ids if ObjectId.is_valid(pid)]
        products = list(mongo.db.products.find({"_id": {"$in": valid_product_ids}}))
        for product in products:
            product['_id'] = str(product['_id'])
        return render_template('account/favorites.html', products=products)
    except Exception as e:
        flash(f"Đã xảy ra lỗi khi tải danh sách sản phẩm yêu thích: {str(e)}", "danger")
        return render_template('account/favorites.html', products=[])

@app.route('/address')
@jwt_required()
def address():
    try:
        current_user = get_jwt_identity()
        user_id = current_user['user_id']

        addresses = list(mongo.db.addresses.find({"user_id": ObjectId(user_id)}))
        for address in addresses:
            address['_id'] = str(address['_id'])
            address['user_id'] = str(address['user_id'])
        return render_template('account/address.html', addresses=addresses)
    except Exception as e:
        flash(f"Đã xảy ra lỗi khi tải danh sách địa chỉ: {str(e)}", "danger")
        return render_template('account/address.html', addresses=[])

@app.route('/change-password')
@jwt_required()
def change_password():
    return render_template('account/change-password.html')
    
@app.route('/payments')
def payments():
    return render_template('cart/payments.html')

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
    return render_template('product/search.html')

@app.route('/checkout')
def checkout():
    return render_template('cart/checkout.html')

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
    return render_template('admin/products.html')

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
        'clearToken': True
    })
    # Đăng xuất người dùng hiện tại nếu đang sử dụng Flask-Login
    try:
        logout_user()
    except Exception:
        pass
    
    # Xóa session
    session.clear()
    
    flash("Bạn đã đăng xuất thành công", "success")
    
    # Thêm script vào response
    return response