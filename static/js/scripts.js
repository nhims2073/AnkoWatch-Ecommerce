function decreaseQuantity(button, productId) {
    let input = button.parentNode.querySelector('input[type=number]');
    if (input.value > 1) {
        fetch(`/cart/update_quantity/${productId}/decrease`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include'
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                // Làm mới trang để cập nhật toàn bộ giao diện
                window.location.reload();
            } else {
                Swal.fire({
                    icon: 'error',
                    title: 'Lỗi',
                    text: data.message || "Có lỗi xảy ra khi cập nhật số lượng!",
                });
            }
        })
        .catch(error => {
            console.error('Error:', error);
            Swal.fire({
                icon: 'error',
                title: 'Lỗi',
                text: "Có lỗi xảy ra khi cập nhật số lượng!",
            });
        });
    }
}

// Hàm tăng số lượng
function increaseQuantity(button, productId) {
    let input = button.parentNode.querySelector('input[type=number]');
    if (input.value < 99) {
        fetch(`/cart/update_quantity/${productId}/increase`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include'
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                // Làm mới trang để cập nhật toàn bộ giao diện
                window.location.reload();
            } else {
                Swal.fire({
                    icon: 'error',
                    title: 'Lỗi',
                    text: data.message || "Có lỗi xảy ra khi cập nhật số lượng!",
                });
            }
        })
        .catch(error => {
            console.error('Error:', error);
            Swal.fire({
                icon: 'error',
                title: 'Lỗi',
                text: "Có lỗi xảy ra khi cập nhật số lượng!",
            });
        });
    }
}

// Hàm xóa sản phẩm khỏi giỏ hàng
function removeFromCart(productId) {
    fetch(`/cart/remove/${productId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        credentials: 'include'
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            location.reload();
        } else {
            Swal.fire({
                icon: 'error',
                title: 'Lỗi',
                text: data.message || "Có lỗi xảy ra khi xóa sản phẩm!",
            });
        }
    })
    .catch(error => {
        console.error('Error:', error);
        Swal.fire({
            icon: 'error',
            title: 'Lỗi',
            text: "Có lỗi xảy ra khi xóa sản phẩm!",
        });
    });
}

// Get the button
const mybutton = document.getElementById("myBtn");

// Khi người dùng cuộn xuống 20px từ đầu trang, hiển thị nút
window.onscroll = function() { scrollFunction(); };

function scrollFunction() {
    if (document.body.scrollTop > 70 || document.documentElement.scrollTop > 70) {
        mybutton.style.display = "block";
    } else {
        mybutton.style.display = "none";
    }
}

// Khi người dùng nhấn nút, cuộn lên đầu trang
function topFunction() {
    document.body.scrollTop = 0;
    document.documentElement.scrollTop = 0;
}

function updateDropdown(buttonId, value) {
    document.getElementById(buttonId).innerText = value;
}

// Xử lý form đăng nhập
const loginForm = document.getElementById("login-form");
if (loginForm) {
    loginForm.addEventListener("submit", function(event) {
        event.preventDefault();

        const username = document.getElementById("username").value;
        const password = document.getElementById("password").value;

        fetch("/login", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                username: username,
                password: password
            })
        })
        .then(response => {
            if (response.status === 401) {
                return response.text().then(text => { throw new Error(text); });
            }
            if (response.redirected) {
                window.location.href = response.url;
            } else {
                return response.json();
            }
        })
        .then(data => {
            console.log("Response:", data);
        })
        .catch(error => {
            console.error("Error:", error);
            Swal.fire({
                icon: 'error',
                title: 'Lỗi',
                text: error.message,
            });
        });
    });
}

// Hàm thêm sản phẩm vào giỏ hàng
function addToCart(productId) {
    fetch(`/add_to_cart/${productId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        credentials: 'include'
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            Swal.fire({
                icon: 'success',
                title: 'Thành công!',
                text: data.message,
                timer: 1500,
                showConfirmButton: false
            });
            updateCartBadge();
            // Nếu đang ở trang giỏ hàng, làm mới giao diện giỏ hàng
            if (window.location.pathname === '/cart') {
                window.location.reload(); // Làm mới trang để cập nhật giỏ hàng
            }
        } else {
            Swal.fire({
                icon: 'error',
                title: 'Lỗi!',
                text: data.message,
                timer: 1500,
                showConfirmButton: false
            });
        }
    })
    .catch(error => {
        console.error('Error adding to cart:', error);
        Swal.fire({
            icon: 'error',
            title: 'Lỗi!',
            text: 'Đã có lỗi xảy ra: ' + error.message,
            timer: 1500,
            showConfirmButton: false
        });
    });
}

