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
