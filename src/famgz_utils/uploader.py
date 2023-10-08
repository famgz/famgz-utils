import json
import os
import requests
import subprocess as sp
from bs4 import BeautifulSoup
from os.path import join as pj
from time import sleep

from .misc import run, kill_process, get_current_os_user, clean_name


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


def get_imdb_contrib(url, cookies, get_id=False):
    #  TODO  it needs a checker for page.ok, expired/no-cookies doesn't trigger error status code. maybe look for some specific element in page
    assert 'contribute.imdb.com/contribution/' in url
    headers = {
        'Connection': 'keep-alive',
        'Cache-Control': 'max-age=0',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'Sec-GPC': '1',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-User': '?1',
        'Sec-Fetch-Dest': 'document',
        'Referer': 'https://contribute.imdb.com/updates/history',
        'Accept-Language': 'en-US,en;q=0.9',
    }
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


def get_vimeo_mpd(info, headers={}):  # info might be link or id
    video_id = None
    mpd_link = None
    if 'vimeo.com' in info:
        vimeo_id = info.split('/')[-1]
    elif info.isdigit():
        vimeo_id = info
    else:
        print('Unrecognized vimeo info')
        return None
    v_page = requests.get(f"https://player.vimeo.com/video/{vimeo_id}", headers=headers)
    if v_page.status_code == 200:
        v_page = BeautifulSoup(v_page.content, 'lxml')
        v_script = v_page.find('body').find_all('script')[1]
        v_script = v_script.text
        v_data = v_script[v_script.find('var config = ') + (len('var config = ')): v_script.find('; if (!config.request)')]
        if 'master.json' not in v_data:
            print("Couldn't find json data in html's script")
            return None
        else:
            v_data = json.loads(v_data)
            mpd_link = v_data['request']['files']['dash']['cdns']['akfire_interconnect_quic']['url']
            mpd_link = mpd_link[:mpd_link.find('.json')] + '.mpd'
            return mpd_link


def open_selenium(headless=True, user_data_dir=None):
    import shlex
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service

    os_user = get_current_os_user()

    brave_path = 'C:\\Program Files\\BraveSoftware\\Brave-Browser\\Application\\brave.exe'
    user_data_dir = user_data_dir or 'C:\\chromedriver\\chrome' or f'C:\\Users\\{os_user}\\AppData\\Local\\BraveSoftware\\Brave-Browser\\User Data'

    # Setting the driver
    if headless is False:
        cmd = f'"{brave_path}" --remote-debugging-port=8888 --user-data-dir="{user_data_dir}" "about:blank"'
        # print(cmd)
        sp.Popen(shlex.split(cmd))
    opt = Options()
    opt.headless = headless
    if headless is True:
        opt.add_experimental_option('excludeSwitches', ['enable-logging'])
        opt.binary_location = brave_path
    if headless is False:
        opt.add_experimental_option("debuggerAddress", "localhost:8888")
    opt.add_argument(f'--user-data-dir="{user_data_dir}"')

    s = Service('C:\\chromedriver\\chromedriver.exe')

    driver = webdriver.Chrome(options=opt, service=s)

    return driver


def open_url(url, scroll=False, player=False, headless=True, select=None, command: str = None, user_data_dir=None):
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    def click_by_id(id_):
        driver.execute_script("arguments[0].click();", driver.find_element_by_id(id_))

    def click_by_name(name):
        driver.execute_script("arguments[0].click();", driver.find_element_by_name(name))

    def click_by_class_name(class_name):
        driver.execute_script("arguments[0].click();", driver.find_element_by_class_name(class_name))

    def net_logger():

        def save_log(x):
            x = str(x)
            with open('C:\\scope\\net_log.txt', 'a') as f:
                f.write(str(x) + '\n\n')

        driver.get(url)
        if command:
            exec(command)
        playlist_link = playlist_type = ''
        MAX_CYCLES = 500
        cycles = 0
        while True:
            net_log = driver.execute_script(
                "var performance = window.performance || window.mozPerformance || window.msPerformance ||"
                "window.webkitPerformance || {}; var network = performance.getEntries() || {}; return network;")

            # save_log(net_log)

            for item in net_log:
                # print(item)
                if '.mpd?h=' in item['name'] or 'playlist.mpd' in item['name'] or 'manifest.mpd' in item['name'] or 'master.json' in item['name'] or '.mpd' in item['name']:
                    playlist_link = item['name'].strip()
                    playlist_type = 'mpd'
                    return playlist_link

                if 'master.json' in item['name']:
                    playlist_link = item['name'].strip()
                    playlist_type = 'mpd'
                    return playlist_link

                if '.m3u8?h=' in item['name']:
                    playlist_link = item['name'].strip()
                    playlist_type = 'm3u8'
                    return playlist_link

            cycles += 1
            if cycles == MAX_CYCLES:
                cycles = 0
                driver.refresh()

    def scroller():
        roll = driver.find_element_by_tag_name('html')
        last_height = driver.execute_script("return document.body.scrollHeight")
        while True:
            for i in range(10):
                roll.send_keys(Keys.END)
                # driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    sleep(.5)
                else:
                    break
            if new_height == last_height:
                break
            last_height = new_height

    kill_process()


    '''
    brave_path = 'C:\\Program Files\\BraveSoftware\\Brave-Browser-Beta\\Application\\brave.exe'
    user_data_dir = user_data_dir or 'C:\\chromedriver\\chrome'

    # Setting the driver
    if headless is False:
        cmd = f'"{brave_path}" --remote-debugging-port=8888 --user-data-dir="{user_data_dir}"'
        print(cmd)
        sp.Popen(shlex.split(cmd))
    opt = Options()
    opt.headless = headless
    if headless is True:
        opt.add_experimental_option('excludeSwitches', ['enable-logging'])
        opt.binary_location = brave_path
    if headless is False:
        opt.add_experimental_option("debuggerAddress", "localhost:8888")
    opt.add_argument(f'--user-data-dir="{user_data_dir}"')

    s = Service('C:\\chromedriver\\chromedriver.exe')

    driver = webdriver.Chrome(options=opt, service=s)
    '''

    driver = open_selenium(headless=headless, user_data_dir=user_data_dir)

    # Starting
    if player is False:
        driver.get(url)
        sleep(1)
        if command:
            exec(command)
        if select:  # This feature applies to GLBO only
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "playkit-select__text")))
            sleep(1)
            search_season = driver.find_element_by_class_name('playkit-select__text')
            search_season.click()
            sleep(1)
            season = driver.find_element_by_xpath(f"//li[@class='playkit-select__options-item ' and text()='{select}ª Temporada']")
            season.click()
        if scroll is True:
            scroller()
        html = driver.page_source
        soup = BeautifulSoup(html, 'lxml')
        sleep(1)
        driver.close()
        driver.quit()
        kill_process()
        return soup

    elif player is True:
        data = net_logger(driver)
        sleep(1)
        driver.close()
        driver.quit()
        kill_process()
        return data
