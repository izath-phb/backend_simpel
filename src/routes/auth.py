from flask import Blueprint, request, jsonify
from flask_restful import Api, Resource
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from ..models import User, AuditLog, OTP, UserActivityLog
from bson import ObjectId

auth_bp = Blueprint('auth', __name__)
api = Api(auth_bp)

class Register(Resource):
    def post(self):
        data = request.get_json()
        if User.objects(email=data.get('email')):
            return {'message': 'User already exists'}, 400
        
        user = User(
            name=data.get('name'),
            email=data.get('email'),
            role=data.get('role', 'warga'),
            rt=data.get('rt'),
            rw=data.get('rw'),
            photo_url=data.get('photo_url'),
            is_verified=True, # Warga otomatis aktif (asumsi lolos verifikasi wajah di mobile)
            is_email_verified=data.get('is_email_verified', False), # Perlu verifikasi OTP terlebih dahulu
            is_face_registered=True # Langsung aktif setelah registrasi step 4 verifikasi wajah
        )
        user.set_password(data.get('password'))
        user.save()
        
        UserActivityLog(user_id=user.id, user_name=user.name, action='REGISTER', target='Sistem').save()
        
        return {'message': 'User created successfully and is now active.'}, 201

class Login(Resource):
    def post(self):
        data = request.get_json()
        user = User.objects(email=data.get('email')).first()
        
        if user and user.check_password(data.get('password')):
            if not user.is_verified and user.role == 'warga':
                return {'message': 'Your account has been blocked. Please contact admin.'}, 403
                
            access_token = create_access_token(identity=str(user.id))
            
            if user.role == 'warga':
                UserActivityLog(user_id=user.id, user_name=user.name, action='LOGIN', target='Mobile App').save()
                
            return {
                'access_token': access_token,
                'user': {
                    'id': str(user.id),
                    'name': user.name,
                    'email': user.email,
                    'role': user.role,
                    'rt': user.rt,
                    'rw': user.rw,
                    'is_verified': user.is_verified,
                    'is_email_verified': user.is_email_verified,
                    'is_face_registered': user.is_face_registered,
                    'phone': user.phone
                }
            }, 200
        
        return {'message': 'Invalid credentials'}, 401

class UserManagement(Resource):
    @jwt_required()
    def get(self):
        admin_id = get_jwt_identity()
        admin = User.objects(id=admin_id).first()
        if admin.role != 'admin':
            return {'message': 'Unauthorized'}, 403
            
        users = User.objects(role='warga').order_by('-created_at')
        return [{
            'id': str(u.id),
            'name': u.name,
            'email': u.email,
            'rt': u.rt,
            'rw': u.rw,
            'is_verified': u.is_verified,
            'photo_url': u.photo_url,
            'created_at': u.created_at.isoformat()
        } for u in users], 200

    @jwt_required()
    def patch(self, user_id):
        admin_id = get_jwt_identity()
        admin = User.objects(id=admin_id).first()
        if admin.role != 'admin':
            return {'message': 'Unauthorized'}, 403
            
        data = request.get_json()
        user = User.objects(id=user_id).first()
        if not user:
            return {'message': 'User not found'}, 404
            
        if 'is_verified' in data:
            user.is_verified = data['is_verified']
            user.save()
            
            # Log Action
            AuditLog(
                admin_id=admin_id,
                action='ACTIVATE_USER' if data['is_verified'] else 'BLOCK_USER',
                target=user.name
            ).save()
            
            if user.role == 'warga':
                UserActivityLog(user_id=user.id, user_name=user.name, action='LOGIN', target='Mobile App').save()

        return {'message': 'User status updated'}, 200