// Hàm cập nhật số lượng badge
function updateCartBadge() {
    fetch('/cart-count', {
        method: 'GET',
        credentials: 'include'
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        const badge = document.getElementById('cart-badge');
        if (badge) {
            badge.textContent = data.count > 0 ? data.count : '';
        }
    })
    .catch(error => {
        console.error('Error fetching cart count:', error);
        const badge = document.getElementById('cart-badge');
        if (badge) badge.textContent = '';
    });
}


// Lắng nghe sự kiện HX-Trigger từ backend
document.addEventListener('updateCartBadge', function() {
    updateCartBadge();
});

// Hàm xóa sản phẩm khỏi danh sách yêu thích
function removeFromFavorite(productId) {
    if (confirm("Bạn có chắc chắn muốn xóa sản phẩm này khỏi danh sách yêu thích?")) {
        fetch(`/remove-favorite/${productId}`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            credentials: 'include'
        })
        .then(response => {
            if (!response.ok) {
                throw new Error("Không thể xóa sản phẩm khỏi danh sách yêu thích");
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                const favoriteItem = document.querySelector(`.favorite-item[data-product-id="${productId}"]`);
                if (favoriteItem) {
                    favoriteItem.remove();
                }
                
                Swal.fire({
                    icon: 'success',
                    title: 'Thành công',
                    text: "Đã xóa sản phẩm khỏi danh sách yêu thích",
                    timer: 1500,
                    showConfirmButton: false
                });
                
                const remainingItems = document.querySelectorAll('.favorite-item');
                if (remainingItems.length === 0) {
                    const favoriteContainer = document.querySelector('#favorite-items-container');
                    if (favoriteContainer) {
                        favoriteContainer.innerHTML = '<p class="text-center">Bạn chưa có sản phẩm yêu thích nào.</p>';
                    }
                }
            } else {
                Swal.fire({
                    icon: 'error',
                    title: 'Lỗi',
                    text: data.message || "Có lỗi xảy ra khi xóa sản phẩm khỏi danh sách yêu thích",
                });
            }
        })
        .catch(error => {
            console.error("Lỗi:", error);
            Swal.fire({
                icon: 'error',
                title: 'Lỗi',
                text: "Đã xảy ra lỗi khi xóa sản phẩm khỏi danh sách yêu thích",
            });
        });
    }
}

function showAlert(type, title, message) {
    Swal.fire({
        icon: type,
        title: title,
        text: message,
        confirmButtonText: 'OK',
        timer: 3000,
        showConfirmButton: '#28a745'
    });
}

function confirmDelete() {
    document.querySelectorAll('.btn-outline-danger').forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const form = this.closest('form');
            
            Swal.fire({
                title: "Bạn có chắc chắn?",
                text: "Bạn sẽ không thể hoàn tác hành động này!",
                icon: "warning",
                showCancelButton: true,
                confirmButtonColor: "#3085d6",
                cancelButtonColor: "#d33",
                confirmButtonText: "Xoá",
                cancelButtonText: "Hủy"
            }).then((result) => {
                if (result.isConfirmed) {
                    form.submit();
                }
            });
        });
    });
}

// Kiểm tra và hiển thị thông báo khi trang được tải
document.addEventListener('DOMContentLoaded', function() {
    updateCartBadge();
    confirmDelete();

    console.log('successMessage:', successMessage);
    console.log('errorMessage:', errorMessage);

    if (successMessage && typeof successMessage === 'string' && successMessage.trim() !== '') {
        Swal.fire({
            icon: 'success',
            title: 'Thành công!',
            text: successMessage,
            timer: 1500,
            showConfirmButton: false
        });
    }

    if (errorMessage && typeof errorMessage === 'string' && errorMessage.trim() !== '') {
        Swal.fire({
            icon: 'error',
            title: 'Lỗi!',
            text: errorMessage,
            timer: 1500,
            showConfirmButton: false
        });
    }
});

function addToFavourites(product_id) {
    fetch(`/add_to_favourites/${product_id}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        }
    })
    .then(response => response.json())
    .then(data => {
        Swal.fire({
            icon: 'success',
            title: 'Đã thêm vào danh sách yêu thích!',
            text: data.success,
            timer: 1500,
            showConfirmButton: false
        });
    })
    .catch(err => {
        console.error(err);
        Swal.fire({
            icon: 'error',
            title: 'Oops...',
            text: 'Có lỗi xảy ra, thử lại sau nha!',
        });
    });
}