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


def func_name(n=0):
    return sys._getframe(n + 1).f_code.co_name


def is_valid_uuid(val):
    import uuid
    try:
        uuid.UUID(str(val))
        return True
    except ValueError:
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
        print(f'[yellow]file does not exists: {file_path}{" creating it..." if create_file or new is not _null else ""}')
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


def convert_subs(file, source_dir, output_dir=''):
    '''
    Convert subtitles formats .vtt/.webvtt to .srt using Subtitle Edit.
    Will move results to 'source_dir' if 'output_dir' is not provided.
    '''
    file_path = pj(source_dir, file)
    file_base, file_ext = os.path.splitext(file)
    output_dir = output_dir or source_dir

    assert os.path.isfile(file_path), f'Invalid file path: {file_path}'
    assert os.path.isdir(output_dir), f'Invalid output directory: {output_dir}'
    assert file_ext in ('.vtt', '.webvtt'), f'Invalid vtt extension: {file}'

    file_srt = file_base + '.srt'
    if file_srt not in os.listdir(output_dir):
        run(f'SubtitleEdit /convert "{file_path}" SubRip /outputfolder:"{output_dir}"', silent=True, cmd=False)
        print(f'{file} converted')
    else:
        print(f'file {file_srt} already exists!')


def file_audio_lang(mkv_path):
    from pymediainfo import MediaInfo
    import pycountry
    mi = MediaInfo.parse(mkv_path)
    # check is there is audio
    if len(mi.audio_tracks) > 0:
        audio_lang = mi.audio_tracks[0].language
        # check if lang is not 'und'
        if audio_lang is not None:
            try:
                audio_lang = pycountry.languages.get(alpha_2=audio_lang).name
                return audio_lang
            except AttributeError:
                return audio_lang
    else:
        print(f'No audio tracks found in {mkv_path}')
        return None


def file_length(mkv_path, min_format=True, round_=True):
    from pymediainfo import MediaInfo
    if min_format is False:
        min_format = 1
    else:
        min_format = 60
    media_info = MediaInfo.parse(mkv_path)
    length = (media_info.general_tracks[0].duration / 1000) / min_format
    if round_ is True:
        length = round(length)
    return length


def video_res(mkv_path):
    '''
    Returns ''(SD), 720p, 1080p
    '''
    res = ''
    from pymediainfo import MediaInfo
    media_info = MediaInfo.parse(mkv_path)
    width = media_info.video_tracks[0].width
    height = media_info.video_tracks[0].height

    if (height == 720 and width < 1920) or (width == 1280 and height < 1080):
        res = '720p'
    if height == 1080 or width == 1920:
        res = '1080p'
    resolution = f'{width} x {height}'
    return res


def get_mkv_name(data={}, original_title='', year='', title_eng='', director='', extra='', res=None, mkv_path=None):
    # check data dict
    if data:
        if isinstance(data, dict):
            original_title = data['original_title']
            year = data['year']
            if 'title_eng' in data:
                title_eng = data['title_eng']
            if 'directors' in data:
                director = data['directors']
        else:
            print('[get_mkv_name] data is not a dict')
    # check crucial items
    if not original_title:
        if not title_eng:
            raise ValueError('[get_mkv_name] no title was given')
        else:
            original_title = title_eng
    if not year:
        raise ValueError('[get_mkv_name] year is missing')
    year = str(year)
    # treating entries
    original_title = clean_name(original_title)
    if title_eng is None:
        title_eng = ''
    else:
        title_eng = clean_name(title_eng)
    if director is None:
        director = ''
    else:
        if isinstance(director, list):
            director = director[0]
        director = clean_name(director)
    # making conditions
    if len(original_title) > 30:
        title_eng = ''
        director = ''
    if len(original_title) > 7:
        director = ''
    if len(original_title + '.AKA.' + title_eng) > 60:
        title_eng = ''
    if title_eng:
        if clean_name(original_title).lower() == clean_name(title_eng).lower():
            title_eng = ''
        else:
            title_eng = f'.AKA.{clean_name(title_eng)}'
    if title_eng:
        director = ''
    if director:  # redundant
        title_eng = ''
    # checking res
    if res is None:
        if mkv_path is None:
            raise ValueError('[get_mkv_name] res and mkv_path are missing')
        elif not os.path.isfile(mkv_path):
            raise ValueError('[get_mkv_name] res missing and mkv_path is invalid')
        res = video_res(mkv_path)
    mkv_name = '.'.join([original_title, title_eng, year, director, extra, res, 'WEB-DL.x264-gooz'])
    while '..' in mkv_name:
        mkv_name = mkv_name.replace('..', '.')
    return mkv_name


