from flask import Blueprint, request
from flask_restful import Api, Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..models import Notification, User

notifications_bp = Blueprint('notifications', __name__)
api = Api(notifications_bp)

class NotificationList(Resource):
    @jwt_required()
    def get(self):
        user_id = get_jwt_identity()
        user = User.objects(id=user_id).first()
        if not user:
            return {'message': 'User not found'}, 404
            
        notifications = Notification.objects(user_id=user.id).order_by('-created_at')
        result = []
        for n in notifications:
            result.append({
                'id': str(n.id),
                'title': n.title,
                'body': n.body,
                'data': n.data,
                'is_read': n.is_read,
                'created_at': n.created_at.isoformat()
            })
            
        return result, 200

class NotificationRead(Resource):
    @jwt_required()
    def patch(self, notification_id):
        user_id = get_jwt_identity()
        notification = Notification.objects(id=notification_id, user_id=user_id).first()
        if not notification:
            return {'message': 'Notification not found'}, 404
            
        notification.is_read = True
        notification.save()
        return {'message': 'Notification marked as read'}, 200

class NotificationReadAll(Resource):
    @jwt_required()
    def patch(self):
        user_id = get_jwt_identity()
        Notification.objects(user_id=user_id, is_read=False).update(set__is_read=True)
        return {'message': 'All notifications marked as read'}, 200

api.add_resource(NotificationList, '/')
api.add_resource(NotificationRead, '/<string:notification_id>/read')
api.add_resource(NotificationReadAll, '/read-all')
