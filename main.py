import can
from datasources import DATA_SOURCES_EXAMPLE
from logexport import *


def unique_name(message_name, signal_name):
    message_name = message_name.removeprefix('DCDC_')
    signal_name = signal_name.removeprefix('DCDC_')
    return '{}::{}'.format(message_name, signal_name)


def export_from_blf():
    source_file = '<relevant data file>'
    reader = can.BLFReader(source_file)
    dbc_file = '<relevant DBC file>'
    dbc_filter = DbcFilter(partly_accepted=DATA_SOURCES_EXAMPLE)
    export = BlfExport(dbc_file, dbc_filter, unique_name)

    for frame in reader:
        export.process_frame(frame)

    print('')
    print('> SHA256 of BLF file: {}'.format(get_sha(source_file)))
    print('> Extracted {}/{} frames based on the DBC'
          .format(export.listed_frame_count, reader.object_count))

    export.print_info()
    export.write_csv(source_file)


if __name__ == '__main__':
    export_from_blf()
