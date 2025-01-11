from models.report import SensorModel
from models.alert import AlertModel, DeviceState, AlertSeverity
from datetime import datetime
import pytz
local_tz = pytz.timezone('Asia/Ho_Chi_Minh')  # Or your local timezone

class Alert:
    def __init__(self, sensor_data: SensorModel = None):
        self.sensor_data = sensor_data
        self.VOLTAGE_WORKING_MIN = 220
        self.VOLTAGE_MAXTHRESHOLD = 240
        self.VOLTAGE_MINTHRESHOLD = 40
        self.current_time = datetime.now(pytz.UTC).astimezone(local_tz)

    def check_voltage(self):
        return self.sensor_data.voltage >= self.VOLTAGE_MINTHRESHOLD
    
    def in_working_hours(self):
        # Assume hour_on (18) > hour_off (5). Working in night time
        current_hour = self.current_time.hour
        current_minute = self.current_time.minute
        is_passed_hour_on = current_hour >= self.sensor_data.hour_on and current_hour <= 23 and (current_minute >= self.sensor_data.minute_on)
        is_yet_hour_off = current_hour <= self.sensor_data.hour_off and current_minute < self.sensor_data.minute_off

        return is_passed_hour_on or is_yet_hour_off

    def check_status(self) -> tuple[DeviceState, AlertSeverity]:
        if self.sensor_data:
            working = self.check_voltage()
            on_working_hours = self.in_working_hours()
            toggle = self.sensor_data.toggle
            auto = self.sensor_data.auto
            # Normal conditions
            ## Device is on manually or automatically during working hours
            if (working and toggle) and (not auto or (auto and on_working_hours)):
                return DeviceState.WORKING, AlertSeverity.NORMAL
            ## Device is off manually or automatically when out of working hours
            elif (not working and not toggle) and (not auto or (auto and not on_working_hours)):
                return DeviceState.POWER_LOST, AlertSeverity.NORMAL
            # Critical conditions
            ## Devie is lost power
            elif not working and toggle:
                return DeviceState.POWER_LOST, AlertSeverity.CRITICAL
            ## Device is still on despite switching down
            elif working and not toggle:
                return DeviceState.WORKING, AlertSeverity.CRITICAL
            # Warning conditions
            ## Device is on out of working hours
            elif working and auto and not on_working_hours:
                return DeviceState.ON_OUT_OF_HOUR, AlertSeverity.WARNING
            ## Device is off out of working hours
            elif not working and auto and on_working_hours:
                return DeviceState.OFF_OUT_OF_HOUR, AlertSeverity.WARNING
        else: 
            return DeviceState.DiSCONNECTED, AlertSeverity.CRITICAL