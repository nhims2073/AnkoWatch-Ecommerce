from flask import Flask, render_template

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


# Admin Routes
@app.route('/admin/dashboard')
def dashboard():
    return render_template('admin/dashboard.html')

if __name__ == '__main__':
    app.run(debug=True)