def get_image_info(img_url, ar=True):
    import urllib
    from PIL import ImageFile

    file = urllib.request.urlopen(img_url)
    size = file.headers.get("content-length")
    if size:
        size = int(size)
    p = ImageFile.Parser()
    # while True:
    data = file.read(1024)
    file.close()
    if not data:
        return None
    p.feed(data)
    if p.image:
        if ar is True:
            w = p.image.size[0]
            h = p.image.size[1]
            ar = h / w
            return ar
        if ar is False:
            return size, p.image.size


def check_imdb_poster(imdb_id):
    if imdb_id:
        from imdb import Cinemagoer as IMDb
        ia = IMDb()
        movie = ia.get_movie(imdb_id.replace('tt', ''))
        imdb_link = '[imdb_poster] https://www.imdb.com/title/' + imdb_id
        print(imdb_link)
        if 'full-size cover url' not in movie.keys():
            print("[imdb_poster] Poster url not found")
            input('[imdb_poster] Press any key\n>')
        else:
            img_url = movie['full-size cover url']
            scaled_img_url = img_url  #.replace('.jpg', '._V1_FMjpg_UY1200_.jpg')
            ar = get_image_info(scaled_img_url, ar=True)
            if ar:
                if ar > 1:
                    print('[imdb_poster] Poster ok')
                elif ar <= 1:
                    print(f"[imdb_poster] Image has bad ratio:\n{scaled_img_url}")
                    input('[imdb_poster] Press any key\n>')
            else:
                print("[imdb_poster] Can't access image info")
                input('[imdb_poster] Press any key\n>')


def get_true_imdbid(old_id):
    from imdb import Cinemagoer as IMDb
    ia = IMDb()
    movie = ia.get_movie(old_id.replace('tt',''))
    new_id = 'tt' + movie['imdbID']
    if new_id != old_id:
        print(f'New id found: {old_id} -> {new_id}')
    return new_id


def get_imdb_contrib(url, get_id=False):
    #  TODO  it needs a checker for page.ok, expired/no-cookies doesn't trigger error status code. maybe look for some specific element in page
    assert 'contribute.imdb.com/contribution/' in url
    cookies = {'session-id': '137-0617204-1791744', 'ubid-main': '130-1879247-1404368', 'adblk': 'adblk_no', 'x-main': 'bn9n48jaiSKTzSdWlhEIj9p4Fq3nQvfUaBfQHEdhi2vJl1nunyjn24jGrDrBa6DD', 'at-main': 'Atza|IwEBIDI6Df_TVTrJGKiZ_rhKBXiFufMSL2Y9zZ3zZJyTcUljqtiDWhuM9d3HVz8UCfbtAIkmrxb-3ahuzE9KGKLtJ0ZSfaBtl6H-w7QImflNVcgeAQDo0WDBu8oKVaeNfeKNsSr3BpWFl1VKU-nM1y3TZeyr-cZjHw_0Df2IxlP96SvExQzHFcntZyCpgx0waJuhudK-5SeD8ERgxs0YetorLE73kljVjgzpV0lT09HZmT_k3g', 'sess-at-main': 'VDfcNlEIHwuCtU0VaMZrhcc7yabkt1G1YASMKDK5Sqw=', 'uu': 'eyJpZCI6InV1OWUzMjFhMjk3YzNhNDJkMzk1NjYiLCJwcmVmZXJlbmNlcyI6eyJmaW5kX2luY2x1ZGVfYWR1bHQiOmZhbHNlfSwidWMiOiJ1cjI1ODMxMDU1In0=', 'lc-main': 'en_US', 'session-id-time': '2082787201l', 'as': '%7B%22n%22%3A%7B%7D%7D', 'session-token': 'hXap8zoQ/3Pqqpyb+O1KqeigX4eBmPyVwrj2wcMjGiX2Yx2uaQ6ikEheB7zomHFe4Bb1InSS9Rg2WDIdPG51KBPbdKhRl4SJzALoHinoycV6IsIUeNtk+FBHA6DxZ1ZuB2gSPj8FQgWnBsr/yuLPqGwYJMOyt8eQRcUEfS+Wf68lnj27r14gG8JFGwzKvFYItwlMFllMDXW6cbpvimUz1Q', 'csm-hit': 'adb:adblk_no&t:1644422373329&tb:BB780JKMVVY7EGFB29JV+s-BB780JKMVVY7EGFB29JV|1644422373329', }
    headers = {'Connection': 'keep-alive', 'Cache-Control': 'max-age=0', 'Upgrade-Insecure-Requests': '1', 'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36', 'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9', 'Sec-GPC': '1', 'Sec-Fetch-Site': 'same-origin', 'Sec-Fetch-Mode': 'navigate', 'Sec-Fetch-User': '?1', 'Sec-Fetch-Dest': 'document', 'Referer': 'https://contribute.imdb.com/updates/history', 'Accept-Language': 'en-US,en;q=0.9',}
    r = requests.get(url, cookies=cookies, headers=headers)
    assert r.ok  # it doesn't matter
    page = BeautifulSoup(r.content, 'lxml')
    imdb_link = page.select_one('a.a-size-large.a-link-normal')
    if imdb_link:
        imdb_link = imdb_link['href']
        assert 'title/' in imdb_link
        if get_id is True:
            imdb_id = imdb_link.split('/')[-1]
            return imdb_id
        else:
            imdb_link = 'https://www.imdb.com' + imdb_link
            return imdb_link