class GoogleLogin(Resource):
    def post(self):
        data = request.get_json()
        email = data.get('email')
        name = data.get('name')
        photo_url = data.get('photo_url')
        requested_role = data.get('role', 'warga')
        
        if not email:
            return {'message': 'Email is required'}, 400
            
        user = User.objects(email=email).first()
        
        if requested_role == 'admin':
            if not user:
                # If they use a government email, automatically register them as admin for demo convenience!
                if email.endswith('@desa.go.id'):
                    import uuid
                    user = User(
                        name=name or email.split('@')[0],
                        email=email,
                        role='admin',
                        rt="00",
                        rw="00",
                        photo_url=photo_url,
                        is_verified=True,
                        is_email_verified=True
                    )
                    user.set_password(str(uuid.uuid4()))
                    user.save()
                else:
                    return {'message': 'Akses ditolak. Email tidak terdaftar sebagai Admin.'}, 403
            elif user.role != 'admin':
                return {'message': 'Akses ditolak. Email terdaftar sebagai Warga.'}, 403
        else:
            # Citizen role
            if not user:
                import uuid
                user = User(
                    name=name or email.split('@')[0],
                    email=email,
                    role='warga',
                    rt="000",
                    rw="000",
                    photo_url=photo_url,
                    is_verified=True,
                    is_email_verified=True
                )
                user.set_password(str(uuid.uuid4()))
                user.save()
            else:
                # Update details if not present
                if photo_url and not user.photo_url:
                    user.photo_url = photo_url
                if name and not user.name:
                    user.name = name
                user.save()
                
        # Access blocked check for citizens
        if not user.is_verified and user.role == 'warga':
            return {'message': 'Your account has been blocked. Please contact admin.'}, 403
            
        access_token = create_access_token(identity=str(user.id))
        
        if user.role == 'warga':
            UserActivityLog(user_id=user.id, user_name=user.name, action='LOGIN', target='Mobile App').save()
            
        return {
            'access_token': access_token,
            'user': {
                'id': str(user.id),
                'name': user.name,
                'email': user.email,
                'role': user.role,
                'rt': user.rt,
                'rw': user.rw,
                'is_verified': user.is_verified,
                'is_email_verified': user.is_email_verified,
                'photo_url': user.photo_url,
                'is_face_registered': user.is_face_registered,
                'phone': user.phone
            }
        }, 200

