import base64
import json
import os
import requests
import subprocess as sp
import sys
from bs4 import BeautifulSoup
from os.path import join as pj
from pathlib import Path
from time import sleep

from .config import print


def clear_cmd_console():
    os.system('cls')


def clear_last_console_line(end='\r'):
    n = os.get_terminal_size().columns
    __builtins__.print(' '*n, end=end)


def run(command, cmd=False, silent=True):
    if not silent:
        sp.run(command, shell=cmd)
    else:
        # subprocess.call(f'{("cmd.exe /C " if cmd is True else "")}{command}',)
        sp.run(command, shell=cmd, stderr=sp.DEVNULL, stdout=sp.DEVNULL)


def get_current_os_user():
    return os.environ.get('USER', os.environ.get('USERNAME'))


def open_folder(path):
    ''' Cross-platform folder opener '''
    import webbrowser
    path = os.path.realpath(path)
    webbrowser.open(path)


def get_running_processes():

    def reduce(x):
        return x.strip().split(' ')[0].strip()

    a = sp.run('tasklist', stdout=sp.PIPE)
    a = a.stdout.decode('utf-8')
    p = {reduce(x) for x in a.split('\n') if reduce(x).endswith('.exe')}
    return p


def kill_process():
    ''' Kill all chrome related proccesses '''
    run('taskkill /IM "chrome.exe" /F', silent=True)
    run('taskkill /IM "chromedriver.exe" /F', silent=True)
    run('taskkill /IM "software_reporter_tool.exe" /F', silent=True)


def func_name(n=0):
    return sys._getframe(n + 1).f_code.co_name


def is_valid_uuid(string):
    import uuid
    try:
        uuid.UUID(str(string))
        return True
    except ValueError:
        return False


def is_valid_b64(string):
    try:
        base64.b64decode(string + '===')
        return True
    except:
        return False


def format_real(x):
    x = float(x)
    x = f'R$ {x:,.2f}'
    x = x.replace('.', '@')
    x = x.replace(',', '.')
    x = x.replace('@', ',')
    return x


def sort_dict(data, reverse=False):
    ''' Sort nested dicts by keys '''
    if isinstance(data, (list, tuple)):
        return [sort_dict(x) for x in data]
    if not isinstance(data, dict):
        return data
    return {k: sort_dict(v) for k, v in sorted(data.items(), reverse=reverse)}


def is_json_response(r):
    return 'json' in r.headers.get('content-type')


def json_(path,
          new='__null__',
          backup: bool = False,
          n_backups: int = 1,
          indent=None,
          sort_keys: bool = False,
          read_tries: int = 5,
          read_encoding='utf-8-sig',
          write_encoding='utf-8',
          ensure_ascii=True,
          create_file=False,
          ):
    '''
    Generic JSON assistant.
    Read/write JSON data based on `new`.
    TODO: add update parameter to append information
    '''
    file_path = Path(path).resolve()
    file_existed = True
    _null = old = '__null__'

    # file does not exist
    if not file_path.exists():
        file_existed = False
        print(f'\[json_][yellow]file does not exists: {file_path}{" creating it..." if create_file or new is not _null else ""}')
        if create_file and new is _null:
            # create file with empty dict {}
            with open(file_path, 'w', encoding=write_encoding) as f:
                json.dump({}, f)

    if file_existed:
        # file path is invalid, likely a folder
        if not file_path.is_file():
            print(f'[yellow]Invalid file path: {file_path}')
            return False

        # read file
        for i in range(read_tries):
            if not os.access(file_path, os.R_OK):
                print(f'[bright_black]Cannot access file ({i}): {file_path}')
                sleep(.1)
                continue
            try:
                with open(file_path, 'r', encoding=read_encoding) as f:
                    old = json.load(f)
                break
            except (PermissionError, FileNotFoundError) as e:
                print(e, file_path)
            except json.decoder.JSONDecodeError as e:
                print(e, file_path)

    '''READ MODE'''
    # returns data if exists or empty dict
    if new is _null:
        return old if old is not _null else {}

    # abort write if no changes
    if new == old:
        return False

    # validate new
    assert new not in (None, False, True), f'Invalid data to write: {new}'

    '''WRITE MODE'''
    # check if JSON serializable
    _ = json.dumps(new)

    # backup if file exists
    if backup and (old is not _null):
        import shutil
        saved = False
        folderpath = file_path.parent
        filename = file_path.name
        checks = range(1, max(n_backups+1, 2))
        # search for available .bak slot
        for i in checks:
            suffix = '' if i == 1 else f'({i})'
            bak_path = f'{file_path}{suffix}.bak'
            if not os.path.isfile(bak_path):
                shutil.move(file_path, bak_path)
                saved = True
                break
        # no .bak slot available to overwrite, fallback to older file
        if not saved:
            files = [file for file in folderpath.iterdir() if file.is_file() and file.name.startswith(filename)]
            files.sort(key=lambda x: x.stat().st_mtime)
            bak_path = files[0]
            shutil.move(file_path, bak_path)
            saved = True

    # use loop to avoid keyboard interrupt corruption (can also be done with "signal"?)
    # TODO: add update implementation
    # content = old.update(new) for dicts / old.append(new) for lists
    while True:
        try:
            # write data
            with open(file_path, 'w', encoding=write_encoding) as f:
                json.dump(new, f, indent=indent, sort_keys=sort_keys, ensure_ascii=ensure_ascii)  # indent=0 creates new lines
            return True
        except KeyboardInterrupt:
            pass


