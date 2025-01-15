import pytz
from datetime import datetime

local_tz = pytz.timezone('Asia/Ho_Chi_Minh')  # Or your local timezone

def get_real_time():
    return datetime.now(pytz.UTC).astimezone(local_tz)