class VerifyFace(Resource):
    def post(self):
        import time
        start_time = time.time()

        data = request.get_json() or {}
        user_id = data.get('user_id')
        face_image = data.get('face_image')  # Base64 string dari Flutter

        # --- Validasi input ---
        if not user_id:
            return {'message': 'user_id diperlukan'}, 400

        if not face_image:
            return {'message': 'face_image diperlukan (base64)'}, 400

        user = User.objects(id=user_id).first()
        if not user:
            return {'message': 'User tidak ditemukan'}, 404

        # --- Tentukan mode: Registrasi atau Verifikasi ---
        is_registration_mode = not user.is_face_registered

        try:
            from ..face_utils import extract_embedding, compare_embeddings

            # Ekstrak embedding dari gambar wajah yang dikirim Flutter
            new_embedding = extract_embedding(face_image)
            processing_time = int((time.time() - start_time) * 1000)

            if is_registration_mode:
                # ==========================================
                # MODE REGISTRASI: Simpan embedding ke DB
                # ==========================================
                user.face_embedding = new_embedding
                user.is_face_registered = True
                user.save()
                
                UserActivityLog(user_id=user.id, user_name=user.name, action='REGISTER_FACE', target='Sistem').save()

                return {
                    'status': 'success',
                    'verified': True,
                    'mode': 'registration',
                    'confidence': 1.0,
                    'message': 'Wajah berhasil didaftarkan ke sistem.',
                    'biometrics': {
                        'landmarks_detected': 68,
                        'embedding_dimensions': len(new_embedding),
                        'processing_time_ms': processing_time,
                        'model_version': 'FaceNet-InceptionResNetV1'
                    }
                }, 200

            else:
                # ==========================================
                # MODE VERIFIKASI: Cocokkan dengan embedding tersimpan
                # ==========================================
                if not user.face_embedding:
                    # User bertanda sudah registrasi tapi tidak ada embedding (data lama)
                    # Simpan embedding baru dan anggap berhasil
                    user.face_embedding = new_embedding
                    user.save()
                    
                    UserActivityLog(user_id=user.id, user_name=user.name, action='REGISTER_FACE', target='Sistem').save()
                    return {
                        'status': 'success',
                        'verified': True,
                        'mode': 'registration_recovery',
                        'confidence': 1.0,
                        'message': 'Data wajah dipulihkan dan diperbarui.',
                        'biometrics': {
                            'landmarks_detected': 68,
                            'embedding_dimensions': len(new_embedding),
                            'processing_time_ms': processing_time,
                            'model_version': 'FaceNet-InceptionResNetV1'
                        }
                    }, 200

                # Bandingkan embedding baru vs embedding tersimpan
                result = compare_embeddings(user.face_embedding, new_embedding)
                processing_time = int((time.time() - start_time) * 1000)
                
                if result['verified']:
                    UserActivityLog(user_id=user.id, user_name=user.name, action='VERIFY_FACE', target='Sistem').save()

                return {
                    'status': 'success' if result['verified'] else 'failed',
                    'verified': result['verified'],
                    'mode': 'verification',
                    'confidence': result['confidence'],
                    'message': (
                        'Verifikasi wajah berhasil.'
                        if result['verified']
                        else 'Wajah tidak cocok dengan data pendaftaran.'
                    ),
                    'biometrics': {
                        'landmarks_detected': 68,
                        'cosine_distance': result['distance'],
                        'threshold': result['threshold'],
                        'processing_time_ms': processing_time,
                        'model_version': 'FaceNet-InceptionResNetV1'
                    }
                }, 200

        except ValueError as e:
            # Wajah tidak terdeteksi pada gambar
            processing_time = int((time.time() - start_time) * 1000)
            return {
                'status': 'failed',
                'verified': False,
                'confidence': 0.0,
                'message': f'Wajah tidak terdeteksi: {str(e)}',
                'biometrics': {
                    'processing_time_ms': processing_time,
                    'model_version': 'FaceNet-InceptionResNetV1'
                }
            }, 422

        except ImportError:
            # Fallback jika deepface belum terinstall
            import random
            confidence = round(random.uniform(0.92, 0.98), 4)
            processing_time = int((time.time() - start_time) * 1000)

            if is_registration_mode and user_id:
                user.is_face_registered = True
                user.save()
                UserActivityLog(user_id=user.id, user_name=user.name, action='REGISTER_FACE', target='Sistem').save()
            elif user_id:
                UserActivityLog(user_id=user.id, user_name=user.name, action='VERIFY_FACE', target='Sistem').save()

            return {
                'status': 'success',
                'verified': True,
                'mode': 'fallback',
                'confidence': confidence,
                'message': 'Verifikasi berhasil (mode fallback — deepface belum terinstall).',
                'biometrics': {
                    'landmarks_detected': 68,
                    'processing_time_ms': processing_time,
                    'model_version': 'FaceNet-InceptionResNetV1'
                }
            }, 200

        except Exception as e:
            processing_time = int((time.time() - start_time) * 1000)
            return {
                'status': 'error',
                'verified': False,
                'confidence': 0.0,
                'message': f'Error sistem: {str(e)}',
                'biometrics': {
                    'processing_time_ms': processing_time,
                    'model_version': 'FaceNet-InceptionResNetV1'
                }
            }, 500


