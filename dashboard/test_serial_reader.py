import unittest

from serial_reader import AquaGuardParser


class AquaGuardParserTests(unittest.TestCase):
    def feed(self, parser, lines):
        result = None
        for line in lines:
            result = parser.feed_line(line) or result
        return result

    def test_parses_complete_message(self):
        parser = AquaGuardParser()
        reading = self.feed(parser, [
            "----------------------",
            "Temperature: 25.60 Celsius",
            "Distance: 6.14 cm",
            "Water Sensor: 590 | Status: WET",
            "Buzzer: ON",
            "----------------------",
        ])
        self.assertEqual(reading["temperature_c"], 25.6)
        self.assertEqual(reading["distance_cm"], 6.14)
        self.assertEqual(reading["water_raw"], 590)
        self.assertEqual(reading["water_status"], "WET")
        self.assertEqual(reading["buzzer"], "ON")
        self.assertIn("timestamp", reading)

    def test_no_echo_and_temperature_error(self):
        parser = AquaGuardParser()
        reading = self.feed(parser, [
            "Temperature: Error",
            "Distance: NO ECHO",
            "Water Sensor: 120 | Status: DRY",
            "Buzzer: OFF",
        ])
        self.assertIsNone(reading["temperature_c"])
        self.assertEqual(reading["temperature_error"], "Error")
        self.assertIsNone(reading["distance_cm"])
        self.assertEqual(reading["distance_status"], "NO ECHO")

    def test_incomplete_message_is_not_published(self):
        parser = AquaGuardParser()
        self.assertIsNone(parser.feed_line("Temperature: 25.60 Celsius"))
        self.assertIsNone(parser.feed_line("Distance: 6.14 cm"))
        self.assertIsNone(parser.feed_line("Buzzer: OFF"))

    def test_unexpected_lines_are_ignored_and_new_cycle_resets_partial(self):
        parser = AquaGuardParser()
        parser.feed_line("Temperature: 20 Celsius")
        parser.feed_line("garbage from device")
        parser.feed_line("Distance: 3 cm")
        parser.feed_line("Temperature: 21 Celsius")
        self.assertIsNone(parser.feed_line("Buzzer: OFF"))
        result = self.feed(parser, ["Distance: 4 cm", "Water Sensor: 800", "Status: DRY", "Buzzer: OFF"])
        self.assertEqual(result["temperature_c"], 21)
        self.assertEqual(result["distance_cm"], 4)


if __name__ == "__main__":
    unittest.main()
