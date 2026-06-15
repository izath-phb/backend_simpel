from flask import Blueprint
from flask_restful import Api, Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..models import Report, Project, User, AuditLog
from datetime import datetime, timedelta

dashboard_bp = Blueprint('dashboard', __name__)
api = Api(dashboard_bp)

class AdminStats(Resource):
    @jwt_required()
    def get(self):
        user_id = get_jwt_identity()
        user = User.objects(id=user_id).first()
        if user.role != 'admin':
            return {'message': 'Unauthorized'}, 403
            
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        stats = {
            'total_reports': Report.objects.count(),
            'pending_reports': Report.objects(status='pending').count(),
            'verified_reports': Report.objects(status='verified').count(),
            'on_progress_reports': Report.objects(status='on_progress').count(),
            'resolved_reports': Report.objects(status='resolved').count(),
            'reports_today': Report.objects(created_at__gte=today).count(),
            'total_projects': Project.objects.count(),
            'total_budget': sum(p.budget for p in Project.objects),
            'avg_progress': sum(p.progress for p in Project.objects) / max(Project.objects.count(), 1),
            'blocked_users': User.objects(is_verified=False, role='warga').count()
        }
        
        # Monthly reports for chart
        monthly_reports = []
        for i in range(6):
            month_start = (today - timedelta(days=30*i)).replace(day=1)
            month_end = (month_start + timedelta(days=32)).replace(day=1)
            count = Report.objects(created_at__gte=month_start, created_at__lt=month_end).count()
            monthly_reports.append({'month': month_start.strftime('%b'), 'count': count})
            
        stats['chart_data'] = monthly_reports[::-1]
        
        # Recent Audit Logs
        logs = AuditLog.objects().order_by('-timestamp').limit(10)
        stats['recent_logs'] = [{
            'admin': l.admin_id.name if l.admin_id else 'System',
            'action': l.action,
            'target': l.target,
            'timestamp': l.timestamp.isoformat()
        } for l in logs]
        
        return stats, 200

class UserStats(Resource):
    @jwt_required()
    def get(self):
        user_id = get_jwt_identity()
        
        stats = {
            'total_reports': Report.objects(user_id=user_id).count(),
            'pending_reports': Report.objects(user_id=user_id, status='pending').count(),
            'verified_reports': Report.objects(user_id=user_id, status='verified').count(),
            'on_progress_reports': Report.objects(user_id=user_id, status='on_progress').count(),
            'resolved_reports': Report.objects(user_id=user_id, status='resolved').count(),
        }
        
        return stats, 200

api.add_resource(AdminStats, '/stats')
api.add_resource(UserStats, '/user-stats')