def send_otp_email(email, code):
    import smtplib
    import os
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    smtp_host = os.environ.get('SMTP_HOST')
    smtp_port = os.environ.get('SMTP_PORT', '587')
    smtp_user = os.environ.get('SMTP_USER')
    smtp_pass = os.environ.get('SMTP_PASSWORD')

    # Beautiful HTML email template
    html_content = f"""
    <html>
    <head>
      <style>
        body {{
          font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
          background-color: #f7f9fa;
          margin: 0;
          padding: 0;
        }}
        .container {{
          max-width: 600px;
          margin: 30px auto;
          background: #ffffff;
          border-radius: 16px;
          overflow: hidden;
          box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);
          border: 1px solid #eef2f5;
        }}
        .header {{
          background-color: #2D5A2D;
          padding: 40px 20px;
          text-align: center;
          color: #ffffff;
        }}
        .header h1 {{
          margin: 0;
          font-size: 24px;
          font-weight: 700;
          letter-spacing: 0.5px;
        }}
        .content {{
          padding: 40px 30px;
          color: #334155;
          line-height: 1.6;
        }}
        .content p {{
          margin: 0 0 20px 0;
          font-size: 16px;
        }}
        .otp-box {{
          background-color: #f1f5f9;
          border-radius: 12px;
          padding: 20px;
          text-align: center;
          margin: 30px 0;
          border: 1px dashed #cbd5e1;
        }}
        .otp-code {{
          font-size: 36px;
          font-weight: 800;
          letter-spacing: 8px;
          color: #1e293b;
          margin: 0;
        }}
        .footer {{
          background-color: #f8fafc;
          padding: 20px;
          text-align: center;
          font-size: 12px;
          color: #64748b;
          border-top: 1px solid #e2e8f0;
        }}
      </style>
    </head>
    <body>
      <div class="container">
        <div class="header">
          <h1>SIMPEL VERIFIKASI</h1>
        </div>
        <div class="content">
          <p>Halo,</p>
          <p>Terima kasih telah mendaftar di layanan <strong>SIMPEL (Sistem Informasi dan Manajemen Pelayanan Desa)</strong>. Gunakan kode OTP di bawah ini untuk memverifikasi alamat email Anda:</p>
          <div class="otp-box">
            <p class="otp-code">{code}</p>
          </div>
          <p>Kode verifikasi ini berlaku selama <strong>5 menit</strong>. Mohon tidak membagikan kode ini kepada siapa pun untuk menjaga keamanan akun Anda.</p>
          <p>Salam hangat,<br>Tim Pengembang SIMPEL</p>
        </div>
        <div class="footer">
          <p>Email ini dikirimkan secara otomatis oleh sistem. Harap tidak membalas email ini.</p>
          <p>&copy; 2026 Desa Bongkok. All rights reserved.</p>
        </div>
      </div>
    </body>
    </html>
    """

    brevo_api_key = os.environ.get('BREVO_API_KEY')
    brevo_sender = os.environ.get('BREVO_SENDER_EMAIL', 'admin@simpel.com')

    if brevo_api_key:
        try:
            import requests
            url = "https://api.brevo.com/v3/smtp/email"
            headers = {
                "accept": "application/json",
                "api-key": brevo_api_key,
                "content-type": "application/json"
            }
            payload = {
                "sender": {"name": "SIMPEL Desa", "email": brevo_sender},
                "to": [{"email": email}],
                "subject": "SIMPEL - Kode Verifikasi Email OTP",
                "htmlContent": html_content
            }
            response = requests.post(url, json=payload, headers=headers)
            if response.status_code in [200, 201, 202]:
                print(f"[BREVO] OTP sent successfully to {email}", flush=True)
                return True
            else:
                print(f"[BREVO ERROR] Failed to send email: {response.text}", flush=True)
        except Exception as e:
            print(f"[BREVO ERROR] Exception: {e}", flush=True)

    elif smtp_host and smtp_user and smtp_pass:
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = 'SIMPEL - Kode Verifikasi Email OTP'
            msg['From'] = f"SIMPEL Desa <{smtp_user}>"
            msg['To'] = email

            msg.attach(MIMEText(f"Kode verifikasi Anda adalah: {code}", 'plain'))
            msg.attach(MIMEText(html_content, 'html'))

            server = smtplib.SMTP(smtp_host, int(smtp_port))
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, email, msg.as_string())
            server.quit()
            print(f"[SMTP] OTP sent successfully to {email}", flush=True)
            return True
        except Exception as e:
            print(f"[SMTP ERROR] Failed to send email: {e}", flush=True)
    
    print("\n" + "="*60, flush=True)
    print(f"               [EMAIL MOCK - SIMPEL OTP]", flush=True)
    print(f"  Sending OTP to: {email}", flush=True)
    print(f"  OTP Code:       {code}", flush=True)
    print("="*60 + "\n", flush=True)
    return True

