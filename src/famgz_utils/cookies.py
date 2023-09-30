from pathlib import Path

from .misc import print, json_
from .time_ import now, f_time



class Cookies:

    def __init__(self, folder_path):
        self.folder_path = Path(folder_path)

        self.cookies_txt_paths = []
        self.cookies_json_paths = []

        self.cookies = {}  # {filename: {key: {value:STRING, expirationDate:TIMESTAMP}}}

        self.get_cookies_file_paths()  # populate self.cookies_paths
        self.get_cookies_data()  # populate self.cookies

    def get_cookies(self, filename=None):
        cookies = self.cookies.get(filename)
        # try desired cookies
        if cookies:
            expired_keys = self.get_expired_keys(cookies)
            if not expired_keys:
                return self.normalize_cookies(cookies)
            print(f'[yellow]{filename} cookies has {len(expired_keys)} expired keys: {" ".join(expired_keys)}')
            if len(self.cookies) > 1:
                print('[yellow]falling back to other cookies')
            else:
                return self.normalize_cookies(cookies)  # return desired cookies regarless expiration
        # try first valid cookies
        for filename, cookies in self.cookies.items():
            expired_keys = self.get_expired_keys(cookies)
            if expired_keys:
                continue
            return self.normalize_cookies(cookies)
        print('[yellow]No valid cookies available')
        return None

    def normalize_cookies(self, cookies):
        return {key: data['value'] for key, data in cookies.items()}

    def read_file(self, path: Path):
        if path.suffix == '.txt':
            with open(path) as f:
                return f.read()
        elif path.suffix == '.json':
            return json_(path)

    def parse_cookies_txt(self, file):
        # Netscape cookies format:
        #        0         1    2    3       4       5      6
        # .instagram.com  TRUE  /  TRUE  TIMESTAMP  NAME  TOKEN
        if not file:
            return None
        lines = [x.strip().expandtabs().split()
                 for x in file.split('\n')
                 if x.strip() and not x.startswith('#')]
        if not lines:
            return None
        # return format -> {key: {value:STRING, expirationDate:TIMESTAMP}}
        return {
            x[5]: {
                'value': x[6] ,
                'expirationDate': int(x[4]),
            }
            for x in lines
        }

    def parse_cookies_json(self, file):
        # JSON cookies format:
        # [{keys:values}]
        if not file:
            return None
        # return format -> {key: {value:STRING, expirationDate:TIMESTAMP}}
        return {
            x['name']: {
                'value': x.get('value', ''),
                'expirationDate': int(x.get('expirationDate', 0)),
            }
            for x in file
        }

    def get_cookies_data(self):
        # txt files
        for path in self.cookies_txt_paths:
            raw_file = self.read_file(path)
            # validate file first line
            if not raw_file or not raw_file.startswith('# Netscape HTTP Cookie File'):
                self.cookies_txt_paths.remove(path)
                continue
            content = self.parse_cookies_txt(raw_file)
            if not content:
                self.cookies_txt_paths.remove(path)
                continue
            self.cookies[path.name] = content

        # JSON files
        for path in self.cookies_json_paths:
            raw_file = self.read_file(path)
            # validate JSON datatypes
            if not raw_file or not isinstance(raw_file, list) or not isinstance(raw_file[0], dict):
                self.cookies_json_paths.remove(path)
                continue
            content = self.parse_cookies_json(raw_file)
            if not content:
                self.cookies_json_paths.remove(path)
                continue
            self.cookies[path.name] = content

    def get_cookies_file_paths(self):
        self.cookies_txt_paths.extend( [x for x in self.folder_path.iterdir() if x.suffix == '.txt'] )
        self.cookies_json_paths.extend( [x for x in self.folder_path.iterdir() if x.suffix == '.json'] )

    def get_expired_keys(self, cookies):
        #  utc ?
        now_ = now() - 50000
        expired = [
            key
            for key, data in cookies.items()
            if data['expirationDate'] and data['expirationDate'] < now_
        ]
        return expired

    def check_expired_cookies(self, display=False):
        expired = []
        for filename, cookies in self.cookies.items():
            if self.get_expired_keys(cookies):
                expired.append(filename)
        if display:
            print(f'{len(expired)} cookies: {" ".join(expired)}')
        return expired

    def print_cookies(self):
        now_ = now()
        for filename, cookies in self.cookies.items():
            print(f'\n[bright_blue]{filename}')
            max_key_len = max( [len(key) for key in cookies] )
            max_key_len = min(30, max_key_len)
            max_value_len = 50
            print(f'   {"KEY":<{max_key_len}} {"EXPIRES IN"} {"VALUE":^{max_value_len}}')
            for i, (key, data) in enumerate(cookies.items()):
                # expirationDate
                remaining = f_remaining = '-'
                expired = False
                if data["expirationDate"]:
                    remaining = data["expirationDate"] - now_
                    if remaining < 0:
                        expired = True
                    f_remaining = f_time(None, diff=remaining, out='single')
                date_color = '[white]' if not expired else '[red]'

                # value
                value = data['value']
                suffix = '' if len(value) <= max_value_len else '...'
                value = value[:max_value_len] + suffix

                print(f'[bright_black]{i+1:<3}[white]{key[:max_key_len]:<{max_key_len}} {date_color}{f_remaining:^10} [bright_black]{value}')
