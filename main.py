import can
import cantools
import csv
from datasources import DATA_SOURCES_EXAMPLE
from logexport import *

SAMPLE_AND_HOLD = True
TARGET_CHANNEL = 0

RELATIVE_TIME = False


def unique_name(message_name, signal_name):
    message_name = message_name.removeprefix('DCDC_')
    signal_name = signal_name.removeprefix('DCDC_')
    return '{}::{}'.format(message_name, signal_name)


def export_from_blf():
    source_file = '<relevant data file>'
    reader = can.BLFReader(source_file)
    dbc_file = '<relevant dbc file>.dbc'
    dbc_filter = DbcFilter(partly_accepted=DATA_SOURCES_EXAMPLE)

    db = cantools.database.load_file(dbc_file)
    nFrames = 0
    nListedFrames = 0
    nFilteredFrames = 0
    export_rows = []
    export_fieldnames = ['timestamp']
    dot_count = 0

    channel_analyzer = ChannelAnalyzer()
    timestamp_recorder = TimestampRecorder(RELATIVE_TIME)

    for frame in reader:

        nFrames += 1

        try:
            # Find frame ID in DBC database
            msg = db.get_message_by_frame_id(frame.arbitration_id)
            nListedFrames += 1
            channel_analyzer.analyze(frame, msg)
            timestamp = timestamp_recorder.record(frame)

            # Filter by channel
            if frame.channel is not TARGET_CHANNEL:
                continue

            # Filter out non-target messages
            if not dbc_filter.is_message_accepted(msg):
                continue
            nFilteredFrames += 1
            dot_count = print_progress_dot(dot_count)

            decoded_values = msg.decode(frame.data)
            to_keep = dbc_filter.keep_accepted_signals(msg, decoded_values)
            to_write = {unique_name(msg.name, signal): value
                        for (signal, value) in to_keep.items()}

            for signal_name in to_write.keys():
                if signal_name not in export_fieldnames:
                    export_fieldnames.append(signal_name)

            to_write['timestamp'] = timestamp_recorder.format(timestamp)
            export_rows.append(to_write)

            if SAMPLE_AND_HOLD:
                sample_and_hold(export_rows)

        except KeyError:
            continue

    print('')
    print('> SHA256 of BLF file: {}'.format(get_sha(source_file)))
    print('> Extracted {}/{} frames based on the DBC'
          .format(nListedFrames, nFrames))
    print('> Time range of the frames is from {} to {}'
          .format(timestamp_recorder.min, timestamp_recorder.max))
    print('> Specified channel:', TARGET_CHANNEL)
    print('> Most likely channel:', channel_analyzer.guess_channel())
    print('> Filtered frame count:', nFilteredFrames)

    with open(source_file + '.csv', 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, delimiter=';', fieldnames=export_fieldnames)
        writer.writeheader()
        writer.writerows(export_rows)


if __name__ == '__main__':
    export_from_blf()