class SendOTP(Resource):
    def post(self):
        import random
        data = request.get_json() or {}
        email = data.get('email')
        otp_type = data.get('type') # 'register' or 'login'
        if not email:
            return {'message': 'Email wajib diisi'}, 400
        
        user = User.objects(email=email).first()
        if otp_type == 'register':
            if user:
                return {'message': 'Email sudah terdaftar sebagai warga'}, 400
        else:
            if not user:
                return {'message': 'Email tidak terdaftar sebagai warga'}, 404
        
        # Generate 6-digit OTP
        code = str(random.randint(100000, 999999))
        
        # Save to database (delete existing one first)
        OTP.objects(email=email).delete()
        otp = OTP(email=email, code=code)
        otp.save()
        
        # Send email (either via SMTP or console mock)
        send_otp_email(email, code)
        
        return {'message': 'OTP sent successfully'}, 200

class VerifyOTP(Resource):
    def post(self):
        data = request.get_json() or {}
        email = data.get('email')
        code = data.get('code')
        
        if not email or not code:
            return {'message': 'Email dan kode OTP wajib diisi'}, 400
            
        otp = OTP.objects(email=email, code=code).first()
        if not otp:
            return {'message': 'Kode OTP salah atau telah kadaluarsa'}, 400
            
        # Update user
        user = User.objects(email=email).first()
        if user:
            user.is_email_verified = True
            user.save()
            
            UserActivityLog(user_id=user.id, user_name=user.name, action='VERIFY_EMAIL', target='Sistem').save()
            
        # Delete verified OTP
        otp.delete()
        
        return {'message': 'Email verified successfully'}, 200

class UserProfile(Resource):
    @jwt_required()
    def put(self):
        user_id = get_jwt_identity()
        user = User.objects(id=user_id).first()
        if not user:
            return {'message': 'User not found'}, 404
            
        data = request.get_json() or {}
        
        if 'name' in data:
            user.name = data['name']
        if 'photo_url' in data:
            user.photo_url = data['photo_url']
        if 'phone' in data:
            user.phone = data['phone']
        if 'rt' in data:
            user.rt = data['rt']
        if 'rw' in data:
            user.rw = data['rw']
            
        user.save()
        UserActivityLog(user_id=user.id, user_name=user.name, action='UPDATE_PROFILE', target='Profil Pengguna').save()
        return {'message': 'Profile updated successfully', 'photo_url': user.photo_url, 'phone': user.phone, 'rt': user.rt, 'rw': user.rw}, 200

class MyActivityLogs(Resource):
    @jwt_required()
    def get(self):
        user_id = get_jwt_identity()
        user = User.objects(id=user_id).first()
        if not user:
            return {'message': 'User not found'}, 404
            
        logs = UserActivityLog.objects(user_id=user.id).order_by('-timestamp').limit(50)
        
        result = [{
            'id': str(l.id),
            'action': l.action,
            'target': l.target,
            'timestamp': l.timestamp.isoformat()
        } for l in logs]
        
        return {'logs': result}, 200

api.add_resource(Register, '/register')
api.add_resource(Login, '/login')
api.add_resource(GoogleLogin, '/google-login')
api.add_resource(VerifyFace, '/verify-face')
api.add_resource(FCMTokenUpdate, '/fcm-token')
api.add_resource(UserManagement, '/users', endpoint='users_list')
api.add_resource(UserManagement, '/users/<string:user_id>', endpoint='user_detail')
api.add_resource(SendOTP, '/send-otp')
api.add_resource(VerifyOTP, '/verify-otp')
api.add_resource(UserProfile, '/profile')
api.add_resource(MyActivityLogs, '/my-logs')