def clean_imdb_link(imdb_link):
    if len(imdb_link.split('/')) == 6:
        garbage = imdb_link.split('/')[-1]
        if garbage:
            imdb_link = imdb_link.replace(garbage, '')
    return imdb_link


def screenshots(mkv_path, folder_path, manual_select=True):
    from pymediainfo import MediaInfo
    import numpy as np

    if '.mkv' not in mkv_path[-4:]:
        mkv_path += '.mkv'

    mkv_name = mkv_path.split('\\')[-1].split('/')[-1].replace('.mkv','')

    media_info = MediaInfo.parse(mkv_path)

    MAX_SCREENS = 70
    MIN_SCREENS = 20
    INIT_RATE = 0.05
    END_RATE = 0.2
    DIV_RATE = 80  # seconds

    total_sec = round(media_info.general_tracks[0].duration / 1000)  # convert ms to s

    first = round(total_sec * INIT_RATE)
    last = round(total_sec - (total_sec * END_RATE))
    total_screens = round((last - first) / DIV_RATE)
    if manual_select is False:
        total_screens = 8
    else:
        if total_screens > MAX_SCREENS:
            total_screens = MAX_SCREENS
        elif total_screens < MIN_SCREENS:
            total_screens = MIN_SCREENS

    frames = list(np.linspace(first, last, num=total_screens, dtype=int))

    for index, frame in enumerate(frames):
        # command = f'ffmpeg -hide_banner -loglevel warning -ss {frame} -i "{mkv_path}" -vf scale=iw*sar:ih -frames:v 1 -q:v 2 "{pj(folder_path, "screens", mkv_name + "_" + str(index+1) + ".png")}"'
        print(f'\rscreenshot # {index+1}/{len(frames)})', end='')
        command = f'ffmpeg -hide_banner -loglevel warning -ss {frame} -i "{mkv_path}" -vf scale=iw*sar:ih -frames:v 1 -q:v 2 "{folder_path}\\screens\\{frame}.png"'
        run(command, silent=False)


def site_is_up(url):
    '''
    Check if site is online using downforeveryoneorjustme service
    '''
    cookies = {'cf_clearance': '9UNIAbATmu8E71lwcyv1bPmCJZvXxm7Bv.tHVHp2dgE-1661526441-0-150', }
    headers = {
        'authority': 'downforeveryoneorjustme.com',
        'accept': '*/*',
        'accept-language': 'en-US,en;q=0.9',
        # 'cookie': 'cf_clearance=9UNIAbATmu8E71lwcyv1bPmCJZvXxm7Bv.tHVHp2dgE-1661526441-0-150',
        # 'referer': f'https://downforeveryoneorjustme.com/columbiainvepar.com.br?proto=https&www=1',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'sec-gpc': '1',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.5060.134 Safari/537.36',
    }
    r = requests.get(f'https://downforeveryoneorjustme.com/api/httpcheck/{url}', cookies=cookies, headers=headers)
    rj = r.json()
    return rj['statusText'] == 'OK'


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
