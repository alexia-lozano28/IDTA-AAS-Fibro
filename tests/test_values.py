import unittest
from datetime import date, datetime

from dpp_aas.values import coerce_value


class CoerceValueTests(unittest.TestCase):
    def test_coerces_numbers_without_float_artifacts(self) -> None:
        self.assertEqual("0.0", coerce_value(0.0, "xs:decimal"))
        self.assertEqual("12", coerce_value("12", "xs:integer"))

    def test_coerces_dates_and_datetimes(self) -> None:
        self.assertEqual("2026-06-11", coerce_value(date(2026, 6, 11), "xs:date"))
        self.assertEqual(
            "2026-06-11T12:30:00",
            coerce_value(datetime(2026, 6, 11, 12, 30), "xs:dateTime"),
        )
        self.assertEqual(
            "2026-06-11T12:00:00",
            coerce_value("2026-06-11T12:00:00Z", "xs:dateTime"),
        )

    def test_rejects_invalid_typed_values(self) -> None:
        with self.assertRaises(ValueError):
            coerce_value("sometimes", "xs:boolean")
        with self.assertRaises(ValueError):
            coerce_value("not a date", "xs:date")


if __name__ == "__main__":
    unittest.main()
