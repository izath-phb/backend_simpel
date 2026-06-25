from flask import Blueprint, request, jsonify
from flask_restful import Api, Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..models import Report, User, ReportLog, AuditLog, Comment, UserActivityLog
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
            
        result = []
        for r in reports:
            try:
                user_id_str = ''
                user_name = 'Warga'
                
                try:
                    if r.user_id:
                        uid = getattr(r.user_id, 'id', r.user_id)
                        user_id_str = str(uid)
                        found_user = User.objects(id=uid).first()
                        if found_user:
                            user_name = found_user.name
                except Exception:
                    pass
                
                likes_list = []
                if hasattr(r, 'likes') and r.likes:
                    for u in r.likes:
                        try:
                            likes_list.append(str(getattr(u, 'id', u)))
                        except Exception:
                            pass
                            
                comments_list = []
                if hasattr(r, 'comments') and r.comments:
                    for c in r.comments:
                        try:
                            c_user_id = str(getattr(c.user_id, 'id', c.user_id)) if c.user_id else ''
                        except Exception:
                            c_user_id = ''
                            
                        comments_list.append({
                            'id': str(c.created_at.timestamp()),
                            'user_id': c_user_id,
                            'user_name': c.user_name,
                            'user_photo_url': c.user_photo_url or '',
                            'content': c.content,
                            'created_at': c.created_at.isoformat()
                        })
                result.append({
                    'id': str(r.id),
                    'user_id': user_id_str,
                    'user_name': user_name,
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
                    'likes': likes_list,
                    'comments': comments_list,
                    'logs': [{
                        'status': l.status,
                        'note': l.note,
                        'timestamp': l.timestamp.isoformat()
                    } for l in r.logs] if hasattr(r, 'logs') and r.logs else []
                })
            except Exception as e:
                print(f"Skipping malformed report {r.id}: {e}", flush=True)
                continue
            
        return result, 200

    @jwt_required()
    def post(self):
        user_id = get_jwt_identity()
        user = User.objects(id=user_id).first()
        data = request.get_json()
        
        report = Report(
            title=data.get('title'),
            description=data.get('description'),
            category=data.get('category'),
            coordinates=data.get('coordinates'), # [lat, lng]
            imageUrl=data.get('imageUrl'),
            user_id=user
        )
        # Initial Log
        report.logs.append(ReportLog(status='pending', note='Laporan berhasil dikirim oleh warga.'))
        report.save()
        
        UserActivityLog(user_id=user.id, user_name=user.name, action='CREATE_REPORT', target=report.title).save()
        
        return {'message': 'Report created successfully', 'id': str(report.id)}, 201

class ReportDetail(Resource):
    @jwt_required()
    def get(self, report_id):
        try:
            report = Report.objects(id=report_id).first()
            if not report:
                return {'message': 'Report not found'}, 404
                
            try:
                user_id_str = str(getattr(report.user_id, 'id', report.user_id)) if report.user_id else ''
                user_name = User.objects(id=user_id_str).first().name if user_id_str and User.objects(id=user_id_str).first() else 'Warga'
            except Exception:
                user_id_str = ''
                user_name = 'Warga'
                
            likes_list = []
            if hasattr(report, 'likes') and report.likes:
                for u in report.likes:
                    try:
                        likes_list.append(str(getattr(u, 'id', u)))
                    except Exception:
                        pass
                        
            comments_list = []
            if hasattr(report, 'comments') and report.comments:
                for c in report.comments:
                    try:
                        c_user_id = str(getattr(c.user_id, 'id', c.user_id)) if c.user_id else ''
                    except Exception:
                        c_user_id = ''
                    comments_list.append({
                        'id': str(c.created_at.timestamp()),
                        'user_id': c_user_id,
                        'user_name': c.user_name,
                        'user_photo_url': getattr(c, 'user_photo_url', ''),
                        'content': c.content,
                        'created_at': c.created_at.isoformat()
                    })

            return {
                'id': str(report.id),
                'user_id': user_id_str,
                'user_name': user_name,
                'title': report.title,
                'description': report.description,
                'category': report.category,
                'coordinates': report.coordinates,
                'status': report.status,
                'imageUrl': report.imageUrl,
                'afterImageUrl': report.afterImageUrl,
                'adminNote': report.adminNote,
                'rating': report.rating,
                'likes': likes_list,
                'comments': comments_list,
                'logs': [{
                    'status': l.status,
                    'note': l.note,
                    'timestamp': l.timestamp.isoformat()
                } for l in report.logs] if hasattr(report, 'logs') and report.logs else []
            }, 200
        except Exception as e:
            print(f"Error fetching report detail: {e}", flush=True)
            return {'message': 'Internal Server Error', 'error': str(e)}, 500

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

    @jwt_required()
    def delete(self, report_id):
        user_id = get_jwt_identity()
        user = User.objects(id=user_id).first()
        
        if user.role != 'admin':
            return {'message': 'Unauthorized'}, 403
            
        report = Report.objects(id=report_id).first()
        if not report:
            return {'message': 'Report not found'}, 404
            
        report_title = report.title
        report.delete()
        
        # Audit Log
        AuditLog(admin_id=user_id, action='DELETE_SPAM_REPORT', target=report_title).save()
        
        return {'message': 'Report deleted successfully'}, 200

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
            UserActivityLog(user_id=user.id, user_name=user.name, action='LIKE_REPORT', target=report.title).save()
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
        
        UserActivityLog(user_id=user.id, user_name=user.name, action='COMMENT_REPORT', target=report.title).save()
        
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
