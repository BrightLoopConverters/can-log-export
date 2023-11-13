import csv
import os.path


# Constructs a new time base name from the message name and the value of the
# multiplexer signal.
def group_name(msg_name, muxvalue=None):
    return msg_name if muxvalue is None else f'{msg_name}.Mux{muxvalue}'


def get_signal_unit(msg, signal_name):
    for signal in msg.signals:
        if signal.name is signal_name:
            if signal.unit is not None:
                return signal.unit


class LogDataGroup:
    def __init__(self, signal_renamer, name=None):
        self.name = 'Default Group' if name is None else name
        self.signal_renamer = signal_renamer
        self.fieldnames = ['timestamp']
        self.units = {}
        self.rows = []
        self.counts = {'timestamp': 0}

    def add_field(self, msg, signal_name):
        fieldname = self.signal_renamer(msg.name, signal_name)
        self.fieldnames.append(fieldname)
        self.counts[fieldname] = 0
        unit = get_signal_unit(msg, signal_name)
        if unit:
            self.units[fieldname] = unit

    def add_field_values(self, decoded_values):
        self.rows.append(decoded_values)
        for fieldname in decoded_values:
            self.counts[fieldname] += 1

    def write_csv(self, filepath, delimiter=',', use_group_name=True):
        # Columns containing no values due to the applied filtering are removed
        # from the list of fields to be written in the CSV.
        for fieldname in self.counts:
            if self.counts[fieldname] == 0:
                self.fieldnames.remove(fieldname)
                if fieldname in self.units:
                    del self.units[fieldname]

        directory = os.path.dirname(filepath)

        if use_group_name:
            output = os.path.join(directory, self.name + '.csv')
        else:
            output = filepath + '.csv'

        with open(output, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, delimiter=delimiter,
                                    fieldnames=self.fieldnames)
            writer.writeheader()
            # If the unit line is empty, it is not written to the CSV
            if self.units:
                writer.writerows([self.units])
            writer.writerows(self.rows)

        return output

    def sample_and_hold(self):
        if len(self.rows) > 1:
            for key in self.rows[-2]:
                if key not in self.rows[-1]:
                    self.rows[-1][key] = self.rows[-2][key]


class LogDataTable:
    def __init__(self, signal_renamer, use_sample_and_hold=False):
        self.signal_renamer = signal_renamer
        self.msg_names = []
        self.group = LogDataGroup(signal_renamer)
        self.use_sample_and_hold = use_sample_and_hold

    def create_fields(self, msg):
        if msg.name in self.msg_names:
            return
        else:
            self.msg_names.append(msg.name)

        for element in msg.signal_tree:
            # Multiplexed signals are provided inside dictionaries
            if type(element) is not dict:
                self.find_group(msg).add_field(msg, element)

            # Non-multiplexed signals are provided as strings
            else:
                [multiplexor, muxgroups] = next(iter(element.items()))
                self.find_group(msg).add_field(msg, multiplexor)

                for muxvalue in muxgroups:
                    group = self.find_group(msg, muxvalue)
                    for signal_name in muxgroups[muxvalue]:
                        group.add_field(msg, signal_name)

    def add_field_values(self, msg, decoded_values, timestamp):
        signals_row = {}
        for signal_name, value in decoded_values.items():
            fieldname = self.signal_renamer(msg.name, signal_name)
            signals_row[fieldname] = value

        if signals_row:
            signals_row['timestamp'] = timestamp
            group = self.find_group(msg)
            group.add_field_values(signals_row)
            if self.use_sample_and_hold:
                group.sample_and_hold()

    def find_group(self, msg, muxvalue=None):
        return self.group

    def groups(self):
        return {self.group.name: self.group}


class LogDataTree:
    def __init__(self, signal_renamer):
        self.signal_renamer = signal_renamer
        self.common_groups = {}
        self.muxed_groups = {}
        self.cached_multiplexors = {}
        self.cached_common_signals = {}

    def create_fields(self, msg):
        if msg.name in self.common_groups:
            return

        # Creating the default group for non-multiplexed signals.
        self.cached_common_signals[msg.name] = []
        self.common_groups[msg.name] = LogDataGroup(self.signal_renamer,
                                                    group_name(msg.name))

        for element in msg.signal_tree:
            # In the signal_tree property, multiplexed signals are grouped into 
            # dictionaries, while non-multiplexed signals are stored as strings.
            if type(element) is not dict:
                self.find_group(msg).add_field(msg, element)
                self.cached_common_signals[msg.name].append(element)

            else:
                # Cases with more than one multiplexer are not supported, so it 
                # sufficient to retrieve the first value in order to access the
                # signals, which are grouped by associated multiplexer value.
                [multiplexor, muxgroups] = next(iter(element.items()))

                # The multiplexer signal itself is part of the group of non-
                # multiplexed signals
                self.find_group(msg).add_field(msg, multiplexor)
                self.cached_common_signals[msg.name].append(multiplexor)
                self.cached_multiplexors[msg.name] = multiplexor

                self.muxed_groups[msg.name] = {}
                for muxvalue in muxgroups:
                    self.muxed_groups[msg.name][muxvalue] = LogDataGroup(self.signal_renamer,
                                                                         group_name(msg.name, muxvalue))

                    group = self.find_group(msg, muxvalue)
                    for signal_name in muxgroups[muxvalue]:
                        group.add_field(msg, signal_name)

    def add_field_values(self, msg, decoded_values, timestamp):
        if msg.name not in self.common_groups:
            print(f'> Group not found for message {msg.name}')
            return

        common_signals_row = {}
        muxed_signals_row = {}

        common_signal_names = self.cached_common_signals[msg.name]
        for signal_name, value in decoded_values.items():
            fieldname = self.signal_renamer(msg.name, signal_name)
            if signal_name in common_signal_names:
                row = common_signals_row
            else:
                row = muxed_signals_row

            row[fieldname] = value

        if common_signals_row:
            common_signals_row['timestamp'] = timestamp
            self.find_group(msg).rows.append(common_signals_row)
        if muxed_signals_row:
            muxed_signals_row['timestamp'] = timestamp
            muxvalue = decoded_values[self.cached_multiplexors[msg.name]]
            self.find_group(msg, muxvalue).rows.append(muxed_signals_row)

    def find_group(self, msg, muxvalue=None):
        if muxvalue is None:
            return self.common_groups[msg.name]
        else:
            return self.muxed_groups[msg.name][muxvalue]

    def groups(self):
        result = {}
        for msg_name, common_group in self.common_groups.items():
            result[common_group.name] = common_group
            if msg_name in self.muxed_groups:
                for muxvalue, muxed_group in self.muxed_groups[msg_name].items():
                    result[muxed_group.name] = muxed_group
        return result
