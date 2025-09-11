import re
from collections import defaultdict
import json
from pathlib import Path


def print_warning(warning):
    warncolor = '\033[95m'
    endcolor = '\033[0m'
    print(f'> {warncolor}{warning}{endcolor}')


class RollingCounterVerifier:

    def __init__(self):
        self.count = 0
        self.previous_counter = None
        self.counter_errors = {}
        pass

    def process_frame(self, frame, msg, decoded_values, error):
        # Nothing to do for messages without a rolling counter
        if 'NCounter' not in decoded_values:
            return

        new_counter = decoded_values['NCounter']

        # Initialize the counter the first time with the first value found
        if self.previous_counter is None:
            self.previous_counter = new_counter
            return

        # No error if the counter value is different from the previous
        if self.previous_counter != new_counter:
            self.previous_counter = new_counter
            return

        # Record the error if the counter value has remained the same
        self.count += 1
        if msg.name not in self.counter_errors:
            self.counter_errors[msg.name] = {
                'NCounter': defaultdict(int)
            }
        self.counter_errors[msg.name]['NCounter'][new_counter] += 1

    def write_report(self, output_dir, filename):
        if self.count > 0:
            print_warning(f'Detected {self.count} frame(s) with invalid (repeated) rolling counter values')

            filepath = Path(output_dir, filename)

            report = []

            for message_name, message_errors in self.counter_errors.items():
                counter_signal_errors = message_errors['NCounter']
                formatted_errors = []
                for counter_value, frame_count in counter_signal_errors.items():
                    formatted_errors.append(
                        {
                            'NCounter': counter_value,
                            'repeated_frames': frame_count
                        }
                    )
                entry = {'message': message_name}
                entry.update({'errors': formatted_errors})
                report.append(entry)

            with open(filepath, 'w') as f:
                json.dump(report, f, indent=2)

            print(f'> Rolling counter verification report written to: {filepath}')
