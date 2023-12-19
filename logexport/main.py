from helpers_dchv import *
from logexport import *
from time import perf_counter
from autofile import *
from pathlib import Path

AUTO_DATA_FILE = True
DATA_DIR = '../data/'
DATA_FILE = None

AUTO_DBC_FILE = True
DBC_DIR = '../dbc/'
DBC_FILE = None

if __name__ == '__main__':
    if AUTO_DATA_FILE:
        data_file = str(guess_data_file(DATA_DIR))
    elif DATA_FILE is not None:
        data_file = str(Path(DATA_DIR, DATA_FILE))
    else:
        print('> No data file specified via DATA_FILE for manual selection')
        exit()

    print(f'> Data file selected for processing: {data_file}')
    print('> SHA256 of data file: {}'.format(get_sha(data_file)))

    if AUTO_DBC_FILE:
        dbc_file = guess_dbc_file(DBC_DIR)
    elif DBC_FILE is not None:
        dbc_file = Path(DBC_DIR, DBC_FILE)
    else:
        print('> No DBC file specified via DBC_FILE for manual selection')
        exit()

    print(f'> DBC file selected to decode CAN frames: {dbc_file}')

    dbc_filter = DbcFilter(accept_all=True)

    reader_init = None

    if reader_init is None:
        [reader_init, count] = try_decode_asc(data_file)
    if reader_init is None:
        [reader_init, count] = try_decode_blf(data_file)
    if reader_init is None:
        [reader_init, count] = try_decode_trc(data_file)
    if reader_init is None:
        raise ValueError('Could not decode provided log file')

    export = LogExport(dbc_file, dbc_filter,
                       signal_renamer=dchv_shortname,
                       use_time_grouping=True,
                       target_channel=AutoChannel,
                       expected_frame_count=count,
                       use_sample_and_hold=False)

    time_start = perf_counter()
    reader = reader_init(data_file)
    for frame in reader:
        export.process_frame(frame, allow_truncated=True)
    time_stop = perf_counter()

    export.print_info()
    print(f'> Elapsed time: {round(time_stop - time_start)}s')
    export.write_csv(data_file)
