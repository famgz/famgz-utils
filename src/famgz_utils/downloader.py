import os
from os import path as p
from os.path import join as pj
from pathlib import Path
from time import sleep

from .misc import run, print, is_valid_uuid

try:
    [mkv_tag_path] = [x for x in Path(__file__).resolve().parent.iterdir() if x.name == 'mkv_tag.xml']
except ValueError:
    mkv_tag_path = ''

# debug options
QUIET_DOWNLOAD = True
QUIET_DECRYPT = True
QUIET_REMUX = True


def downloader(
        OUTPUT_DIR,
        WORKING_DIR,
        slug,
        mpd_link,
        wvkey=None,
        audio_lang=None,
        audio_name='',
        max_res=720,
        kid_audio=1,
        kid_video=1,
        delete_raw=True,
        check_url=True,
        debug=False
    ) -> bool:

    '''
    Script to download both encrypted or unencrypted video sources based on whether `wvkey` is given
    The actual file downloader relies on having yt-dlp installed and on PATH
    '''

    def file_already_exists():
        file_name = slug + '.mkv'
        if file_name in os.listdir(OUTPUT_DIR):
            print(f'[green]File {file_name} already found!')
            return True
        return False

    def check_wvkey():
        # won't interrupt execution, only flag a message
        if wvkey:
            return False
        print(f'[yellow]warning, invalid wvkey: {wvkey}')
        return is_valid_uuid(wvkey)

    def req_url(url):
        import requests
        headers = {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.83 Safari/537.36',
            'accept': '*/*',
        }
        r = requests.get(url, headers=headers)
        return r

    def bad_url():
        if not check_url:
            return False
        r = req_url(mpd_link)
        if r.ok:
            return False
        print(f'[black on yellow] Invalid or unavailable url: \n[bright_magenta]{mpd_link}[/]\nstatus: <{r.status_code}>')
        sleep(0.5)
        return True

    def get_subs_command():
        global ALLSUBS
        all_subs = ''
        clean_slug = slug.split('.')[0]
        if os.path.exists(pj(OUTPUT_DIR, 'subs')):
            for file in os.listdir(pj(OUTPUT_DIR, 'subs')):
                if file.startswith(clean_slug + '.') and file.endswith('.srt'):
                    lang = file.split('.')[-2]
                    def_track = 'no'
                    if lang in ['eng', 'por']:
                        def_track = 'yes'
                    all_subs = f'''{all_subs} --language 0:{lang} --default-track 0:{def_track} "{pj(OUTPUT_DIR, 'subs', file)}"'''
            all_subs = all_subs.strip()
        ALLSUBS = all_subs

    def download():
        print("[white]> downloading source files")
        drm = '--allow-unplayable-formats --keep-video ' if wvkey else ''
        run(
            silent=QUIET_DOWNLOAD,
            command=f'yt-dlp '
                     '--retries 10 '
                     '--fragment-retries 10 '
                     '--abort-on-error '
                     '--fixup never '
                     '--downloader aria2c '
                     '--downloader-args aria2c:'
                     '--disable-ipv6=true '
                     '--allow-unplayable-formats '
                     '--no-check-certificates '
                    f'{drm}-f bestvideo[height<={max_res}]+bestaudio[acodec!=opus] '
                    f'"{mpd_link}" '
                    f'-o "{slug}" '
                    f'-P "{WORKING_DIR}"'
        )
        video = [x for x in WORKING_DIR.iterdir() if x.name.startswith(slug) and x.suffix == '.mp4']
        audio = [x for x in WORKING_DIR.iterdir() if x.name.startswith(slug) and x.suffix == '.m4a']
        assert video and audio, 'ERROR downloading source files'

    def decrypt():
        if not wvkey:
            return
        print('[white]> decrypting')
        global raw_video_path
        global raw_audio_path
        paths = WORKING_DIR.iterdir()
        files = lambda: os.listdir(WORKING_DIR)
        for file in paths:
            # Decrypt raw video
            if file.name.startswith(slug) and file.suffix == '.mp4':
                if 'vdec' not in files():
                    print('[bright_black]  video')
                    command = f'''mp4decrypt --key {kid_video}:{wvkey} "{file}" "{Path(WORKING_DIR, 'vdec')}"'''
                    run(command, silent=QUIET_DECRYPT)
                else:
                    print('[bright_black]  vdec already exists')
                raw_video_path = file

            # Decrypt raw audio
            elif file.name.startswith(slug) and file.suffix == '.m4a':
                if 'adec' not in files():
                    print('[bright_black]  audio')
                    command = f'''mp4decrypt --key {kid_audio}:{wvkey} "{file}" "{Path(WORKING_DIR, 'adec')}"'''
                    run(command, silent=QUIET_DECRYPT)
                else:
                    print('[bright_black]  adec already exists')
                raw_audio_path = file

        assert 'vdec' in files(), '[black on yellow] ERROR decrypting: vdec file not found! '
        assert 'adec' in files(), '[black on yellow] ERROR decrypting: adec file not found! '

    def set_languages():
        nonlocal audio_name
        nonlocal audio_lang
        global single_mp4
        global source
        audio_lang = audio_lang or 'und'
        source = adec = vdec = ''

        # set data for decrypted files
        if wvkey:
            if 'adec' in os.listdir(WORKING_DIR):
                if audio_name:
                    audio_name = f'--track-name 0:"{audio_name}" '
                adec = f'''--language 0:{audio_lang} {audio_name}"{pj(WORKING_DIR, 'adec')}"'''
            if 'vdec' in os.listdir(WORKING_DIR):
                vdec = f'''--language 0:und "{pj(WORKING_DIR, 'vdec')}"'''
            source = f'{vdec} {adec}'

        # set data for single mp4
        else:
            single_mp4 = [x for x in os.listdir(WORKING_DIR) if x.endswith('mp4')][0]
            single_mp4 = pj(WORKING_DIR, single_mp4)
            if audio_name:
                audio_name = f'--track-name 1:"{audio_name}" '
            source = f'--language 0:und --language 1:{audio_lang} {audio_name}"{single_mp4}" --track-order 0:0,0:1'

    def get_global_tag():
        return f'--global-tags "{str(mkv_tag_path)}"' if mkv_tag_path else ''

    def remux():
        print('[white]> remuxing')
        items = [x for x in ['mkvmerge -q', '--output', f'''"{pj(OUTPUT_DIR, slug + '.mkv')}"''', source, get_global_tag(), ALLSUBS] if x]
        mkv_command = ' '.join(items)
        run(mkv_command, silent=QUIET_REMUX)
        assert (slug + '.mkv') in os.listdir(OUTPUT_DIR), f'[black on yellow] ERROR remuxing: {slug}.mkv not found! '

    def delete_raw_files():
        if not delete_raw:
            return
        print('[white]> deleting raw files')
        if wvkey:
            for file_path in (
                raw_video_path,
                raw_audio_path,
                pj(WORKING_DIR, 'vdec'),
                pj(WORKING_DIR, 'adec')
            ):
                if p.isfile(file_path):
                    os.remove(file_path)
        else:
            os.remove(single_mp4)

    WORKING_DIR = Path(WORKING_DIR)
    OUTPUT_DIR  = Path(OUTPUT_DIR)

    print(f'\n[bold red]{slug}[/bold red]')

    if file_already_exists():
        return True

    if bad_url():
        return False

    if debug:
        global QUIET_DOWNLOAD
        global QUIET_DECRYPT
        global QUIET_REMUX
        QUIET_DOWNLOAD = False
        QUIET_DECRYPT = False
        QUIET_REMUX = False

    check_wvkey()

    print(f'[white]link: [bright_black]{mpd_link}')
    print(f'[white]wvkey: [bright_black]{wvkey}')

    download()

    decrypt()

    get_subs_command()

    set_languages()

    remux()

    delete_raw_files()

    print('[bright_green]done!')

    return True
