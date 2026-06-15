from flask import Blueprint, request, jsonify
from flask_restful import Api, Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..models import Report, User, ReportLog, AuditLog, Comment
from datetime import datetime

reports_bp = Blueprint('reports', __name__)
api = Api(reports_bp)

class ReportList(Resource):
    @jwt_required()
    def get(self):
        user_id = get_jwt_identity()
        user = User.objects(id=user_id).first()
        
        scope = request.args.get('scope', 'all')
        
        if user.role == 'admin':
            reports = Report.objects().order_by('-created_at')
        else:
            if scope == 'my':
                reports = Report.objects(user_id=user_id).order_by('-created_at')
            else:
                reports = Report.objects().order_by('-created_at')
            
        return [{
            'id': str(r.id),
            'user_id': str(r.user_id.id) if r.user_id else '',
            'user_name': User.objects(id=r.user_id.id).first().name if r.user_id and User.objects(id=r.user_id.id).first() else 'Warga',
            'title': r.title,
            'description': r.description,
            'category': r.category,
            'coordinates': r.coordinates,
            'status': r.status,
            'imageUrl': r.imageUrl,
            'afterImageUrl': r.afterImageUrl,
            'adminNote': r.adminNote,
            'rating': r.rating,
            'created_at': r.created_at.isoformat(),
            'likes': [str(u.id) for u in r.likes] if r.likes else [],
            'comments': [{
                'id': str(c.created_at.timestamp()),
                'user_id': str(c.user_id.id) if c.user_id else '',
                'user_name': c.user_name,
                'user_photo_url': c.user_photo_url or '',
                'content': c.content,
                'created_at': c.created_at.isoformat()
            } for c in r.comments] if r.comments else [],
            'logs': [{
                'status': l.status,
                'note': l.note,
                'timestamp': l.timestamp.isoformat()
            } for l in r.logs]
        } for r in reports], 200

    @jwt_required()
    def post(self):
        user_id = get_jwt_identity()
        data = request.get_json()
        
        report = Report(
            title=data.get('title'),
            description=data.get('description'),
            category=data.get('category'),
            coordinates=data.get('coordinates'), # [lat, lng]
            imageUrl=data.get('imageUrl'),
            user_id=user_id
        )
        # Initial Log
        report.logs.append(ReportLog(status='pending', note='Laporan berhasil dikirim oleh warga.'))
        report.save()
        
        return {'message': 'Report submitted successfully', 'id': str(report.id)}, 201

class ReportDetail(Resource):
    @jwt_required()
    def get(self, report_id):
        report = Report.objects(id=report_id).first()
        if not report:
            return {'message': 'Report not found'}, 404
        return {
            'id': str(report.id),
            'user_id': str(report.user_id.id) if report.user_id else '',
            'user_name': User.objects(id=report.user_id.id).first().name if report.user_id and User.objects(id=report.user_id.id).first() else 'Warga',
            'title': report.title,
            'description': report.description,
            'category': report.category,
            'coordinates': report.coordinates,
            'status': report.status,
            'imageUrl': report.imageUrl,
            'afterImageUrl': report.afterImageUrl,
            'adminNote': report.adminNote,
            'likes': [str(u.id) for u in report.likes] if report.likes else [],
            'comments': [{
                'id': str(c.created_at.timestamp()),
                'user_id': str(c.user_id.id) if c.user_id else '',
                'user_name': c.user_name,
                'user_photo_url': c.user_photo_url or '',
                'content': c.content,
                'created_at': c.created_at.isoformat()
            } for c in report.comments] if report.comments else [],
            'logs': [{
                'status': l.status,
                'note': l.note,
                'timestamp': l.timestamp.isoformat()
            } for l in report.logs]
        }, 200

    @jwt_required()
    def patch(self, report_id):
        user_id = get_jwt_identity()
        user = User.objects(id=user_id).first()
        
        if user.role != 'admin':
            return {'message': 'Unauthorized'}, 403
            
        data = request.get_json()
        report = Report.objects(id=report_id).first()
        if not report:
            return {'message': 'Report not found'}, 404
            
        if 'status' in data:
            note = data.get('note')
            if not note:
                return {'message': 'Note is required when updating status'}, 400
                
            report.status = data['status']
            # Add detailed log
            log = ReportLog(status=data['status'], note=note)
            report.logs.append(log)
            
            # Audit Log
            AuditLog(admin_id=user_id, action='UPDATE_REPORT_STATUS', target=report.title).save()
            
        if 'adminNote' in data:
            report.adminNote = data['adminNote']
            
        if 'afterImageUrl' in data:
            report.afterImageUrl = data['afterImageUrl']
            
        report.updated_at = datetime.utcnow()
        report.save()
        
        return {'message': 'Report updated successfully'}, 200

class ReportLikeToggle(Resource):
    @jwt_required()
    def post(self, report_id):
        user_id = get_jwt_identity()
        user = User.objects(id=user_id).first()
        if not user:
            return {'message': 'User not found'}, 404
            
        report = Report.objects(id=report_id).first()
        if not report:
            return {'message': 'Report not found'}, 404
            
        is_liked = False
        # Compare user objects or IDs
        liked_users = [str(u.id) for u in report.likes]
        if str(user.id) in liked_users:
            # find and remove
            for u in report.likes:
                if str(u.id) == str(user.id):
                    report.likes.remove(u)
                    break
            message = 'Unliked'
        else:
            report.likes.append(user)
            message = 'Liked'
            is_liked = True
            
        report.save()
        return {
            'message': message,
            'is_liked': is_liked,
            'likes_count': len(report.likes),
            'likes': [str(u.id) for u in report.likes]
        }, 200

class ReportComment(Resource):
    @jwt_required()
    def post(self, report_id):
        user_id = get_jwt_identity()
        user = User.objects(id=user_id).first()
        if not user:
            return {'message': 'User not found'}, 404
            
        report = Report.objects(id=report_id).first()
        if not report:
            return {'message': 'Report not found'}, 404
            
        data = request.get_json()
        content = data.get('content')
        if not content:
            return {'message': 'Comment content is required'}, 400
            
        comment = Comment(
            user_id=user,
            user_name=user.name,
            user_photo_url=user.photo_url or '',
            content=content,
            created_at=datetime.utcnow()
        )
        report.comments.append(comment)
        report.save()
        
        return {
            'message': 'Comment added successfully',
            'comment': {
                'id': str(comment.created_at.timestamp()),
                'user_id': str(user.id),
                'user_name': user.name,
                'user_photo_url': user.photo_url or '',
                'content': content,
                'created_at': comment.created_at.isoformat()
            }
        }, 201

api.add_resource(ReportList, '/')
api.add_resource(ReportDetail, '/<string:report_id>')
api.add_resource(ReportLikeToggle, '/<string:report_id>/like')
api.add_resource(ReportComment, '/<string:report_id>/comments')
