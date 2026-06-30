from flask import Blueprint, request
from flask_restful import Api, Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..models import ChatSession, ChatMessage, User, UserActivityLog
from datetime import datetime

chat_bp = Blueprint('chat', __name__)
api = Api(chat_bp)

class AdminChatSessions(Resource):
    @jwt_required()
    def get(self):
        user_id = get_jwt_identity()
        user = User.objects(id=user_id).first()
        if user.role != 'admin':
            return {'message': 'Unauthorized'}, 403
            
        sessions = ChatSession.objects().order_by('-updated_at')
        result = []
        for s in sessions:
            try:
                uid = str(s.user_id.id) if s.user_id else None
            except Exception:
                uid = None
            
            if not uid:
                continue
                
            result.append({
                'id': str(s.id),
                'user_id': uid,
                'user_name': s.user_name or "Warga",
                'user_photo_url': s.user_photo_url,
                'last_message': s.last_message or "",
                'last_sender_role': s.last_sender_role or "warga",
                'unread_admin': s.unread_admin or 0,
                'updated_at': s.updated_at.isoformat() if s.updated_at else datetime.utcnow().isoformat()
            })
        return result, 200

class AdminChatMessages(Resource):
    @jwt_required()
    def get(self, target_user_id):
        user_id = get_jwt_identity()
        user = User.objects(id=user_id).first()
        if user.role != 'admin':
            return {'message': 'Unauthorized'}, 403
            
        session = ChatSession.objects(user_id=target_user_id).first()
        if not session:
            return [], 200
            
        # Reset unread count for admin
        if session.unread_admin > 0:
            session.unread_admin = 0
            session.save()
            
        messages = ChatMessage.objects(session_id=session.id).order_by('created_at')
        result = []
        for m in messages:
            try:
                sid = str(m.sender_id.id) if m.sender_id else None
            except Exception:
                sid = None
            result.append({
                'id': str(m.id),
                'sender_id': sid or "unknown",
                'sender_role': m.sender_role,
                'message': m.message,
                'created_at': m.created_at.isoformat() if m.created_at else datetime.utcnow().isoformat()
            })
        return result, 200

    @jwt_required()
    def post(self, target_user_id):
        user_id = get_jwt_identity()
        user = User.objects(id=user_id).first()
        if user.role != 'admin':
            return {'message': 'Unauthorized'}, 403
            
        data = request.get_json()
        message_text = data.get('message')
        if not message_text:
            return {'message': 'Message is required'}, 400
            
        target_user = User.objects(id=target_user_id).first()
        if not target_user:
            return {'message': 'User not found'}, 404
            
        session = ChatSession.objects(user_id=target_user_id).first()
        if not session:
            session = ChatSession(
                user_id=target_user,
                user_name=target_user.name,
                user_photo_url=target_user.photo_url
            )
            
        session.last_message = message_text
        session.last_sender_role = 'admin'
        session.unread_user += 1
        session.updated_at = datetime.utcnow()
        session.save()
        
        message = ChatMessage(
            session_id=session,
            sender_id=user,
            sender_role='admin',
            message=message_text
        )
        message.save()
        
        return {
            'id': str(message.id),
            'sender_role': message.sender_role,
            'message': message.message,
            'created_at': message.created_at.isoformat()
        }, 201

class WargaChatMessages(Resource):
    @jwt_required()
    def get(self):
        user_id = get_jwt_identity()
        
        session = ChatSession.objects(user_id=user_id).first()
        if not session:
            return [], 200
            
        # Reset unread count for user
        if session.unread_user > 0:
            session.unread_user = 0
            session.save()
            
        messages = ChatMessage.objects(session_id=session.id).order_by('created_at')
        result = []
        for m in messages:
            try:
                sid = str(m.sender_id.id) if m.sender_id else None
            except Exception:
                sid = None
            result.append({
                'id': str(m.id),
                'sender_id': sid or "unknown",
                'sender_role': m.sender_role,
                'message': m.message,
                'created_at': m.created_at.isoformat() if m.created_at else datetime.utcnow().isoformat()
            })
        return result, 200

    @jwt_required()
    def post(self):
        user_id = get_jwt_identity()
        user = User.objects(id=user_id).first()
        
        data = request.get_json()
        message_text = data.get('message')
        if not message_text:
            return {'message': 'Message is required'}, 400
            
        session = ChatSession.objects(user_id=user_id).first()
        if not session:
            session = ChatSession(
                user_id=user,
                user_name=user.name,
                user_photo_url=user.photo_url
            )
            
        session.last_message = message_text
        session.last_sender_role = 'warga'
        session.unread_admin += 1
        session.updated_at = datetime.utcnow()
        # Update user info in case it changed
        session.user_name = user.name
        session.user_photo_url = user.photo_url
        session.save()
        
        message = ChatMessage(
            session_id=session,
            sender_id=user,
            sender_role='warga',
            message=message_text
        )
        message.save()
        
        UserActivityLog(user_id=user.id, user_name=user.name, action='SEND_MESSAGE', target='Admin Desa').save()
        
        return {
            'id': str(message.id),
            'sender_role': message.sender_role,
            'message': message.message,
            'created_at': message.created_at.isoformat()
        }, 201

api.add_resource(AdminChatSessions, '/sessions')
api.add_resource(AdminChatMessages, '/admin/messages/<string:target_user_id>')
api.add_resource(WargaChatMessages, '/my-messages')
