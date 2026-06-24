import os
import sys

# Add backend dir to python path
sys.path.append(r"d:\project capstone\backand")

from flask import Flask
from mongoengine import connect
from src.models import Report, User

app = Flask(__name__)
connect('capstone', host='mongodb://localhost:27017/capstone')

try:
    reports = Report.objects()
    for r in reports:
        print(f"Report ID: {r.id}")
        if r.user_id:
            try:
                uid = getattr(r.user_id, 'id', r.user_id)
                print(f"User ID: {uid}")
            except Exception as e:
                print(f"Error accessing user_id: {e}")
        else:
            print("No user_id")
except Exception as e:
    print(f"Database error: {e}")
