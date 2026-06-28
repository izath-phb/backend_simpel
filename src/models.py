import mongoengine as db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Document):
    meta = {'collection': 'users'}
    name = db.StringField(required=True)
    email = db.EmailField(required=True, unique=True)
    password = db.StringField(required=True)
    role = db.StringField(choices=['admin', 'warga'], default='warga')
    rt = db.StringField()
    rw = db.StringField()
    phone = db.StringField()
    photo_url = db.StringField()
    is_verified = db.BooleanField(default=False)       # Untuk verifikasi pendaftaran
    is_email_verified = db.BooleanField(default=False) # Untuk verifikasi email OTP
    is_face_registered = db.BooleanField(default=False) # Status perekaman wajah
    face_embedding = db.ListField(db.FloatField())      # Embedding FaceNet 128-dimensi
    created_at = db.DateTimeField(default=datetime.utcnow)


    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

class OTP(db.Document):
    meta = {
        'collection': 'otps',
        'indexes': [
            {'fields': ['created_at'], 'expireAfterSeconds': 300} # Hapus otomatis setelah 5 menit
        ]
    }
    email = db.EmailField(required=True)
    code = db.StringField(required=True)
    created_at = db.DateTimeField(default=datetime.utcnow)


class ReportLog(db.EmbeddedDocument):
    status = db.StringField(required=True)
    note = db.StringField()
    timestamp = db.DateTimeField(default=datetime.utcnow)

class Comment(db.EmbeddedDocument):
    user_id = db.ReferenceField('User', required=True)
    user_name = db.StringField(required=True)
    user_photo_url = db.StringField()
    content = db.StringField(required=True)
    created_at = db.DateTimeField(default=datetime.utcnow)

class Report(db.Document):
    meta = {'collection': 'reports'}
    user_id = db.ReferenceField('User')
    title = db.StringField(required=True)
    description = db.StringField(required=True)
    category = db.StringField()
    coordinates = db.ListField(db.FloatField()) # [lat, lng]
    status = db.StringField(
        choices=['pending', 'verified', 'on_progress', 'resolved', 'rejected'], 
        default='pending'
    )
    imageUrl = db.StringField()
    afterImageUrl = db.StringField()
    adminNote = db.StringField()
    logs = db.EmbeddedDocumentListField(ReportLog)
    rating = db.IntField(min_value=1, max_value=5) # 1-5 bintang
    likes = db.ListField(db.ReferenceField('User'))
    comments = db.EmbeddedDocumentListField(Comment)
    created_at = db.DateTimeField(default=datetime.utcnow)
    updated_at = db.DateTimeField(default=datetime.utcnow)

class Project(db.Document):
    meta = {'collection': 'projects'}
    title = db.StringField(required=True)
    description = db.StringField()
    budget = db.FloatField()
    progress = db.IntField(min_value=0, max_value=100, default=0)
    status = db.StringField()
    coordinates = db.ListField(db.FloatField()) # [lat, lng]
    imageUrl = db.StringField()
    startDate = db.DateTimeField()
    endDate = db.DateTimeField()
    followers = db.ListField(db.ReferenceField('User'))
    created_at = db.DateTimeField(default=datetime.utcnow)

class Announcement(db.Document):
    meta = {'collection': 'announcements'}
    title = db.StringField(required=True)
    content = db.StringField(required=True)
    imageUrl = db.StringField() # Banner
    authorName = db.StringField()
    is_carousel = db.BooleanField(default=False) # Muncul di slider aplikasi warga
    created_at = db.DateTimeField(default=datetime.utcnow)

class AuditLog(db.Document):
    meta = {'collection': 'audit_logs'}
    admin_id = db.ReferenceField(User)
    action = db.StringField()
    target = db.StringField()
    timestamp = db.DateTimeField(default=datetime.utcnow)

class UserActivityLog(db.Document):
    meta = {'collection': 'user_activity_logs'}
    user_id = db.ReferenceField('User', required=True)
    user_name = db.StringField()
    action = db.StringField(required=True)
    target = db.StringField()
    timestamp = db.DateTimeField(default=datetime.utcnow)

class ChatSession(db.Document):
    meta = {'collection': 'chat_sessions'}
    user_id = db.ReferenceField('User', required=True, unique=True)
    user_name = db.StringField()
    user_photo_url = db.StringField()
    last_message = db.StringField()
    last_sender_role = db.StringField(choices=['admin', 'warga'])
    unread_admin = db.IntField(default=0)
    unread_user = db.IntField(default=0)
    updated_at = db.DateTimeField(default=datetime.utcnow)
    created_at = db.DateTimeField(default=datetime.utcnow)

class ChatMessage(db.Document):
    meta = {'collection': 'chat_messages'}
    session_id = db.ReferenceField(ChatSession, required=True)
    sender_id = db.ReferenceField('User', required=True)
    sender_role = db.StringField(choices=['admin', 'warga'])
    message = db.StringField(required=True)
    created_at = db.DateTimeField(default=datetime.utcnow)

class BigDataLog(db.Document):
    meta = {'collection': 'big_data_logs'}
    timestamp = db.DateTimeField(default=datetime.utcnow)
    total_users = db.IntField(default=0)
    total_reports = db.IntField(default=0)
    total_projects = db.IntField(default=0)
    total_bmkg = db.IntField(default=0)
    total_news = db.IntField(default=0)
    total_weather = db.IntField(default=0)

class BmkgData(db.Document):
    meta = {'collection': 'bmkg', 'db_alias': 'bigdata_db'}
    # Define fields if needed, or leave flexible

class NewsData(db.Document):
    meta = {'collection': 'news', 'db_alias': 'bigdata_db'}

class WeatherData(db.Document):
    meta = {'collection': 'weather', 'db_alias': 'bigdata_db'}
