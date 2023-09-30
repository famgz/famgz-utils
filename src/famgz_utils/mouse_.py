import json
import keyboard
import mouse
import os
import os.path as p
from mouse import MoveEvent
from os.path import join as pj
from pathlib import Path
from timeit import default_timer as timer

from .time_ import countdown, timeit, f_time
from .misc import json_, print

source_dir = Path(__file__).resolve().parent
mm_dir = pj(source_dir, 'mouse_movements')


def save_in_json(events):
    for i in range(1, 1001):
        i = str(i).zfill(3)
        path = pj(mm_dir, f'{i}.json')
        if not p.isfile(path):
            with open(path, 'w') as f:
                json.dump(events, f)
                print(f'[green]Succesfully writen: {path}!')
                return


def record_mouse_event():
    print('\n[white]Starting recording in...')
    countdown(3)
    print('\n\nMake some mouse movements then press `a`.')

    events = []                  # This is the list where all the events will be stored
    mouse.hook(events.append)    # starting the recording
    keyboard.wait("a")           # Waiting for `a` to be pressed
    mouse.unhook(events.append)  # Stopping the recording

    if events:
        print(len(events), 'events')
        save_in_json(events)
        mouse.play(events, speed_factor=1.2)


# @timeit
def load_mouse_event(n=1, max_dur=None):
    '''
    Emulates a mouse movement loading a random set of saved events.
    Max duration is an aproximation.
    '''
    from random import choice, randint
    files = [file for file in os.listdir(mm_dir) if file.endswith('.json')]
    for _ in range(n):
        file = choice(files)
        path = pj(mm_dir, file)
        assert p.isfile(path)
        raw_events = json_(path)
        offset = randint(0, 10)

        first_t, last_t = raw_events[0][2], raw_events[-1][2]
        # raw_duration = last_t - first_t

        events = [MoveEvent(x+offset, y+offset, t) for (x, y, t) in raw_events if not max_dur or (max_dur and t - first_t < max_dur)]

        # t1 = timer()
        mouse.play(events, speed_factor=1.2)  # 1.2 speed shows less difference between raw and live duration
        # t2 = timer() -t1

        # print('\n\nraw duration', raw_duration)
        # print('live duration', t2)
        # print('diff', t2 - raw_duration)


if __name__ == '__main__':
    while True:
        os.system('cls')
        record_mouse_event()
