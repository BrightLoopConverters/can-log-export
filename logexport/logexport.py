import hashlib
from datetime import datetime
import cantools
from cantools import database
import csv
import sys
from tqdm import tqdm


def get_sha(filename):
    sha256_hash = hashlib.sha256()
    with open(filename, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def count_lines(file):
    with open(file, "rbU") as f:
        num_lines = sum(1 for _ in f)
    return num_lines


def sample_and_hold(rows):
    if len(rows) > 1:
        for key in rows[-2]:
            if key not in rows[-1]:
                rows[-1][key] = rows[-2][key]


class TimestampRecorder:
    def __init__(self, relative):
        self.min = None
        self.max = None
        self.relative = relative

    def record(self, frame):
        timestamp = datetime.fromtimestamp(frame.timestamp)
        if self.min is None or timestamp < self.min:
            self.min = timestamp
        if self.max is None or timestamp > self.max:
            self.max = timestamp
        return timestamp

    def format(self, timestamp):
        return timestamp - self.min if self.relative else timestamp


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


class DbcFilter:
    def __init__(self, accept_all=False, fully_accepted=None, partly_accepted=None):
        if fully_accepted is None:
            fully_accepted = {}
        if partly_accepted is None:
            partly_accepted = {}
            
        self.accept_all = accept_all
        self.fully_accepted = fully_accepted
        self.partly_accepted = partly_accepted

    def is_message_accepted(self, message):
        return self.accept_all\
               or (message.name in self.fully_accepted) \
               or (message.name in self.partly_accepted.keys())

    def keep_accepted_signals(self, message, signal_values):
        accepted_signal_names = {}

        if self.accept_all or message.name in self.fully_accepted:
            accepted_signal_names = signal_values
        else:
            if message.name in self.partly_accepted:
                accepted_signal_names = self.partly_accepted[message.name]

        accepted_signal_values = {name: value for (name, value) in signal_values.items()
                                  if name in accepted_signal_names}
        return accepted_signal_values


class LogExport:
    def __init__(self, dbc_file, dbc_filter,
                 signal_renamer=lambda x, y: y,
                 use_sample_and_hold=False,
                 use_relative_time=False,
                 target_channel=0,
                 expected_frame_count=None):

        self.dbc = cantools.database.load_file(dbc_file)
        self.dbc_filter = dbc_filter
        self.signal_renamer = signal_renamer
        self.use_sample_and_hold = use_sample_and_hold
        self.use_relative_time = use_relative_time
        self.target_channel = target_channel
        self.expected_frame_count = expected_frame_count
        self.total_frame_count = 0
        self.listed_frame_count = 0
        self.accepted_frame_count = 0
        self.progressbar = tqdm(total=expected_frame_count, desc='> Processing frames',
                                unit='frames', file=sys.stdout, ncols=100)
        self.rows = []
        self.fieldnames = ['timestamp']
        self.fieldunits = {}
        self.channel_analyzer = ChannelAnalyzer()
        self.timestamp_recorder = TimestampRecorder(use_relative_time)

    def process_frame(self, frame, allow_truncated=False):
        self.progressbar.update(1)
        self.total_frame_count += 1
        try:
            msg = self.dbc.get_message_by_frame_id(frame.arbitration_id)
        except KeyError:
            return
        self.process_message(frame, msg, allow_truncated)

    def process_message(self, frame, msg, allow_truncated):
        self.listed_frame_count += 1
        self.channel_analyzer.analyze(frame, msg)
        timestamp = self.timestamp_recorder.record(frame)

        if frame.channel is not self.target_channel:
            return

        if not self.dbc_filter.is_message_accepted(msg):
            return

        self.accepted_frame_count += 1

        try:
            decoded_values = msg.decode(frame.data,
                                        allow_truncated=allow_truncated,
                                        decode_choices=False)
        except cantools.database.errors.DecodeError as e:
            print(e)
            decoded_values = {}

        to_keep = self.dbc_filter.keep_accepted_signals(msg, decoded_values)

        to_write = {}
        for (signal_name, value) in to_keep.items():
            renamed = self.signal_renamer(msg.name, signal_name)
            to_write[renamed] = value
            if renamed not in self.fieldnames:
                self.fieldnames.append(renamed)
                for signal in msg.signals:
                    if signal.name is signal_name:
                        if signal.unit is not None:
                            self.fieldunits[renamed] = signal.unit.encode('cp1252').decode('utf8')

        to_write['timestamp'] = self.timestamp_recorder.format(timestamp)
        self.rows.append(to_write)

        if self.use_sample_and_hold:
            sample_and_hold(self.rows)

    def print_info(self):
        self.progressbar.close()
        print('> Time range of the frames is from {} to {}'
              .format(self.timestamp_recorder.min, self.timestamp_recorder.max))
        print('> Specified channel:', self.target_channel)
        print('> Most likely channel:', self.channel_analyzer.guess_channel())
        print('> Extracted {}/{} frames based on the DBC'
              .format(self.listed_frame_count, self.total_frame_count))
        print('> Accepted frame count:', self.accepted_frame_count)

    def write_csv(self, filename):
        with open(filename + '.csv', 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, delimiter=';', fieldnames=self.fieldnames)
            writer.writeheader()
            writer.writerows([self.fieldunits])
            print(self.fieldunits)
            writer.writerows(self.rows)
        print('> SHA256 of CSV file: {}'.format(get_sha(filename + '.csv')))
