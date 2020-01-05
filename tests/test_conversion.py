import json
import unittest
import re

from deconz2mqtt.conversion import percent_to_bri, bri_to_percent, ct_to_percent, percent_to_ct, global_ct_max, \
    global_ct_min, string_to_on_off, convert_state_percent_to_value, convert_state_value_to_percent, \
    convert_state_to_http_payload


class TestConversion(unittest.TestCase):

    def test_brightness_percent_to_value(self):
        self.assertEqual(255, percent_to_bri(100))
        self.assertEqual(25, percent_to_bri(10))
        self.assertEqual(0, percent_to_bri(0))

    def test_brightness_value_to_percent(self):
        self.assertEqual(100, bri_to_percent(255))
        self.assertEqual(0, bri_to_percent(0))
        self.assertEqual(50, bri_to_percent(128))

    def test_ct_percent_to_value(self):
        self.assertEqual(global_ct_max, percent_to_ct(100), "100 percent should always be same as ct_max")
        self.assertEqual(187, percent_to_ct(10))
        self.assertEqual(global_ct_min, percent_to_ct(0))

    def test_ct_value_to_percent(self):
        self.assertEqual(100, ct_to_percent(global_ct_max), "ct_max should always return 100%")
        self.assertEqual(0, ct_to_percent(global_ct_min), "ct_min should always return 0%")
        self.assertEqual(0, ct_to_percent(0), "0 should always return 0%")

    def test_string_to_on_off_should_be_ON(self):
        self.assertEqual('ON', string_to_on_off('TruE'))
        self.assertEqual('ON', string_to_on_off('T'))
        self.assertEqual('ON', string_to_on_off('true'))
        self.assertEqual('ON', string_to_on_off(True))
        self.assertEqual('ON', string_to_on_off('on'))
        self.assertEqual('ON', string_to_on_off('On'))
        self.assertEqual('ON', string_to_on_off('ON'))

    def test_string_to_on_off_should_be_OFF(self):
        self.assertEqual('OFF', string_to_on_off('F'))
        self.assertEqual('OFF', string_to_on_off('False'))
        self.assertEqual('OFF', string_to_on_off('false'))
        self.assertEqual('OFF', string_to_on_off(False))
        self.assertEqual('OFF', string_to_on_off('OFF'))
        self.assertEqual('OFF', string_to_on_off('Off'))
        self.assertEqual('OFF', string_to_on_off('off'))
        self.assertEqual('OFF', string_to_on_off(None))
        self.assertEqual('OFF', string_to_on_off(''))

    def test_convert_state_value_on_off(self):
        for i in ['on', 'reachable', 'status', 'any_on', 'all_on']:
            self.assertEqual(False, convert_state_percent_to_value(i, 'False'))
            self.assertEqual(False, convert_state_percent_to_value(i, "b'false'"))
            self.assertEqual(False, convert_state_percent_to_value(i, False))
            self.assertEqual(True, convert_state_percent_to_value(i, True))
            self.assertEqual(True, convert_state_percent_to_value(i, 'True'))
            self.assertEqual(True, convert_state_percent_to_value(i, "b'true'"))

    def test_convert_value_on_off_to_percent(self):
        for i in ['on', 'reachable', 'status', 'any_on', 'all_on']:
            self.assertEqual("OFF", convert_state_value_to_percent(i, False))
            self.assertEqual("OFF", convert_state_value_to_percent(i, 'False'))
            self.assertEqual("ON", convert_state_value_to_percent(i, True))
            self.assertEqual("ON", convert_state_value_to_percent(i, 'True'))

    def test_convert_state_value_integer_all(self):
        for i in ['bri', 'sat', 'hue']:
            self.assertEqual(0, convert_state_percent_to_value(i, 0), "should convert 0 and " + i)
            self.assertEqual(0, convert_state_percent_to_value(i, 'False'), "should convert False and " + i)
            self.assertEqual(0, convert_state_percent_to_value(i, 'True'), "should convert True and " + i)
        for i in ['ct', 'cti']:
            self.assertEqual(global_ct_min, convert_state_percent_to_value(i, 0), "should convert 0 and " + i)
            self.assertEqual(0, convert_state_percent_to_value(i, 'False'))
            self.assertEqual(0, convert_state_percent_to_value(i, 'True'))

    def test_convert_state_value_integer_bri(self):
        self.assertEqual(0, convert_state_value_to_percent('bri', 0), "should convert 0 and bri")
        self.assertEqual(100, convert_state_value_to_percent('bri', 255), "should convert 255 and bri")
        self.assertEqual(50, convert_state_value_to_percent('bri', 255/2), "should convert 255/2 and bri")
        self.assertEqual(44, convert_state_value_to_percent('bri', 112), "Should convert 112 and bri to")

    def test_convert_state_value_integer_sat(self):
        self.assertEqual(0, convert_state_value_to_percent('sat', 0), "should convert 0 and sat")
        self.assertEqual(100, convert_state_value_to_percent('sat', 255), "should convert 255 and sat")
        self.assertEqual(50, convert_state_value_to_percent('sat', 255 / 2), "should convert 255/2 and sat")
        self.assertEqual(44, convert_state_value_to_percent('sat', 112), "Should convert 112 and sat to")

    def test_convert_state_value_integer_ct(self):
        self.assertEqual(0, convert_state_value_to_percent('ct', 0), "should convert 0 and ct")
        self.assertEqual(28, convert_state_value_to_percent('ct', 255), "should convert 255 and ct")
        self.assertEqual(100, convert_state_value_to_percent('ct', global_ct_max), "should convert ct_max and ct")
        self.assertEqual(0, convert_state_value_to_percent('ct', global_ct_min), "Should convert ct_min and ct")

    def test_sub(self):
        self.assertEqual('0', re.sub(r"^\D+'(?P<n>.*)'", "\g<n>", "b'0'"))
        self.assertEqual('true', re.sub(r"^\D+'(?P<n>.*)'", "\g<n>", "b'true'"))
        self.assertEqual('true', re.sub(r"^\D+'(?P<n>.*)'", "\g<n>", "d'true'"))

    def test_convert_state_to_http_payload_lights_on(self):
        item_state_type, result = convert_state_to_http_payload('on', 'lights', 'ON')
        self.assertEqual(json.dumps({"on": True}), result)
        self.assertEqual('state', item_state_type)

    def test_convert_state_to_http_payload_groups_on(self):
        item_state_type, result = convert_state_to_http_payload('on', 'groups', 'ON')
        self.assertEqual(json.dumps({"on": True}), result)
        self.assertEqual('action', item_state_type)

    def test_convert_state_to_http_payload_bri_100(self):
        item_state_type, result = convert_state_to_http_payload('bri', 'groups', 100)
        self.assertEqual(json.dumps({
            "bri": 255,
            "on": True
        }), result)
        self.assertEqual('action', item_state_type)

    def test_convert_state_to_http_payload_bri_0(self):
        item_state_type, result = convert_state_to_http_payload('bri', 'groups', 0)
        self.assertEqual(json.dumps({
            "bri": 0,
            "on": False
        }), result)
        self.assertEqual('action', item_state_type)


if __name__ == '__main__':
    unittest.main()
