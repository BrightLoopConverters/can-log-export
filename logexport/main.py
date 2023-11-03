import can
from helpers_dchv import *
from logexport import *


def export_from_blf():
    source_file = '../data/<relevant BLF data filename>.blf'
    print('> SHA256 of log file: {}'.format(get_sha(source_file)))
    reader = can.BLFReader(source_file)
    dbc_file = '../dbc/<relevant DBC filename>.dbc'
    dbc_filter = DbcFilter(accept_all=True)

    export = LogExport(dbc_file, dbc_filter,
                       signal_renamer=dchv_shortname,
                       expected_frame_count=reader.object_count,
                       use_sample_and_hold=False)
    for frame in reader:
        export.process_frame(frame)

    export.print_info()
    export.write_csv(source_file)


def export_from_trc():
    source_file = '../data/<relevant TRC data filename>.trc'
    print('> SHA256 of log file: {}'.format(get_sha(source_file)))
    reader = can.TRCReader(source_file)
    dbc_file = '../dbc/<relevant DBC filename>.dbc'
    dbc_filter = DbcFilter(accept_all=True)

    export = LogExport(dbc_file, dbc_filter,
                       signal_renamer=dchv_shortname,
                       target_channel=1,
                       expected_frame_count=count_lines(source_file))

    for frame in reader:
        export.process_frame(frame, allow_truncated=True)

    export.print_info()
    export.write_csv(source_file)


def export_from_asc():
    source_file = '../data/<relevant ASC data filename>.asc'
    print('> SHA256 of log file: {}'.format(get_sha(source_file)))
    reader = can.ASCReader(source_file)

    dbc_file = '../dbc/<relevant DBC filename>.dbc'
    dbc_filter = DbcFilter(accept_all=True)

    export = LogExport(dbc_file, dbc_filter,
                       signal_renamer=dchv_shortname,
                       target_channel=0,
                       expected_frame_count=count_lines(source_file))

    for frame in reader:
        export.process_frame(frame, allow_truncated=True)

    export.print_info()
    export.write_csv(source_file)


if __name__ == '__main__':
    export_from_asc()
