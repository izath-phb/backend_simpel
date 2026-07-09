import firebase_admin
from firebase_admin import credentials, messaging
import os
import logging
import json

logger = logging.getLogger(__name__)

# Initialize Firebase Admin
try:
    # 1. Attempt to initialize via Raw JSON string from env var (Best for Railway/Heroku)
    firebase_json_str = os.environ.get('FIREBASE_SERVICE_ACCOUNT_JSON')
    
    # 2. Attempt to initialize via file path
    cred_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    
    if firebase_json_str:
        cred_dict = json.loads(firebase_json_str)
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
        logger.info("Firebase Admin initialized with raw JSON credentials.")
    elif cred_path and os.path.exists(cred_path):
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
        logger.info("Firebase Admin initialized with credentials.")
    else:
        # Tries default initialization (works in GCP or if already authenticated)
        try:
            firebase_admin.initialize_app()
            logger.info("Firebase Admin initialized with default credentials.")
        except Exception as e:
            logger.warning(f"Could not initialize Firebase Admin automatically: {e}")
            logger.warning("Push notifications will not be sent until credentials are provided.")
except Exception as e:
    logger.error(f"Error initializing Firebase Admin: {e}")

def send_push_notification(token, title, body, data=None):
    if not token:
        return False
        
    try:
        # Ensure we have an app initialized
        if not firebase_admin._apps:
            logger.warning("Firebase Admin is not initialized. Cannot send push notification.")
            return False

        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            android=messaging.AndroidConfig(
                priority='high',
                notification=messaging.AndroidNotification(
                    channel_id='high_importance_channel',
                    sound='default'
                )
            ),
            data=data or {},
            token=token,
        )
        
        response = messaging.send(message)
        logger.info(f"Successfully sent message: {response}")
        return True
    except Exception as e:
        logger.error(f"Error sending push notification to {token}: {e}")
        return False