def logger(path, item):  # path == full path to file.txt
    '''
    Deprecated. Replaced by `log_txt`.
    '''
    with open(path, 'r+', encoding='utf-8') as f:
        file = f.read()
        if file.strip():
            if not file.endswith('\n'):
                f.write('\n')
        f.write(str(item) + '\n')


def log_txt(path, new=None, dupe=False):
    '''
    Read or write *.txt files based on `new` is given or not.
    <dupe> allows duplicate entries to be written
    '''
    if not os.path.isfile(path):  # File not found, no need to check duplicates
        if new:
            with open(path, 'a', encoding='utf-8') as f:
                f.write(str(new) + '\n')
        else:
            raise FileNotFoundError(f'Missing file in read mode. Path: {path}')

    else:
        with open(path, 'r+', encoding='utf-8') as f:
            file = f.read()
            old = [x.strip() for x in file.split('\n') if x.strip() and not x.strip().startswith('#')]

            if new:
                if new not in old or dupe:
                    # write new line at end of file if needed
                    if file.strip():
                        if not file.endswith('\n'):
                            f.write('\n')
                    f.write(str(new) + '\n')
            else:
                return old


def log_json(log_path, slug='', new_value=None):
    '''
    Read or log data in json based on whether "new_value" is given or not
    Built to read/write slug:value entries
    '''
    log_path = Path(log_path)

    assert log_path.is_file(), f'Invalid path: {log_path}'

    with open(log_path, 'r', encoding='utf-8-sig') as f:
        data = json.load(f)

    # read mode, returns a single slug:mpd value or all of them
    if new_value in (None, ''):
        return data.get(slug) if slug else data

    # log mode
    if data.get(slug) == new_value:  # exit if there's no change
        return
    else:
        data[slug] = new_value

    assert slug, f'Missing {slug = } in update mode'
    assert isinstance(new_value, str) or new_value == 0, f'Invalid {new_value = } in update mode'

    # backup. log.json.bak will be overwritten
    # safe to proceed directly, "data = json.load(f)" as guardian in case file is empty
    from shutil import copyfile
    bak_path = Path(log_path.parent, log_path.name + '.bak')
    copyfile(log_path, bak_path)

    with open(log_path, 'w', encoding='utf-8-sig') as f:
        json.dump(data, f, indent=0, sort_keys=False)  # indent=0 creates new lines


