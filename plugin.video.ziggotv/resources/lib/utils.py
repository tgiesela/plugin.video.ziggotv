import binascii
from datetime import datetime


def hexlify(barr):
    binascii.hexlify(bytearray(barr))


def ah2b(s):
    return bytes.fromhex(s)


def b2ah(barr):
    return barr.hex()


def atoh(barr):
    return "".join("{:02x}".format(ord(c)) for c in barr)


def main():
    pass


import threading
import time


class Timer(threading.Thread):

    def __init__(self, interval, callback_function=None):
        self._timer_runs = threading.Event()
        self._timer_runs.set()
        self.interval = interval
        self.callback_function = callback_function
        super().__init__()

    def run(self):
        while self._timer_runs.is_set():
            time.sleep(self.interval)
            self.timer()

    def stop(self):
        self._timer_runs.clear()

    def timer(self):
        self.callback_function()


class DatetimeHelper:
    @staticmethod
    def fromUnix(unix_time: int, tz: datetime.tzinfo = None) -> datetime:
        date_time_max = datetime(2100, 12, 31, 0, 0)
        max_unix_time_in_secs = time.mktime(date_time_max.timetuple())
        if unix_time > max_unix_time_in_secs:
            return datetime.fromtimestamp(unix_time/1000, tz)
        else:
            return datetime.fromtimestamp(unix_time, tz)

    @staticmethod
    def now(tz: datetime.tzinfo = None) -> datetime:
        return datetime.now(tz)

    @staticmethod
    def toUnix(dt: str, dt_format: str):
        return int(time.mktime(datetime.strptime(dt, dt_format).timetuple()))

    @staticmethod
    def unixDatetime(dt: datetime):
        return int(time.mktime(dt.timetuple()))


if __name__ == '__main__':
    pass