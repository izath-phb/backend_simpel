from flask import Blueprint, jsonify, request
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
            
        # Parse time_range
        time_range = request.args.get('time_range', '24h')
        limit = 24
        if time_range == '7d':
            limit = 24 * 7
        elif time_range == '30d':
            limit = 24 * 30

        # Get historical data for the line chart
        logs = BigDataLog.objects.order_by('-timestamp').limit(limit)
        historical_data = []
        for log in reversed(list(logs)):
            historical_data.append({
                'time': log.timestamp.strftime('%H:%M') if isinstance(log.timestamp, datetime.datetime) else 'N/A',
                'volume': log.total_users + log.total_reports + log.total_bmkg + log.total_news + log.total_weather,
                'bmkg': log.total_bmkg,
                'news': log.total_news,
                'weather': log.total_weather,
                'users': log.total_users,
                'reports': log.total_reports
            })
            
        # Add dummy data if history is empty to make chart visible
        if not historical_data:
            historical_data = [
                {'time': '08:00', 'volume': 150, 'bmkg': 20, 'news': 50, 'weather': 10, 'users': 100, 'reports': 30},
                {'time': '09:00', 'volume': 200, 'bmkg': 25, 'news': 55, 'weather': 12, 'users': 105, 'reports': 35},
                {'time': '10:00', 'volume': 180, 'bmkg': 30, 'news': 60, 'weather': 15, 'users': 110, 'reports': 40},
                {'time': '11:00', 'volume': 220, 'bmkg': 35, 'news': 65, 'weather': 20, 'users': 115, 'reports': 45},
                {'time': '12:00', 'volume': 250, 'bmkg': 40, 'news': 70, 'weather': 25, 'users': 120, 'reports': 50},
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
            'internal_bar_chart': [
                {'name': 'Users', 'value': latest_log.total_users if isinstance(latest_log, BigDataLog) else latest_log['total_users']},
                {'name': 'Reports', 'value': latest_log.total_reports if isinstance(latest_log, BigDataLog) else latest_log['total_reports']},
                {'name': 'Projects', 'value': latest_log.total_projects if isinstance(latest_log, BigDataLog) else latest_log['total_projects']},
            ],
            'external_pie_chart': [
                {'name': 'BMKG', 'value': latest_log.total_bmkg if isinstance(latest_log, BigDataLog) else latest_log['total_bmkg'], 'color': '#f59e0b'},
                {'name': 'News', 'value': latest_log.total_news if isinstance(latest_log, BigDataLog) else latest_log['total_news'], 'color': '#ec4899'},
                {'name': 'Weather', 'value': latest_log.total_weather if isinstance(latest_log, BigDataLog) else latest_log['total_weather'], 'color': '#06b6d4'},
            ],
            'line_chart': historical_data
        }
        
        return jsonify({'status': 'success', 'data': stats}), 200
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@bigdata_bp.route('/raw', methods=['GET'])
def get_raw_data():
    try:
        source = request.args.get('source', 'news') # news, weather, bmkg
        search = request.args.get('search', '').lower()
        limit = int(request.args.get('limit', 50))
        
        results = []
        
        # Access underlying PyMongo collection to handle dynamic fields easily
        if source == 'news':
            coll = NewsData._get_collection()
        elif source == 'weather':
            coll = WeatherData._get_collection()
        elif source == 'bmkg':
            coll = BmkgData._get_collection()
        else:
            return jsonify({'status': 'error', 'message': 'Invalid source'}), 400

        # Build query
        query = {}
        if search:
            query = {'$or': [
                {'title': {'$regex': search, '$options': 'i'}},
                {'description': {'$regex': search, '$options': 'i'}},
                {'city': {'$regex': search, '$options': 'i'}},
                {'name': {'$regex': search, '$options': 'i'}}
            ]}
            
        cursor = coll.find(query).sort('_id', -1).limit(limit)
        
        for doc in cursor:
            # Clean up ObjectId for JSON serialization
            doc['_id'] = str(doc['_id'])
            results.append(doc)
            
        return jsonify({'status': 'success', 'data': results}), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)}), 500