def read_log(log_path, item=None, get_key=None):
    '''
    Deprecated. Used to work with file.txt with dicts by line. Replaced by `log_json`.
    Generates an iterable or return a specific value

    "item" can be :str = key or dict: {key: value}

    Return conditions:
        log_path only = return list of full dicts (data)
        log_path, item:str = return list of data[key]'s
        log_path, item:dict = return single dict data
        log_path, item:dict, get_key = return data[get_key] based on item:dict

    :param log_path: log.txt full path
    :param item: str(key) or {key: value}
    :param get_key: key to get based on {key: value}
    :return: iterable (full dicts / keys) or specific info
    '''
    def file_error():
        raise FileNotFoundError(f'[read_log] Invalid log path for {log_path}')

    # generator
    def gen():
        with open(log_path, encoding='utf-8-sig') as f:
            for line in f:
                line = line.strip()
                # avoid blank line
                if not line:
                    continue
                # avoid comments
                if line.startswith('#'):
                    continue
                # check if is dict format
                if not line.startswith('{') or not line.endswith('}'):
                    raise ValueError(f'[read_log] Invalid dict format in line:\n{line}')

                data = eval(line)

                if key is not None:
                    if get_key is not None:
                        if data[key] == value:
                            yield data[get_key]
                            break
                    else:
                        if value is not None:
                            if data[key] == value:
                                yield data
                                break
                        else:
                            yield data[key]
                else:
                    yield data

    # check if path is valid
    if not os.path.exists(log_path):
        file_error()
    if not log_path.endswith('.txt'):
        if not os.path.isfile(pj(log_path, 'log.txt')):
            file_error()
        else:
            log_path = pj(log_path, 'log.txt')
            if not os.path.isfile(log_path):
                file_error()

    # parse "item"
    key = value = None
    if isinstance(item, str):
        key = item
    elif isinstance(item, dict):
        key, value = list(item.items())[0]
    if value is not None and key is None:
        raise ValueError('[read_log] "key" is missing')
    if get_key is not None:
        if value is None:
            raise ValueError('[read_log] parsed "get_key" but "value" is missing')
        if key is None:
            raise ValueError('[read_log] parsed "get_key" but "key" is missing')

    # return info
    if value is None:
        return list(gen())
    else:
        for i in gen():
            return i


def edit_log(file_path, old, new):  # still need some tests
    import os
    from shutil import copyfile

    file_path = file_path.strip(os.sep)      # remove '\' at the end
    assert os.path.isfile(file_path)        # assert file exists
    assert file_path.endswith('.txt')        # assert file is .txt

    assert old and new                      # assert data is not empty ('', [], None)
    old = str(old)
    new = str(new)

    with open(file_path, encoding='utf-8-sig') as f:
        old_file = f.read()

    if old in old_file:
        try:
            backup_path = file_path + '.bak'  # create backup
            copyfile(file_path, backup_path)
            with open(file_path, 'w', encoding='utf-8-sig') as f:
                new_file = old_file.replace(old, new)
                f.write(new_file)
            print(f'[edit_log] string: {new} edited in file: {file_path} !')
        except:
            print(f'[edit_log] Error writing data, backup available: {backup_path}')
            pass
        else:
            os.remove(backup_path)
    else:
        print(f'[edit_log] string not found in file: {old}')


class LogPrint:
    '''
    Rich print and log to file simultaneously.
    Initialization: `print = LogPrint(<path\\to\\logfile>).print`
    '''
    def __init__(self, path, dated=False):
        self.dated = dated
        self.ext = 'log'
        path = Path(path)
        parent, stem = path.parent, path.stem
        self.extless_path = str(Path(parent, stem))
        self._print = print
        from builtins import print as builtin_print
        self.builtin_print = builtin_print

    def _log_path(self):
        if not self.dated:
            return f'{self.extless_path}.{self.ext}'
        from datetime import date
        day = f'{str(date.today())}'
        return f'{self.extless_path}_{day}.{self.ext}'

    def print(self, *a, **kw):
        # rich print to terminal
        self._print(*a, **kw)
        # log to file
        with open(self._log_path(), 'a', encoding='utf-8') as f:
            kw.pop('highlight', None)
            self.builtin_print(*a, **kw, file=f)


def check_all_keys(film_data: dict):
    keys = ['slug', 'title_pt', 'title_eng', 'original_title', 'imdb_id', 'year', 'length', 'genres', 'directors', 'countries', 'languages', 'cast', 'synopsis_pt', 'synopsis_eng', 'production', 'producer', 'screenplay', 'cinematography', 'editing']
    for key in keys:
        if key not in film_data.keys():
            film_data[key] = None
    return film_data


def clean_name(x, dot=True):
    import re
    from unidecode import unidecode
    if x is None:
        return None
    x = x.strip()
    x = unidecode(x)
    x = re.sub(r'[]¡!"#$%\'()*+,:;…<=>¿?@\\/^_`’{|}~[]', '', x)
    x = x.replace(' - ', '.')
    if dot is True:
        x = x.replace(' ', '.')
        while '..' in x:
            x = x.replace('..', '.')
    else:
        while '  ' in x:
            x = x.replace('  ', ' ')
    x = x.strip()
    return x


