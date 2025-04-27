document.addEventListener('htmx:afterOnLoad', function(event) {
    // Kiểm tra response headers cho HX-Trigger
    const triggerHeader = event.detail.xhr.getResponseHeader('HX-Trigger');
    if (triggerHeader) {
        const triggers = JSON.parse(triggerHeader);
        if (triggers.tokenExpired) {
            // Chuyển hướng đến trang logout sau 1 giây
            setTimeout(() => {
                window.location.href = '/logout';
            }, 1000);
        }
    }
});

// Xử lý lỗi 401 từ API
document.addEventListener('htmx:responseError', function(event) {
    if (event.detail.xhr.status === 401) {
        try {
            const response = JSON.parse(event.detail.xhr.responseText);
            if (response.code === 'token_expired') {
                window.location.href = '/logout';
            }
        } catch (e) {
            console.error('Error parsing response:', e);
        }
    }
});

// Kiểm tra token expiration định kỳ
function checkTokenExpiration() {
    const token = document.cookie
        .split('; ')
        .find(row => row.startsWith('access_token_cookie='));
    
    if (token) {
        try {
            const tokenParts = token.split('=')[1];
            const payload = JSON.parse(atob(tokenParts.split('.')[1]));
            const expirationTime = payload.exp * 1000; // Convert to milliseconds
            const currentTime = Date.now();
            const timeUntilExpiration = expirationTime - currentTime;

            if (timeUntilExpiration <= 0) {
                window.location.href = '/logout';
            } else {
                // Kiểm tra lại trước khi token hết hạn
                setTimeout(checkTokenExpiration, Math.min(timeUntilExpiration, 60000)); // Check every minute or before expiration
            }
        } catch (e) {
            console.error('Error checking token expiration:', e);
        }
    }
}

// Start checking token expiration
document.addEventListener('DOMContentLoaded', checkTokenExpiration);