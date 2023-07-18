DATA_SOURCES_EXAMPLE = {
    'MESSAGE_1': [
        'PARAM_1_x',
        'PARAM_1_y',
        'PARAM_1_z'
    ],
    'MESSAGE_2': [
        'PARAM_2_x',
        'PARAM_2_y',
        'PARAM_2_z'
    ]
}

def dchv_shortname(message_name, signal_name):
    message_name = message_name.removeprefix('Dcdc')
    return '{}::{}'.format(message_name, signal_name)