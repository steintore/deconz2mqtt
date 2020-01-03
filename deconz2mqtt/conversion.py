global_bri_max: int = 255
global_ct_min: int = 153
global_ct_max: int = 500

on_off_keys = ['on', 'reachable', 'status', 'any_on', 'all_on']
int_keys = ['bri', 'ct', 'sat', 'hue', 'cti']


def bri_to_percent(bri):
    return int(round(bri / global_bri_max, 2) * 100)


def percent_to_bri(percent):
    if isinstance(percent, int):
        return int(round(float(percent) / 100, 2) * global_bri_max)
    return 0


def ct_to_percent(ct, ct_min=global_ct_min, ct_max=global_ct_max):
    if ct <= ct_min:
        return 0
    return int(round(float(ct - ct_min) / (ct_max - ct_min), 2) * 100)


def percent_to_ct(percent, ct_min=global_ct_min, ct_max=global_ct_max):
    return int(round(float(percent) / 100, 2) * (ct_max - ct_min) + ct_min)


def string_to_on_off(value):
    if value is None or value is False:
        return 'OFF'
    return 'ON' if str(value).lower() in ['true', 't', 'on'] else 'OFF'


def convert_state_percent_to_value(value_type, value, ct_min=global_ct_min, ct_max=global_ct_max):
    new_state = string_to_on_off(value) if value_type in on_off_keys else value
    if value_type in int_keys and not isinstance(new_state, int):
        return 0
    new_state = int(new_state) if value_type in int_keys and isinstance(new_state, int) else new_state
    if value_type in ['bri', 'sat']:
        new_state = percent_to_bri(new_state)
    if value_type in ['ct', 'cti']:
        new_state = percent_to_ct(new_state, ct_min, ct_max)
    # TODO Handle HUE
    return new_state


def convert_state_value_to_percent(value_type, value, ct_min=global_ct_min, ct_max=global_ct_max):
    new_state = string_to_on_off(value) if value_type in on_off_keys else value
    new_state = int(new_state) if value_type in int_keys and isinstance(new_state, int) else new_state
    if value_type in ['bri', 'sat']:
        new_state = bri_to_percent(new_state)
    if value_type in ['ct', 'cti']:
        new_state = ct_to_percent(new_state, ct_min, ct_max)
    # TODO Handle HUE
    return new_state
