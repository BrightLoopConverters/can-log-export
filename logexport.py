import hashlib


def get_sha(filename):
    sha256_hash = hashlib.sha256()
    with open(filename, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def print_progress_dot(dot_count):
    dot_count += 1
    if dot_count > 80:
        print('.')
        dot_count = 0
    else:
        print('.', end='')
    return dot_count


def sample_and_hold(rows):
    if len(rows) > 1:
        for key in rows[-2]:
            if key not in rows[-1]:
                rows[-1][key] = rows[-2][key]


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
    def __init__(self, accept_all=False, fully_accepted={}, partly_accepted={}):
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
