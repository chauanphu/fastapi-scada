import pytz
from datetime import datetime

local_tz = pytz.timezone('Asia/Ho_Chi_Minh')  # Or your local timezone

def get_real_time():
    data = datetime.now(pytz.UTC).astimezone(local_tz)
    return data

def fix_offset(time: datetime):
    localized = pytz.utc.localize(time)
    return localized.astimezone(local_tz)