from flask import render_template, flash
from flask_jwt_extended import get_jwt_identity, get_jwt
from app import mongo
from bson import ObjectId
from datetime import datetime, timedelta

def cart_exc():
    try:
        user_id = get_jwt_identity()

        claims = get_jwt()
        discount_amount = claims.get('discount_amount', 0)

        cart = mongo.db.carts.find_one({"user_id": ObjectId(user_id)})

        if not cart or 'products' not in cart:
            cart_items = []
            subtotal = 0
            total_quantity = 0
        else:
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
            total_quantity = sum(item['quantity'] for item in cart['products'])
            for product in products_list:
                product['_id'] = str(product['_id'])
                for item in cart['products']:
                    if str(item['product_id']) == product['_id']:
                        product['quantity'] = item['quantity']
                        price = float(product['price']) if isinstance(product['price'], (str, int)) else product['price']
                        subtotal += price * item['quantity']
                        break
                cart_items.append(product)

        today = datetime.now().strftime('%d.%m.%Y')
        delivery_date = (datetime.now() + timedelta(days=2)).strftime('%d.%m.%Y')
        discount = float(discount_amount)
        total = subtotal - discount

        return render_template('cart/cart.html', cart_items=cart_items, today=today, delivery_date=delivery_date, subtotal=subtotal, total=total, total_quantity=total_quantity)

    except Exception as e:
        flash(f"Đã xảy ra lỗi khi tải giỏ hàng: {str(e)}", "danger")
        return render_template('cart/cart.html', cart_items=[], today=datetime.now().strftime('%d.%m.%Y'), delivery_date=(datetime.now() + timedelta(days=2)).strftime('%d.%m.%Y'), subtotal=0, total=0, total_quantity=0)