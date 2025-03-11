from flask import Flask, render_template, request, make_response, jsonify, flash, redirect, url_for, session
from services.middleware import role_required, cache_middleware
from werkzeug.security import check_password_hash
from flask_jwt_extended import create_access_token
from app import mongo, app
import json, os

app = Flask(__name__)

# User Routes
@app.route('/')
def home():
    return render_template('base.html')

@app.route('/login')
def login():
    return render_template('auth/login.html')

@app.route('/register')
def register():
    return render_template('auth/register.html')

@app.route('/forgot-password')
def forgot_password():
    return render_template('auth/forgot-password.html')

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    return render_template('product/product-detail.html', product_id=product_id)

@app.route('/info')
def info():
    return render_template('policy/info.html')

@app.route('/cart')
def cart():
    return render_template('cart/cart.html')

@app.route('/checkout')
def checkout():
    return render_template('cart/checkout.html')

@app.route('/policy')
def policy():
    return render_template('policy/policy.html')

# Admin Routes (Chỉ cho admin)
@app.route('/admin/dashboard')
def dashboard():
    return render_template('admin/dashboard.html')

@app.route('/admin/orders')
def orders():
    return render_template('admin/orders.html')

@app.route('/admin/products')
def products():
    return render_template('admin/products.html')

@app.route('/admin/customers')
def customers():
    return render_template('admin/customers.html')

@app.route('/admin/reports')
def reports():
    return render_template('admin/reports.html')

@app.route('/admin/integrations')
def integrations():
    return render_template('admin/integrations.html')
