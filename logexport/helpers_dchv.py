def dchv_shortname(message_name, signal_name):
    message_name = message_name.removeprefix('Dcdc')
    return f'{message_name}.{signal_name}'