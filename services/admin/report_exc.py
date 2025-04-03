from services.admin.orders_exc import get_orders_report

def get_revenue_report(time_frame='month'):
    """
    Tạo báo cáo doanh thu dựa trên khung thời gian: week, month, quarter, year.
    """
    try:
        report_data = get_orders_report(time_frame)
        return report_data
    except Exception as e:
        print(f"Error in get_revenue_report: {str(e)}")
        # Trả về dữ liệu mặc định nếu có lỗi
        return {
            'time_frame': time_frame,
            'total_orders': 0,
            'total_revenue': 0,
            'status_chart': {
                'labels': ['Thành công', 'Hủy bỏ', 'Hoàn hàng', 'Khác'],
                'data': [0, 0, 0, 0],
                'percentages': [0, 0, 0, 0]
            },
            'revenue_chart': {
                'labels': [],
                'data': []
            },
            'start_date': '',
            'end_date': ''
        }