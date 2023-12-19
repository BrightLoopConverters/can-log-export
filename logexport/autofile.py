import os
import time
from pathlib import Path


def guess_data_file(dirpath):
    files = possible_files(dirpath, is_possible_data_file)
    files = sorted(files, key=os.path.getctime, reverse=True)
    result = files[0] if files else None

    print(f'> Selecting data file automatically: found {len(files)} candidates in {dirpath}')

    if result:
        timestr = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(result.stat().st_ctime))
        print(f'> Most recent data file: {result.name} (created: {timestr})')

    return result


def guess_dbc_file(dirpath):
    files = possible_files(dirpath, is_possible_dbc_file)
    files = sorted(files, key=os.path.getmtime, reverse=True)
    result = files[0]

    print(f'> Selecting DBC file automatically: found {len(files)} candidates in {dirpath}')
    timestr = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(result.stat().st_ctime))
    print(f'> Most recent DBC file: {result.name} (created: {timestr})')
    return result


def possible_files(dirpath, possible_file_test):
    paths = Path(dirpath).iterdir()
    files = []
    dirs = []
    for p in paths:
        if p.is_dir():
            dirs.append(p)
        elif possible_file_test(p):
            files.append(p)

    # Recursion
    for d in dirs:
        nested_files = possible_files(d, possible_file_test)
        files.extend(nested_files)

    return files


def is_possible_data_file(p):
    # Retain files that are neither zip nor .gitignore
    return p.is_file() and p.suffix != '.zip' and p.suffix != '.csv' and not p.stem.startswith('.')


def is_possible_dbc_file(p):
    return p.is_file and p.suffix == '.dbc'
