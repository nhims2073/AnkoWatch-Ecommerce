from app import mongo
from bson import ObjectId
from werkzeug.utils import secure_filename
import os
import cloudinary.uploader
from datetime import datetime

def get_all_products_exc():
    """
    Lấy tất cả sản phẩm, bao gồm thông tin danh mục, hãng, mô tả và cost_price.
    """
    products = mongo.db.products.find()
    product_list = []
    for product in products:
        product['_id'] = str(product['_id'])
        
        # Lấy thông tin danh mục (có thể có nhiều danh mục, nhưng hiện tại chỉ có một)
        category_names = []
        category_ids = product.get('category_ids', [])
        for cat_id in category_ids:
            try:
                category = mongo.db.categories.find_one({"_id": ObjectId(cat_id)})
                if category:
                    category_names.append(category['name'])
            except (ValueError, TypeError):
                continue
        product['category_names'] = category_names if category_names else ["Không xác định"]

        # Lấy thông tin hãng (chỉ một hãng)
        brand_name = "Không xác định"
        if 'brand_id' in product and product['brand_id']:
            try:
                brand = mongo.db.brands.find_one({"_id": ObjectId(product['brand_id'])})
                brand_name = brand['name'] if brand else "Không xác định"
            except (ValueError, TypeError):
                brand_name = "Không xác định"
        product['brand_name'] = brand_name

        # Lấy mô tả từ collection descriptions
        description_doc = mongo.db.descriptions.find_one({"product_id": product['_id']})
        if description_doc:
            product['description'] = description_doc['description']
        else:
            product['description'] = "No description available"
            # Optional: Log for debugging
            print(f"No description found for product_id: {product['_id']}")

        # Đảm bảo cost_price được lấy từ CSDL, nếu không có thì mặc định là 0
        product['cost_price'] = product.get('cost_price', 0)

        # Đảm bảo các trường mới (material, origin, technology, year) được lấy
        product['material'] = product.get('material', '')
        product['origin'] = product.get('origin', '')
        product['technology'] = product.get('technology', '')
        product['year'] = product.get('year', '')

        product_list.append(product)
    return product_list

