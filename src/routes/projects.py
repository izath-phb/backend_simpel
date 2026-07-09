from flask import Blueprint, request
from flask_restful import Api, Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..models import Project, User, AuditLog, UserActivityLog, Notification
from datetime import datetime
from ..utils.fcm import send_push_notification

projects_bp = Blueprint('projects', __name__)
api = Api(projects_bp)

class ProjectList(Resource):
    def get(self):
        projects = Project.objects().order_by('-created_at')
        result = []
        for p in projects:
            followers_list = []
            if p.followers:
                for u in p.followers:
                    try:
                        followers_list.append(str(getattr(u, 'id', u)))
                    except Exception:
                        pass
            
            result.append({
                'id': str(p.id),
                'title': p.title,
                'description': p.description,
                'budget': p.budget,
                'progress': p.progress,
                'status': p.status,
                'coordinates': p.coordinates,
                'imageUrl': p.imageUrl,
                'startDate': p.startDate.isoformat() if p.startDate else None,
                'endDate': p.endDate.isoformat() if p.endDate else None,
                'followers': followers_list,
                'created_at': p.created_at.isoformat()
            })
        return result, 200

    @jwt_required()
    def post(self):
        user_id = get_jwt_identity()
        user = User.objects(id=user_id).first()
        if user.role != 'admin':
            return {'message': 'Unauthorized'}, 403
            
        data = request.get_json()
        # Handle ISO strings for dates
        if 'startDate' in data and data['startDate']:
            data['startDate'] = datetime.fromisoformat(data['startDate'].replace('Z', ''))
        if 'endDate' in data and data['endDate']:
            data['endDate'] = datetime.fromisoformat(data['endDate'].replace('Z', ''))
            
        project = Project(**data)
        project.save()
        
        AuditLog(admin_id=user_id, action='CREATE_PROJECT', target=project.title).save()
        
        return {'message': 'Project created', 'id': str(project.id)}, 201

class ProjectDetail(Resource):
    @jwt_required()
    def patch(self, project_id):
        user_id = get_jwt_identity()
        user = User.objects(id=user_id).first()
        if user.role != 'admin':
            return {'message': 'Unauthorized'}, 403
            
        data = request.get_json()
        project = Project.objects(id=project_id).first()
        if not project:
            return {'message': 'Project not found'}, 404
            
        for key, value in data.items():
            if hasattr(project, key):
                if key in ['startDate', 'endDate'] and value:
                    value = datetime.fromisoformat(value.replace('Z', ''))
                setattr(project, key, value)
        
        project.save()
        AuditLog(admin_id=user_id, action='UPDATE_PROJECT', target=project.title).save()
        
        # Notify followers
        if project.followers:
            title = "Update Proyek: " + project.title
            body = f"Ada pembaruan pada proyek yang Anda ikuti. Progres saat ini: {project.progress}%."
            data = {"type": "project_update", "project_id": str(project.id)}
            
            for follower in project.followers:
                # Resolve the reference if it's lazily loaded
                follower_user = follower if isinstance(follower, User) else User.objects(id=follower.id).first()
                if not follower_user:
                    continue
                    
                # Create in-app notification
                Notification(
                    user_id=follower_user.id,
                    title=title,
                    body=body,
                    data=data
                ).save()
                
                # Send push notification
                if follower_user.fcm_token:
                    send_push_notification(follower_user.fcm_token, title, body, data)
        
        return {'message': 'Project updated'}, 200

    @jwt_required()
    def delete(self, project_id):
        user_id = get_jwt_identity()
        user = User.objects(id=user_id).first()
        if user.role != 'admin':
            return {'message': 'Unauthorized'}, 403
            
        project = Project.objects(id=project_id).first()
        if project:
            title = project.title
            project.delete()
            AuditLog(admin_id=user_id, action='DELETE_PROJECT', target=title).save()
            
        return {'message': 'Project deleted'}, 200

class ProjectFollowToggle(Resource):
    @jwt_required()
    def post(self, project_id):
        user_id = get_jwt_identity()
        user = User.objects(id=user_id).first()
        if not user:
            return {'message': 'User not found'}, 404
            
        project = Project.objects(id=project_id).first()
        if not project:
            return {'message': 'Project not found'}, 404
            
        is_following = False
        followers_list = [str(u.id) for u in project.followers]
        if str(user.id) in followers_list:
            for u in project.followers:
                if str(u.id) == str(user.id):
                    project.followers.remove(u)
                    UserActivityLog(user_id=user.id, user_name=user.name, action='UNFOLLOW_PROJECT', target=project.title).save()
                    break
            message = 'Unfollowed'
        else:
            project.followers.append(user)
            UserActivityLog(user_id=user.id, user_name=user.name, action='FOLLOW_PROJECT', target=project.title).save()
            message = 'Followed'
            is_following = True
            
        project.save()
        
        followers_list = []
        if project.followers:
            for u in project.followers:
                try:
                    followers_list.append(str(getattr(u, 'id', u)))
                except Exception:
                    pass
                    
        return {
            'message': message,
            'is_following': is_following,
            'followers_count': len(followers_list),
            'followers': followers_list
        }, 200

api.add_resource(ProjectList, '/')
api.add_resource(ProjectDetail, '/<string:project_id>')
api.add_resource(ProjectFollowToggle, '/<string:project_id>/follow')
