from flask import Blueprint, request
from flask_restful import Api, Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..models import Announcement, User, AuditLog
from datetime import datetime

announcements_bp = Blueprint('announcements', __name__)
api = Api(announcements_bp)

class AnnouncementList(Resource):
    def get(self):
        announcements = Announcement.objects().order_by('-created_at')
        return [{
            'id': str(a.id),
            'title': a.title,
            'content': a.content,
            'imageUrl': a.imageUrl,
            'authorName': a.authorName,
            'is_carousel': a.is_carousel,
            'created_at': a.created_at.isoformat()
        } for a in announcements], 200

    @jwt_required()
    def post(self):
        user_id = get_jwt_identity()
        user = User.objects(id=user_id).first()
        if user.role != 'admin':
            return {'message': 'Unauthorized'}, 403
            
        data = request.get_json()
        ann = Announcement(
            title=data.get('title'),
            content=data.get('content'),
            imageUrl=data.get('imageUrl'),
            authorName=user.name,
            is_carousel=data.get('is_carousel', False)
        )
        ann.save()
        AuditLog(admin_id=user_id, action='CREATE_ANNOUNCEMENT', target=ann.title).save()
        
        return {'message': 'Announcement created', 'id': str(ann.id)}, 201

class AnnouncementDetail(Resource):
    @jwt_required()
    def patch(self, ann_id):
        user_id = get_jwt_identity()
        user = User.objects(id=user_id).first()
        if user.role != 'admin':
            return {'message': 'Unauthorized'}, 403
            
        data = request.get_json()
        ann = Announcement.objects(id=ann_id).first()
        if not ann:
            return {'message': 'Announcement not found'}, 404
            
        if 'is_carousel' in data:
            ann.is_carousel = data['is_carousel']
            
        if 'title' in data: ann.title = data['title']
        if 'content' in data: ann.content = data['content']
        if 'imageUrl' in data: ann.imageUrl = data['imageUrl']
            
        ann.save()
        return {'message': 'Announcement updated'}, 200

    @jwt_required()
    def delete(self, ann_id):
        user_id = get_jwt_identity()
        user = User.objects(id=user_id).first()
        if user.role != 'admin':
            return {'message': 'Unauthorized'}, 403
        ann = Announcement.objects(id=ann_id).first()
        if ann:
            title = ann.title
            ann.delete()
            AuditLog(admin_id=user_id, action='DELETE_ANNOUNCEMENT', target=title).save()
        return {'message': 'Deleted'}, 200

api.add_resource(AnnouncementList, '/')
api.add_resource(AnnouncementDetail, '/<string:ann_id>')
