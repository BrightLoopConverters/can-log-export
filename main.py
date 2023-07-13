import can
import cantools
import hashlib
from datetime import datetime
import csv

SAMPLE_AND_HOLD = True
TARGET_CHANNEL = 0

ACCEPT_ALL_DATA_SOURCES = False

DATA_SOURCES = {
    'MESSAGE_1': [
        'PARAM_1_x',
        'PARAM_1_y',
        'PARAM_1_z'
    ],
    'MESSAGE_2': [
        'PARAM_2_x',
        'PARAM_2_y',
        'PARAM_2_z'
    ]
}

class ChannelAnalyzer:
    def __init__(self):
        self.mismatch_counts = {}
        self.mismatch_values = {}
        self.frame_counts = {}

    def update_dlc_mismatch(self, frame, msg):
        if frame.dlc is not msg.length:
            if frame.channel not in self.mismatch_counts:
                self.mismatch_counts[frame.channel] = 0
            self.mismatch_counts[frame.channel] += 1

        if msg.name not in self.mismatch_values:
            self.mismatch_values[msg.name] = {}
        if frame.channel not in self.mismatch_values[msg.name]:
            self.mismatch_values[msg.name][frame.channel] = []
        if frame.dlc not in self.mismatch_values[msg.name][frame.channel]:
            self.mismatch_values[msg.name][frame.channel].append(frame.dlc)

    def update_channel_count(self, frame):
        if frame.channel not in self.frame_counts:
            self.frame_counts[frame.channel] = 0
        self.frame_counts[frame.channel] += 1

    def guess_channel(self):
        for channel in self.frame_counts:
            if channel not in self.mismatch_counts:
                return channel

    def analyze(self, frame, msg):
        self.update_channel_count(frame)
        self.update_dlc_mismatch(frame, msg)


def unique_name(message_name, signal_name):
    message_name = message_name.removeprefix('DCDC_')
    signal_name = signal_name.removeprefix('DCDC_')
    return '{}::{}'.format(message_name, signal_name)

def accept_message(message):
    desired_message_names = DATA_SOURCES.keys()
    return (message.name in desired_message_names) or ACCEPT_ALL_DATA_SOURCES


def filter_signals(message, signals):
    extracted_signals = {}
    desired_signal_names = {}

    if ACCEPT_ALL_DATA_SOURCES:
        desired_signal_names = signals
    else:
        if message.name in DATA_SOURCES:
            desired_signal_names = DATA_SOURCES[message.name]

    for signal_name in desired_signal_names:
        value = signals[signal_name]
        extracted_signals[unique_name(message.name, signal_name)] = value

    return extracted_signals


def get_sha(filename):
    sha256_hash = hashlib.sha256()
    with open(filename, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


if __name__ == '__main__':
    blf_file = '<relevant filename>.blf'

    db = cantools.database.load_file('<relevant filename>.dbc')

    nFrames = 0
    nListedFrames = 0
    nFilteredFrames = 0

    minTimestamp = None
    maxTimestamp = None

    export_rows = []
    export_fieldnames = ['timestamp']

    dotCount = 0

    with can.BLFReader(blf_file) as reader:
        channel_analyzer = ChannelAnalyzer()
        for frame in reader:

            nFrames += 1

            try:
                # Find frame ID in DBC database
                msg = db.get_message_by_frame_id(frame.arbitration_id)
                nListedFrames += 1

                channel_analyzer.analyze(frame, msg)

                # Update timestamp range
                timestamp = datetime.fromtimestamp(frame.timestamp).time()

                if minTimestamp is None or timestamp < minTimestamp:
                    minTimestamp = timestamp

                if maxTimestamp is None or timestamp > maxTimestamp:
                    maxTimestamp = timestamp

                # Filter by channel
                if frame.channel is not TARGET_CHANNEL:
                    continue

                # Filter out non-target messages
                if not accept_message(msg):
                    continue
                nFilteredFrames += 1
                dotCount += 1
                if dotCount > 80:
                    print('.')
                    dotCount = 0
                else:
                    print('.', end='')

                decoded_data = msg.decode(frame.data)
                filtered_signals = filter_signals(msg, decoded_data)

                for signal_name in filtered_signals.keys():
                    if signal_name not in export_fieldnames:
                        export_fieldnames.append(signal_name)

                filtered_signals['timestamp'] = datetime.fromtimestamp(frame.timestamp)
                export_rows.append(filtered_signals)

                if SAMPLE_AND_HOLD:
                    for key in export_fieldnames:
                        if key not in filtered_signals and len(export_rows) > 1:
                            prev = ''
                            if key in export_rows[-2]:
                                previous_value = export_rows[-2][key]
                                export_rows[-1][key] = previous_value

            except KeyError:
                continue

        print('')
        print('> SHA256 of BLF file: {}'.format(get_sha(blf_file)))
        print('> Extracted {}/{} frames based on the DBC'
              .format(nListedFrames, nFrames))
        print('> Time range of the frames is from {} to {}'
              .format(minTimestamp, maxTimestamp))
        print('> Specified channel:', TARGET_CHANNEL)
        print('> Most likely channel:', channel_analyzer.guess_channel())
        print('> Filtered frame count:', nFilteredFrames)

        with open(blf_file + '.csv', 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, delimiter=';', fieldnames=export_fieldnames)
            writer.writeheader()
            writer.writerows(export_rows)
