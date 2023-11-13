import can
from helpers_dchv import *
from logexport import *

if __name__ == '__main__':
    data_file = '../data/<relevant data filename>'

    print('> SHA256 of log file: {}'.format(get_sha(data_file)))

    dbc_file = '../dbc/<relevant DBC filename>.dbc'
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
                       target_channel=0,
                       expected_frame_count=count,
                       use_sample_and_hold=False)

    reader = reader_init(data_file)
    for frame in reader:
        export.process_frame(frame, allow_truncated=True)

    export.print_info()
    export.write_csv(data_file)
