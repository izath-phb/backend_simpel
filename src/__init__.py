from flask import Flask, jsonify, request
from flask_restful import Api
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from mongoengine import connect
import os

jwt = JWTManager()

def create_app():
    app = Flask(__name__)

    # Configuration
    mongo_uri = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/simpel_db')
    app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'simpel-super-secret-key-2024')
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = 86400  # 24 hours

    # Initialize Extensions
    connect(host=mongo_uri)
    jwt.init_app(app)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Register Blueprints
    from .routes.auth import auth_bp
    from .routes.reports import reports_bp
    from .routes.projects import projects_bp
    from .routes.dashboard import dashboard_bp
    from .routes.announcements import announcements_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(reports_bp, url_prefix='/api/reports')
    app.register_blueprint(projects_bp, url_prefix='/api/projects')
    app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')
    app.register_blueprint(announcements_bp, url_prefix='/api/announcements')

    @app.before_request
    def log_request_info():
        print(f"\n[REQUEST] {request.method} {request.path}", flush=True)
        if request.is_json:
            try:
                body = request.get_json()
                if body:
                    # Mask sensitive data like password if printed
                    safe_body = {k: ('*****' if k in ['password', 'secret', 'token'] else v) for k, v in body.items()}
                    print(f"[BODY] {safe_body}", flush=True)
            except Exception:
                pass

    @app.after_request
    def log_response_info(response):
        print(f"[RESPONSE] Status: {response.status}", flush=True)
        return response

    @app.route('/api/health')
    def health():
        return {'status': 'ok', 'service': 'SIMPEL API'}, 200

    @app.route('/api/swagger.json')
    def get_swagger():
        import json
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            with open(os.path.join(current_dir, 'swagger.json'), 'r', encoding='utf-8') as f:
                data = json.load(f)
            return jsonify(data), 200
        except Exception as e:
            return {'error': str(e)}, 500

    @app.route('/api/docs')
    def render_swagger_ui():
        html_content = """<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="UTF-8">
  <title>SIMPEL API - Swagger UI</title>
  <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@3.52.5/swagger-ui.css">
  <style>
    html { box-sizing: border-box; overflow: -margin-top-collapse; }
    *, *:before, *:after { box-sizing: inherit; }
    body { margin: 0; background: #fafafa; }
  </style>
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="https://unpkg.com/swagger-ui-dist@3.52.5/swagger-ui-bundle.js"></script>
  <script src="https://unpkg.com/swagger-ui-dist@3.52.5/swagger-ui-standalone-preset.js"></script>
  <script>
    window.onload = function() {
      const ui = SwaggerUIBundle({
        url: "/api/swagger.json",
        dom_id: '#swagger-ui',
        deepLinking: true,
        presets: [
          SwaggerUIBundle.presets.apis,
          SwaggerUIStandalonePreset
        ],
        plugins: [
          SwaggerUIBundle.plugins.DownloadUrl
        ],
        layout: "BaseLayout"
      });
      window.ui = ui;
    };
  </script>
</body>
</html>"""
        from flask import Response
        return Response(html_content, mimetype='text/html')

    return app
