import can
from datasources import DATA_SOURCES_EXAMPLE
from logexport import *


def unique_name(message_name, signal_name):
    message_name = message_name.removeprefix('DCDC_')
    signal_name = signal_name.removeprefix('DCDC_')
    return '{}::{}'.format(message_name, signal_name)


def export_from_blf():
    source_file = '<relevant BLF data file>'
    print('> SHA256 of log file: {}'.format(get_sha(source_file)))
    reader = can.BLFReader(source_file)
    dbc_file = '<relevant DBC file>'
    dbc_filter = DbcFilter(partly_accepted=DATA_SOURCES_EXAMPLE)

    export = LogExport(dbc_file, dbc_filter, unique_name,
                       expected_frame_count=reader.object_count)
    for frame in reader:
        export.process_frame(frame)

    export.print_info()
    export.write_csv(source_file)


def export_from_trc():
    source_file = '<relevant TRC data file>'
    print('> SHA256 of log file: {}'.format(get_sha(source_file)))
    reader = can.TRCReader(source_file)
    dbc_file = '<relevant DBC file>'
    dbc_filter = DbcFilter(accept_all=True)

    export = LogExport(dbc_file, dbc_filter, target_channel=1,
                       expected_frame_count=count_lines(source_file))
    for frame in reader:
        export.process_frame(frame, allow_truncated=True)

    export.print_info()
    export.write_csv(source_file)


if __name__ == '__main__':
    export_from_trc()
