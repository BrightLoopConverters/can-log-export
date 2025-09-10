import re
from collections import defaultdict
import json
from pathlib import Path


def print_warning(warning):
    warncolor = '\033[95m'
    endcolor = '\033[0m'
    print(f'> {warncolor}{warning}{endcolor}')


class MuxVerifier:

    def __init__(self):
        self.mux_errors = {}
        self.count = 0
        pass

    def process_frame(self, frame, msg, decoded_values, error):
        if error is not None:
            text = str(error)
            match = re.search(r'expected multiplexer id (\d+), but got (\d+)', text)
            if match:
                self.count += 1
                expected, got = map(int, match.groups())
                # Pas besoin d'aller rechercher la définition dans le DBC !?
                for element in msg.signal_tree:
                    # Multiplexed signals are provided inside dictionaries
                    if type(element) is dict:
                        [multiplexor, muxgroups] = next(iter(element.items()))
                        mux_values = set(muxgroups.keys())
                        if msg.name not in self.mux_errors:
                            self.mux_errors[msg.name] = {'multiplexor': multiplexor,
                                                         'expected_values_from_dbc': mux_values,
                                                         'actual_values_in_frames': defaultdict(int)}
                        self.mux_errors[msg.name]['actual_values_in_frames'][got] += 1

    def write_report(self, output_dir, filename):
        if self.count > 0:
            print_warning(f'Detected {self.count} frame(s) with unexpected multiplexor values')

            filepath = Path(output_dir, filename)

            report = []

            for name, errors in self.mux_errors.items():
                formatted_errors = {
                    'multiplexor': errors['multiplexor'],
                    'expected_values_from_dbc': list(errors['expected_values_from_dbc']),
                    'actual_values_in_frames': list(errors['actual_values_in_frames'])
                }
                entry = {'message': name}
                entry.update(formatted_errors)
                report.append(entry)

            with open(filepath, 'w') as f:
                json.dump(report, f, indent=2)

            print(f'> Multiplexor verification report written to: {filepath}')
