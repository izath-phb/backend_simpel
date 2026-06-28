from flask import Blueprint, jsonify
from src.models import BigDataLog, User, Report, Project, BmkgData, NewsData, WeatherData
import datetime

bigdata_bp = Blueprint('bigdata', __name__)

@bigdata_bp.route('/stats', methods=['GET'])
def get_bigdata_stats():
    try:
        # Get latest aggregated log
        latest_log = BigDataLog.objects.order_by('-timestamp').first()
        
        # Or calculate realtime if not exist
        if not latest_log:
            latest_log = {
                'total_users': User.objects.count(),
                'total_reports': Report.objects.count(),
                'total_projects': Project.objects.count(),
                'total_bmkg': BmkgData.objects.count(),
                'total_news': NewsData.objects.count(),
                'total_weather': WeatherData.objects.count()
            }
            
        # Get historical data for the line chart (last 24 hours / days)
        logs = BigDataLog.objects.order_by('-timestamp').limit(24)
        historical_data = []
        for log in reversed(list(logs)):
            historical_data.append({
                'time': log.timestamp.strftime('%H:%M') if isinstance(log.timestamp, datetime.datetime) else 'N/A',
                'volume': log.total_users + log.total_reports + log.total_bmkg + log.total_news + log.total_weather,
                'bmkg': log.total_bmkg,
                'news': log.total_news,
                'weather': log.total_weather
            })
            
        # Add dummy data if history is empty to make chart visible
        if not historical_data:
            historical_data = [
                {'time': '08:00', 'volume': 150, 'bmkg': 20, 'news': 50, 'weather': 10},
                {'time': '09:00', 'volume': 200, 'bmkg': 25, 'news': 55, 'weather': 12},
                {'time': '10:00', 'volume': 180, 'bmkg': 30, 'news': 60, 'weather': 15},
                {'time': '11:00', 'volume': 220, 'bmkg': 35, 'news': 65, 'weather': 20},
                {'time': '12:00', 'volume': 250, 'bmkg': 40, 'news': 70, 'weather': 25},
            ]

        # Calculate proportions for Pie Chart (Capstore vs External)
        total_capstore = latest_log.total_users + latest_log.total_reports + latest_log.total_projects if isinstance(latest_log, BigDataLog) else latest_log['total_users'] + latest_log['total_reports'] + latest_log['total_projects']
        total_external = latest_log.total_bmkg + latest_log.total_news + latest_log.total_weather if isinstance(latest_log, BigDataLog) else latest_log['total_bmkg'] + latest_log['total_news'] + latest_log['total_weather']

        # Format stats for response
        stats = {
            'overview': {
                'total_capstore': total_capstore,
                'total_external': total_external,
                'total_combined': total_capstore + total_external
            },
            'bar_chart': [
                {'name': 'Users', 'value': latest_log.total_users if isinstance(latest_log, BigDataLog) else latest_log['total_users']},
                {'name': 'Reports', 'value': latest_log.total_reports if isinstance(latest_log, BigDataLog) else latest_log['total_reports']},
                {'name': 'BMKG', 'value': latest_log.total_bmkg if isinstance(latest_log, BigDataLog) else latest_log['total_bmkg']},
                {'name': 'News', 'value': latest_log.total_news if isinstance(latest_log, BigDataLog) else latest_log['total_news']},
                {'name': 'Weather', 'value': latest_log.total_weather if isinstance(latest_log, BigDataLog) else latest_log['total_weather']},
            ],
            'pie_chart': [
                {'name': 'Aplikasi Capstore', 'value': total_capstore, 'color': '#6366f1'},
                {'name': 'External Big Data', 'value': total_external, 'color': '#10b981'}
            ],
            'line_chart': historical_data
        }
        
        return jsonify({'status': 'success', 'data': stats}), 200
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)}), 500
