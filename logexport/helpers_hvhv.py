def hvhv_shortname(message_name, signal_name):
    message_name = message_name.removeprefix('HVHV_')
    return f'{message_name}.{signal_name}'