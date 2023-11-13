import csv
import os.path


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

    def add_field(self, msg, signal_name):
        fieldname = self.signal_renamer(msg.name, signal_name)
        self.fieldnames.append(fieldname)
        unit = get_signal_unit(msg, signal_name)
        if unit:
            self.units[fieldname] = unit

    def write_csv(self, filepath, delimiter=',', use_group_name=True):

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


class LogDataTable:
    def __init__(self, signal_renamer):
        self.signal_renamer = signal_renamer
        self.msg_names = []
        self.group = LogDataGroup(signal_renamer)

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
            group.rows.append(signals_row)

    def find_group(self, msg, muxvalue=None):
        return self.group
