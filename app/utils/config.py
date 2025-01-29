from enum import Enum
from decouple import config
# Import all the models in the database
REDIS_HOST = config("REDIS_HOST")
REDIS_PORT = config("REDIS_PORT")
FRONTEND_ENDPOINT = config("FRONTEND_ENDPOINT")
SUPERADMIN_USERNAME = config("SUPERADMIN_USERNAME")
SUPERADMIN_PASSWORD = config("SUPERADMIN_PASSWORD")
SUPERADMIN_EMAIL = config("SUPERADMIN_EMAIL")

SECRET_KEY = config("SECRET_KEY")  # Replace with a secure key
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 # 1 day in minutes
POWERLOST_THRESHOLD = 50 # 50W
DEBUG = config("DEBUG", default=False, cast=bool)
ACCESS_TOKEN_EXPIRE_MINUTES = config("ACCESS_TOKEN_EXPIRE_MINUTES", default=60, cast=int) # 1 hour

# MQTT setup
MQTT_BROKER = config("MQTT_BROKER")
MQTT_PORT = int(config("MQTT_PORT"))
MQTT_CLIENT_ID = config("MQTT_CLIENT_ID")

# Mongo
MONGO_URI = config("MONGO_URI")