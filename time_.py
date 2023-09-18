import time
from time import sleep
import functools
import calendar
from datetime import datetime, timedelta
from timeit import default_timer as timer
from .utils import print

_timezone_in_sec = time.timezone


class Time:  # TODO: wrapper everything inside this class

    def __init__(self):
        self.day_in_sec = 24 * 60 * 60  # 86400 seconds
        self.hour_in_sec = 60 * 60      # 3600 seconds
        self.min_in_sec = 60            # 60 seconds


def now():
    return time.time()  # in timestamp


def now_utc():
    now_utc = datetime.now().utcnow()
    return now_utc.timestamp()  # in timestamp


def today():
    import datetime
    return datetime.date.today()  # in full date YYYY/MM/DD


def second():
    return datetime.now().second


def minute():
    return datetime.now().minute


def hour():
    return datetime.now().hour


def day():
    return datetime.now().day


def weekday(iso_format=False):
    '''
    regular format: 0=monday 1=tuesday 2=wednesday 3=thursday 4=friday 5=saturday 6=sunday
    iso format:     1=monday 2=tuesday 3=wednesday 4=thursday 5=friday 6=saturday 7=sunday
    '''
    if iso_format:
        return datetime.now().isoweekday()
    return datetime.now().weekday()


def month():
    return datetime.now().month


def year():
    return datetime.now().year


def dayparts():
    ''' Return the current minute within the 1440 minutes of a day '''
    return (hour() * 60) + minute()


def get_local_date_time(t=None):
    t = t or time.localtime()
    local_time = time.strftime('%Y-%m-%d %H:%M:%S', t)
    t_f = f"{local_time}"
    return t_f


def timestamp_to_date(x, full=False):
    if not full:
        return datetime.fromtimestamp(float(x)).date()
    return datetime.fromtimestamp(float(x))


def timestamp_to_full_date(x):
    return datetime.fromtimestamp(float(x))


def add_months(sourcedate, months):
    import datetime
    month = sourcedate.month - 1 + months
    year = sourcedate.year + month // 12
    month = month % 12 + 1
    day = min(sourcedate.day, calendar.monthrange(year, month)[1])
    return datetime.date(year, month, day)


def date_to_timestamp(*x):
    '''
    Expected input (in order):
    Mandatory: year, month, day.
    Optional:  hour, minute, seconds, mseconds.
    '''
    t =  datetime(*x).timestamp()  # input in integers
    return int(t)


def split_utc_date(t):
    ''' Expects t in format: <2022-04-30T17:00:00.000Z> '''
    date_, time_ = t.strip('Z').split('T')
    time_, *_, = time_.split('.')
    year, month, day = date_.split('-')
    hour, minute, second = time_.split(':')
    # print(year, month, day, hour, minute, second)`
    return [int(x) for x in (year, month, day, hour, minute, second)]


def ldap_to_timestamp(x, add_timezone=True):
    x = int(x)
    digits = len(str(x))
    # Invalid LDAP timestamp
    if digits not in [17, 18]:
        return x
    if digits == 17:
        x *= 10
    x = datetime(1601, 1, 1) + timedelta(seconds=x/10000000)
    x = int(x.timestamp())
    if add_timezone:
        x -= _timezone_in_sec
    return int(x)


def timeit(func):
    '''
    Decorator
    Time the parsed function execution with precision
    '''
    @functools.wraps(func)
    def inner(*a, **kw):
        t1 = timer()
        res = func(*a, **kw)
        t2 = timer()-t1
        print(f'[bright_black]<{func.__name__}> elapsed: {f_time(None, t2, decimal=5)}')
        return res
    return inner


def min_duration(wait):
    '''
    Decorator
    Wait minimum residual duration
    if function execution time is lower than `wait`.
    '''
    def decorator(func):
        @functools.wraps(func)
        def inner(*a, **kw):
            t1 = timer()
            out = func(*a, **kw)
            elapsed = timer()-t1
            wait_left = max(wait - elapsed, 0)
            sleep(wait_left)
            return out
        return inner
    return decorator


def f_time(t1, diff=None, out='single', decimal=0):
    '''
    Formats a given timestamp interval `diff` if given
    or calculate it based on t1 and current time
    '''
    diff = diff if (diff or diff == 0) else (time.time() - t1)

    m, s = divmod(diff, 60)
    h, m = divmod(m,  60)
    d, h = divmod(h,  24)

    d, h, m = int(d), int(h), int(m)

    s = int(s) if decimal==0 else round(s, decimal)

    fd = f'{d}d' if d else 0  # day
    fh = f'{h}h' if h else 0  # hour
    fm = f'{m}m' if m else 0  # minute
    fs = f'{s}s' if s else '0s'  # second

    # example: 2d 20h 0m 50s (diff=244850)
    return {
        # '2d'
        'single':  fd or fh or fm or fs,
        # '2d 20h 50s'
        'partial':  ' '.join([f'{x}{y}' for x, y in ((d,'d'),(h,'h'),(m,'m'),(s,'s'),) if x]) or '0s',
        # ' 2d 20h     50s'
        'partial2': ' '.join([f'{x:>2}{y}' if x else '   ' for x, y in ((d,'d'),(h,'h'),(m,'m'),(s,'s'),)]),
        # ' 2d 20h  0m 50s'
        'full':     ' '.join([f'{x:>2}{y}'                 for x, y in ((d,'d'),(h,'h'),(m,'m'),(s,'s'),)]),
        # (2, 20, 0, 50)
        'sep_raw': (d, h, m, s),
        # ('2d', '20h', None, '50s')
        'sep': (fd, fh, fm, fs)
    }[out]


def countdown(t, clear=False):
    '''
    Starts a continuous HH:MM:SS display countdown.
    Input time in seconds.
    '''
    t = int(t) if not isinstance(t, int) else t

    while t >= 0:
        m, s = divmod(t, 60)
        h, m = divmod(m, 60)
        timer = f'{h:d}:{m:02d}:{s:02d}'
        print(timer, end="\r")
        sleep(1)
        t -= 1
    # print()
    if clear:
        from famgz_utils import clear_last_console_line
        clear_last_console_line()
    return
