from helpers_dchv import *
from logexport import *
from time import perf_counter
from autofile import *
from pathlib import Path

AUTO_DATA_FILE = True
DATA_DIR = '../data/'
DATA_FILE = ''

AUTO_DBC_FILE = True
DBC_DIR = '../dbc/'
DBC_FILE = ''

OUTPUT_DIR = '../output/'


def run():
    if AUTO_DATA_FILE:
        data_file = guess_data_file(DATA_DIR)
    elif DATA_FILE:
        data_file = Path(DATA_DIR, DATA_FILE)
    else:
        print('> No data file specified via DATA_FILE for manual selection')
        return

    print(f'> Data file selected for processing: {data_file}')
    if not data_file:
        return

    print('> SHA256 of data file: {}'.format(get_sha(data_file)))

    if AUTO_DBC_FILE:
        dbc_file = guess_dbc_file(DBC_DIR)
    elif DBC_FILE:
        dbc_file = Path(DBC_DIR, DBC_FILE)
    else:
        print('> No DBC file specified via DBC_FILE for manual selection')
        return

    print(f'> DBC file selected to decode CAN frames: {dbc_file}')
    if not dbc_file:
        return

    dbc_filter = DbcFilter(accept_all=True)

    reader_init = None
    count = 0

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
    output_file = export.write_csv(OUTPUT_DIR, str(data_file))

    if output_file:
        report_path = Path(OUTPUT_DIR, 'report.txt')
        with open(report_path, 'w') as report:
            report.write(output_file)

    export.write_signals_json(OUTPUT_DIR,'exported_signals.json')
    export.write_crc_report(OUTPUT_DIR, 'crc_report.json')
    export.frame_listeners[0].write_report(OUTPUT_DIR, 'mux_report.json')
    export.frame_listeners[1].write_report(OUTPUT_DIR, 'rolling_counter_report.json')


if __name__ == '__main__':
    run()
