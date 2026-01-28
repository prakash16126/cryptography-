from django.db import models
import json
from django.conf import settings

class User:
    FILE_PATH = settings.BASE_DIR / 'user_data.json'

    @staticmethod
    def save_user(data):
        with open(User.FILE_PATH, 'w') as file:
            json.dump(data, file)

    @staticmethod
    def load_users():
        try:
            with open(User.FILE_PATH, 'r') as file:
                return json.load(file)
        except FileNotFoundError:
            return {}

# Create your models here.