def translate_(x, source='auto', target='en', title=True):
    # from googletrans import Translator
    # translator = Translator()
    if not x and not isinstance(x, str):
        print(f'Invalid input: {x}')
        return ''
    from deep_translator import GoogleTranslator
    try:
        x = GoogleTranslator(source=source, target=target).translate(x)
        if title:
            x = x.title()
        return x
    except Exception as e:
        print(f'Error translating {x}: {type(e).__name__}!')


def pt_lower(x):
    if x is None:
        return x
    reps = [' A ', ' À ', ' Ao ', ' Aa ', ' Às ', ' Com ', ' Da ', ' Das ', ' De ', ' Do ', ' Dos ', ' E ', ' É ', ' És ', ' Em ', ' Esta ', ' Este ', ' Me ', ' Na ', ' Nas ', ' No ', ' Nos ', ' O ', ' Os ', ' Por ', ' Qual ', ' Quais ', ' Que ', ' Se ', ' Te ', ' Ti ', ' Um ', ' Uns ',]
    for i in reps:
        if i in x:
            x = x.replace(i, i.lower())
    return x


def is_latin(x: str):
    excpt = [i for i in range(8192, 8303+1)] + [i for i in range(7680, 7935+1)]
    for i in x:
        if ord(i) in excpt:
            continue
        if ord(i) > 879:  #if not re.match(u'[\u0000-\u0400]', i)
            # print(i, ord(i))
            return False
    return True


# To treat bs4 list results
def treat_list(x):
    if x:
        return [v.text.strip() for v in x if v.text.strip()]
    return x


# To treat bs4 string results
def treat_text(x):
    if x:
        return x.text.strip()
    else:
        return None


def text_to_list(x):
    assert isinstance(x, str), f'{x} is not a string'
    if x:
        for sep in [' e ', ' - ', ' & ', '/', '|', ';']:
            x = x.replace(sep, ',')
        if ',' in x:
            x = [i.strip().title() if i.isupper() else i.strip() for i in x.split(',') if i.strip()]
        else:
            x = [x]
    return x


def lang_converter(input):
    '''
    Dynamic Language code conversion.
    '''
    import pycountry
    a = None
    if len(input) == 2:
        a = pycountry.languages.get(alpha_2=input)             # input = fr
    elif len(input) == 3:
        a = pycountry.languages.get(alpha_3=input)             # input = fra
        if not a:
            a = pycountry.languages.get(bibliographic=input)   # input = fre
    elif len(input) > 3:
        a = pycountry.languages.get(name=input)                # input = French
    if a:
        try:
            return a.bibliographic
        except AttributeError:
            return a.alpha_3


def site_is_up(url):
    '''
    Check if site is online using downforeveryoneorjustme service
    '''
    headers = {
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.6',
        'Connection': 'keep-alive',
        'Content-type': 'application/x-www-form-urlencoded',
        'Origin': 'https://downforeveryoneorjustme.com',
        'Referer': 'https://downforeveryoneorjustme.com/',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'cross-site',
        'Sec-GPC': '1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36',
        'sec-ch-ua': '"Brave";v="117", "Not;A=Brand";v="8", "Chromium";v="117"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
    }

    data = '{"commenterToken":"anonymous","domain":"downforeveryoneorjustme.com","path":"/%s"}' % url

    r = requests.post('https://commento.io/api/comment/list', headers=headers, data=data)
    rj = r.json()
    return rj['success']


def links_to_bookmark(title, links, link_prefix_a='', link_prefix_b='', output_dir='', file_name='bookmarks'):
    '''
    Must receive `links` as dict{name: link}
    or list[links] which will be converted to dict{link: link}
    '''
    assert output_dir, 'Empty outpur_dir'

    if isinstance(links, list):
        links = {x: x for x in links}

    body = []
    style = 'table, th, td { border-collapse: collapse; padding: 6px;} tr:nth-child(even) { background-color: #EEEEEE; }'

    for index, (a, b) in enumerate(links.items()):
        line = f'''<tr><td>{str(index + 1).zfill(4)}</td>
        <td><a href="{link_prefix_a + a}">{a}</a></td>
        <td><a href="{link_prefix_b + b}">{b}</a></td></tr>'''
        body.append(line)

    body = '\n'.join(body)

    output = f'''<!doctype NETSCAPE-Bookmark-file-1>
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
<title>{title}</title>
<h1>{title}</h1>
<dl><p>
<dl><p>
<style>
{style}
</style>
<table>
{body}
</table>
</dl><p>
</dl><p>'''

    html_path = pj(output_dir, f'{file_name}.html')

    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(output)