def add_product_exc(data, file):
    """
    Thêm sản phẩm mới.
    """
    # Kiểm tra brand_id
    brand_id = data.get('brand_id')
    if not brand_id:
        return {"error": "Hãng là bắt buộc!"}
    try:
        brand_id = ObjectId(brand_id)
    except (ValueError, TypeError):
        return {"error": "Hãng không hợp lệ!"}

    # Kiểm tra xem brand_id có tồn tại không
    brand = mongo.db.brands.find_one({"_id": brand_id})
    if not brand:
        return {"error": "Hãng không tồn tại!"}

    # Lấy category_id (chỉ một danh mục)
    category_id = data.get('category_id')
    if not category_id:
        return {"error": "Phải chọn một danh mục!"}
    
    try:
        category_id_obj = ObjectId(category_id)
        category = mongo.db.categories.find_one({"_id": category_id_obj})
        if not category:
            return {"error": f"Danh mục {category_id} không tồn tại!"}
    except (ValueError, TypeError):
        return {"error": f"Danh mục {category_id} không hợp lệ!"}

    # Xử lý upload ảnh
    image_url = ""
    if file:
        upload_result = cloudinary.uploader.upload(file)
        image_url = upload_result['secure_url']
    else:
        image_url = "https://via.placeholder.com/150"

    # Lấy danh sách size (dạng mảng)
    sizes = data.getlist('size')
    if not sizes:
        return {"error": "Phải nhập ít nhất một kích thước!"}

    # Xử lý discount: nếu là chuỗi rỗng, gán giá trị mặc định là 0
    discount = data.get('discount', '0')
    try:
        discount_value = float(discount) if discount.strip() else 0.0
    except ValueError:
        return {"error": "Giá trị giảm giá không hợp lệ!"}

    # Lấy giá bán (price) và giá nhập (cost_price)
    try:
        price = float(data.get('price'))
        cost_price = float(data.get('cost_price'))
        if cost_price < 0 or price < 0:
            return {"error": "Giá nhập và giá bán phải lớn hơn hoặc bằng 0!"}
    except (ValueError, TypeError):
        return {"error": "Giá nhập hoặc giá bán không hợp lệ!"}

    # Tính giá sau khi giảm (discounted_price)
    discounted_price = price * (1 - discount_value / 100)

    # Lấy các trường mới
    material = data.get('material', '').strip()
    origin = data.get('origin', '').strip()
    technology = data.get('technology', '').strip()
    year = data.get('year', '')
    if year:
        try:
            year = int(year)
            if year < 1900 or year > 2099:
                return {"error": "Năm sản xuất phải nằm trong khoảng từ 1900 đến 2099!"}
        except ValueError:
            return {"error": "Năm sản xuất không hợp lệ!"}

    product = {
        "name": data.get('name'),
        "image": image_url,
        "quantity": int(data.get('quantity')),
        "price": price,
        "cost_price": cost_price,  # Lưu giá nhập
        "discount": discount_value,
        "discounted_price": discounted_price,  # Lưu giá sau giảm
        "size": sizes,
        "brand_id": brand_id,
        "category_ids": [category_id_obj],
        "material": material,  # Thêm trường chất liệu
        "origin": origin,  # Thêm trường xuất xứ
        "technology": technology,  # Thêm trường công nghệ
        "year": year if year else None,  # Thêm trường năm sản xuất, nếu không có thì để None
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    result = mongo.db.products.insert_one(product)

    # Lưu description vào collection descriptions
    description = data.get('description', '')
    mongo.db.descriptions.insert_one({
        "product_id": result.inserted_id,
        "description": description
    })

    return {"success": "Thêm sản phẩm thành công!", "product_id": str(result.inserted_id), "redirect": "/admin/products"}

def update_product_exc(product_id, data, file=None):
    """
    Cập nhật sản phẩm.
    """
    # Kiểm tra brand_id
    brand_id = data.get('brand_id')
    if not brand_id:
        return {"error": "Hãng là bắt buộc!"}
    try:
        brand_id = ObjectId(brand_id)
    except (ValueError, TypeError):
        return {"error": "Hãng không hợp lệ!"}

    # Kiểm tra xem brand_id có tồn tại không
    brand = mongo.db.brands.find_one({"_id": brand_id})
    if not brand:
        return {"error": "Hãng không tồn tại!"}

    # Lấy category_id (chỉ một danh mục)
    category_id = data.get('category_id')
    if not category_id:
        return {"error": "Phải chọn một danh mục!"}
    
    try:
        category_id_obj = ObjectId(category_id)
        category = mongo.db.categories.find_one({"_id": category_id_obj})
        if not category:
            return {"error": f"Danh mục {category_id} không tồn tại!"}
    except (ValueError, TypeError):
        return {"error": f"Danh mục {category_id} không hợp lệ!"}

    # Lấy danh sách size (dạng mảng)
    sizes = data.getlist('size')
    if not sizes:
        return {"error": "Phải nhập ít nhất một kích thước!"}

    # Xử lý discount: nếu là chuỗi rỗng, gán giá trị mặc định là 0
    discount = data.get('discount', '0')
    try:
        discount_value = float(discount) if discount.strip() else 0.0
    except ValueError:
        return {"error": "Giá trị giảm giá không hợp lệ!"}

    # Lấy giá bán (price) và giá nhập (cost_price)
    try:
        price = float(data.get('price'))
        cost_price = float(data.get('cost_price'))
        if cost_price < 0 or price < 0:
            return {"error": "Giá nhập và giá bán phải lớn hơn hoặc bằng 0!"}
    except (ValueError, TypeError):
        return {"error": "Giá nhập hoặc giá bán không hợp lệ!"}

    # Tính giá sau khi giảm (discounted_price)
    discounted_price = price * (1 - discount_value / 100)

    # Lấy các trường mới
    material = data.get('material', '').strip()
    origin = data.get('origin', '').strip()
    technology = data.get('technology', '').strip()
    year = data.get('year', '')
    if year:
        try:
            year = int(year)
            if year < 1900 or year > 2099:
                return {"error": "Năm sản xuất phải nằm trong khoảng từ 1900 đến 2099!"}
        except ValueError:
            return {"error": "Năm sản xuất không hợp lệ!"}

    update_data = {
        "name": data.get('name'),
        "quantity": int(data.get('quantity')),
        "price": price,
        "cost_price": cost_price,
        "discount": discount_value,
        "discounted_price": discounted_price,
        "size": sizes,  # This should correctly update the size field
        "brand_id": brand_id,
        "category_ids": [category_id_obj],
        "material": material,
        "origin": origin,
        "technology": technology,
        "year": year if year else None,
        "updated_at": datetime.utcnow()
    }

    # Nếu có file ảnh mới, upload và cập nhật
    if file:
        upload_result = cloudinary.uploader.upload(file)
        update_data['image'] = upload_result['secure_url']

    result = mongo.db.products.update_one(
        {"_id": ObjectId(product_id)},
        {"$set": update_data}
    )

    # Cập nhật description trong collection descriptions
    description = data.get('description', '')
    mongo.db.descriptions.update_one(
        {"product_id": ObjectId(product_id)},
        {"$set": {"description": description}},
        upsert=True  # Nếu không tồn tại, tạo mới
    )

    if result.modified_count > 0:
        return {"success": "Cập nhật sản phẩm thành công!"}
    return {"error": "Không tìm thấy sản phẩm hoặc không có thay đổi!"}

def delete_product_exc(product_id):
    """
    Xóa sản phẩm.
    """
    # Xóa description liên quan
    mongo.db.descriptions.delete_one({"product_id": ObjectId(product_id)})

    result = mongo.db.products.delete_one({"_id": ObjectId(product_id)})
    if result.deleted_count > 0:
        return {"success": "Xóa sản phẩm thành công!"}
    return {"error": "Không tìm thấy sản phẩm!"}

def get_all_categories_exc():
    """
    Lấy tất cả danh mục sản phẩm.
    """
    categories = mongo.db.categories.find()
    return [{"_id": str(category['_id']), "name": category['name']} for category in categories]

def add_category_exc(data):
    """
    Thêm danh mục sản phẩm.
    """
    category = {    
        "name": data.get('name'),
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    result = mongo.db.categories.insert_one(category)
    return {"success": "Thêm danh mục thành công!", "category_id": str(result.inserted_id)}

def update_category_exc(category_id, data):
    """
    Cập nhật danh mục sản phẩm.
    """
    result = mongo.db.categories.update_one(
        {"_id": ObjectId(category_id)},
        {"$set": {
            "name": data.get('name'),
            "updated_at": datetime.utcnow()
        }}
    )
    if result.modified_count > 0:
        return {"success": "Cập nhật danh mục thành công!"}
    return {"error": "Không tìm thấy danh mục hoặc không có thay đổi!"}

def delete_category_exc(category_id):
    """
    Xóa danh mục sản phẩm.
    """
    # Kiểm tra xem danh mục có đang được sử dụng bởi sản phẩm nào không
    product_count = mongo.db.products.count_documents({"category_ids": ObjectId(category_id)})
    if product_count > 0:
        return {"error": "Không thể xóa danh mục vì đang được sử dụng bởi sản phẩm!"}

    result = mongo.db.categories.delete_one({"_id": ObjectId(category_id)})
    if result.deleted_count > 0:
        return {"success": "Xóa danh mục thành công!"}
    return {"error": "Không tìm thấy danh mục!"}

def get_all_brands_exc():
    """
    Lấy tất cả hãng.
    """
    brands = mongo.db.brands.find()
    return [{"_id": str(brand['_id']), "name": brand['name']} for brand in brands]

def add_brand_exc(data):
    """
    Thêm hãng.
    """
    brand = {
        "name": data.get('name'),
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    result = mongo.db.brands.insert_one(brand)
    return {"success": "Thêm hãng thành công!", "brand_id": str(result.inserted_id), "redirect": "/admin/products"}

def update_brand_exc(brand_id, data):
    """
    Cập nhật hãng.
    """
    result = mongo.db.brands.update_one(
        {"_id": ObjectId(brand_id)},
        {"$set": {
            "name": data.get('name'),
            "updated_at": datetime.utcnow()
        }}
    )
    if result.modified_count > 0:
        return {"success": "Cập nhật hãng thành công!"}
    return {"error": "Không tìm thấy hãng hoặc không có thay đổi!"}

def delete_brand_exc(brand_id):
    """
    Xóa hãng.
    """
    # Kiểm tra xem hãng có đang được sử dụng bởi sản phẩm nào không
    product_count = mongo.db.products.count_documents({"brand_id": ObjectId(brand_id)})
    if product_count > 0:
        return {"error": "Không thể xóa hãng vì đang được sử dụng bởi sản phẩm!"}

    result = mongo.db.brands.delete_one({"_id": ObjectId(brand_id)})
    if result.deleted_count > 0:
        return {"success": "Xóa hãng thành công!"}
    return {"error": "Không tìm thấy hãng!"}