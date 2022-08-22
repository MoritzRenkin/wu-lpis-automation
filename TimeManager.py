from datetime import datetime, timedelta, time
import requests
import pause

class TimeManager:
    def __init__(self, vanilla=False):
        if not vanilla:
            response = requests.get('http://worldtimeapi.org/api/timezone/Europe/Vienna.txt').content

            local_time = datetime.now()

            time_list = response.decode('UTF-8').split('+', 2)[0].split('\n')[-1].split('T')[1].replace('.', ':').split(':')
            time_list = [int(x) for x in time_list]

            correct_time = datetime.combine(date=datetime.today(),
                                                 time=time(hour=time_list[0], minute=time_list[1], second=time_list[2],
                                                           microsecond=time_list[3]))

            self.delta = local_time - correct_time

        else:
            self.delta = timedelta()

    def get_correct(self, datetime_object):
        return datetime_object - self.delta

    def get_local(self, datetime_object):
        return datetime_object + self.delta

    def corrected_now(self):
        return self.get_correct(datetime.now())

    def pause_until(self, correct_datetime_object):
        pause.until(correct_datetime_object + self.delta)

