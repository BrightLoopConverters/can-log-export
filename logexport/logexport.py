import hashlib
import json
from datetime import datetime

import can
import cantools
from cantools import database
import sys
from tqdm import tqdm
from logdata import *
from pathlib import Path
import shutil
from crc_verifier import *
from mux_verifier import *


def print_warning(warning):
    warncolor = '\033[95m'
    endcolor = '\033[0m'
    print(f'> {warncolor}{warning}{endcolor}')


def get_sha(filename):
    sha256_hash = hashlib.sha256()
    with open(filename, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def count_lines(file):
    with open(file, "rb") as f:
        num_lines = sum(1 for _ in f)
    return num_lines


# Attempts to decode the file using the ASC format
def try_decode_asc(file):
    try:
        reader = can.ASCReader(file)
        frame = next(iter(reader))
        print('> Successfully decoded file as ASC')
        return [can.ASCReader, count_lines(file)]
    except (UnicodeDecodeError, StopIteration) as e:
        print('> Failed to decode file as ASC')
        return [None, 0]


# Attempts to decode the file using the TRC format
def try_decode_trc(file):
    try:
        reader = can.TRCReader(file)
        frame = next(iter(reader))
        print('> Successfully decoded file as TRC')
        return [can.TRCReader, count_lines(file)]
    except (UnicodeDecodeError, ValueError, StopIteration) as e:
        print('> Failed to decode file as TRC')
        return [None, 0]


# Attempts to decode the file using the BLF format
def try_decode_blf(file):
    try:
        reader = can.BLFReader(file)
        frame = next(iter(reader))
        print('> Successfully decoded file as BLF')
        return [can.BLFReader, reader.object_count]
    except can.io.blf.BLFParseError as e:
        print('> Failed to decode file as BLF')
        return [None, 0]


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
        if frame.channel not in self.mismatch_counts:
            self.mismatch_counts[frame.channel] = 0
        if frame.dlc is not msg.length:
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
        # The most probable channel is the one with the fewest DLC errors
        sorted_channels = sorted(self.mismatch_counts,
                                 key=lambda k: self.mismatch_counts[k])
        if sorted_channels:
            return sorted_channels[0]

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
        return self.accept_all \
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
    class AutoChannelRepr:
        def __repr__(self): return 'AutoChannel'

    def __init__(self, dbc_file, dbc_filter,
                 use_time_grouping=False,
                 signal_renamer=lambda x, y: y,
                 use_sample_and_hold=False,
                 use_relative_time=False,
                 target_channel=0,
                 expected_frame_count=None):
        """
        Keyword arguments:
        target_channel -- Most logging formats include a "channel" field
        indicating the CAN interface that recorded each frame. ASC logs use
        1-based channel numbering, but this tool shifts channels to 0-based
        numbering during export.
        """
        self.decode_error = None
        self.dbc = cantools.database.load_file(dbc_file)
        self.dbc_filter = dbc_filter
        self.use_time_grouping = use_time_grouping
        self.signal_renamer = signal_renamer
        self.use_sample_and_hold = use_sample_and_hold
        self.use_relative_time = use_relative_time
        self.target_channel = target_channel
        self.expected_frame_count = expected_frame_count
        self.total_frame_count = 0
        self.listed_frame_count = 0
        self.accepted_frame_count = 0
        self.progressbar = tqdm(total=expected_frame_count, desc='> Processing frames',
                                unit=' frames', file=sys.stdout, ncols=100)
        self.channel_analyzer = ChannelAnalyzer()
        self.timestamp_recorder = TimestampRecorder(use_relative_time)
        self.data = {}
        self.crc_verifier = CrcVerifier()
        self.frame_listeners = [MuxVerifier()]

    def initialize_log_data(self, channel):
        if channel in self.data:
            return

        if self.use_time_grouping:
            self.data[channel] = LogDataTree(self.signal_renamer)
        else:
            self.data[channel] = LogDataTable(self.signal_renamer,
                                              use_sample_and_hold=self.use_sample_and_hold)

    def process_frame(self, frame, allow_truncated=False):
        self.progressbar.update(1)
        self.total_frame_count += 1
        try:
            msg = self.dbc.get_message_by_frame_id(frame.arbitration_id)
        except KeyError:
            return

        self.listed_frame_count += 1
        self.channel_analyzer.analyze(frame, msg)

        if frame.channel is self.target_channel or self.target_channel is AutoChannel:
            self.decode_error = self.process_message(frame, msg, allow_truncated)
            self.crc_verifier.check_frame(frame, msg)

    def process_message(self, frame, msg, allow_truncated):
        if not self.dbc_filter.is_message_accepted(msg):
            return

        self.accepted_frame_count += 1
        timestamp = self.timestamp_recorder.record(frame)

        error = None
        try:
            decoded_values = msg.decode(frame.data,
                                        allow_truncated=allow_truncated,
                                        decode_choices=False)
        except cantools.database.errors.DecodeError as e:
            error = e
            decoded_values = {}

        self._notify_listeners(frame, msg, decoded_values, error)

        to_keep = self.dbc_filter.keep_accepted_signals(msg, decoded_values)

        self.initialize_log_data(frame.channel)
        data = self.data[frame.channel]
        data.create_fields(msg)
        data.add_field_values(msg, to_keep, self.timestamp_recorder.format(timestamp))
        return error

    def print_info(self):
        self.progressbar.update(self.progressbar.total)
        self.progressbar.close()
        print('> Time range of the frames is from {} to {}'
              .format(self.timestamp_recorder.min, self.timestamp_recorder.max))
        print('> Extracted {}/{} frames based on the DBC'
              .format(self.listed_frame_count, self.total_frame_count))
        print(f'> Channel specified: {self.target_channel}')
        if self.target_channel is AutoChannel:
            print(f'> AutoChannel selection result: Channel {self.channel_analyzer.guess_channel()}')
        print('> Accepted frame count:', self.accepted_frame_count)
        if self.decode_error is not None:
            print('> Encountered decoding error:', self.decode_error)

    def get_active_groups(self):
        if not self.data:
            return {}

        if self.target_channel is AutoChannel:
            channel = self.channel_analyzer.guess_channel()
        else:
            channel = self.target_channel

        return self.data[channel].groups()

    def write_crc_report(self, output_dir, filename):
        if self.crc_verifier.count > 0:
            print_warning(f'Detected {self.crc_verifier.count} frame(s) with incorrect NCrc values')
            filepath = Path(output_dir, filename)
            self.crc_verifier.write_json_report(filepath)
            print(f'> CRC verification report written to: {filepath}')

    def write_csv(self, output_dir, data_file):
        output_path = Path(output_dir, Path(data_file).name)

        groups = self.get_active_groups()
        group_count = len(groups)

        if group_count == 0:
            return

        elif group_count > 1:
            directory = Path(data_file + '_groups')
            if directory.exists():
                shutil.rmtree(directory)
            directory.mkdir()

            for group in groups.values():
                print(f'> Writing CSV file for group {group.name}')
                group.remove_empty_columns()
                group.write_csv(directory)

            zip_archive_name = shutil.make_archive(output_path, 'zip', directory)
            print(f'> Created ZIP archive: {zip_archive_name}')
            return zip_archive_name

        else:
            group = next(iter(groups.values()))
            csv_name = group.write_csv(output_path, ';').resolve()
            print(f'> Created CSV file: {csv_name}')
            return str(csv_name)

    def write_signals_json(self, output_dir, filename):
        groups = self.get_active_groups()
        signal_set = set()

        for group in groups.values():
            signal_set.update(group.fieldnames)
        signal_set.discard('timestamp')
        signal_list = sorted(signal_set)

        signals_path = Path(output_dir, filename)
        with open(signals_path, 'w') as signals_file:
            json.dump(signal_list, signals_file, indent=2)

    def add_listener(self, listener) -> None:
        self.frame_listeners.append(listener)

    def _notify_listeners(self, frame, message, decoded_values, error) -> None:
        for listener in self.frame_listeners:
            listener.process_frame(frame, message, decoded_values, error)


AutoChannel = LogExport.AutoChannelRepr()
