import os
import time
from pathlib import Path


def guess_data_file(dirpath):
    files = possible_data_files(dirpath)
    files = sorted(files, key=os.path.getmtime, reverse=True)
    data_file = files[0]

    print(f'> Selecting data file automatically: found {len(files)} candidates in {dirpath}')
    timestr = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(data_file.stat().st_mtime))
    print(f'> Most recent data file: {data_file.name} (last modified: {timestr})')
    return data_file

def possible_data_files(dirpath):
    paths = Path(dirpath).iterdir()
    files = []
    dirs = []
    for p in paths:
        if p.is_dir():
            dirs.append(p)
        # Retain files that are neither zip nor .gitignore
        elif p.is_file() and p.suffix != '.zip' and p.suffix != '.csv' and not p.stem.startswith('.'):
            files.append(p)

    # Recursion
    for d in dirs:
        nested_files = possible_data_files(d)
        files.extend(nested_files)

    return files