# Recidiviz - a data platform for criminal justice reform
# Copyright (C) 2020 Recidiviz, Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
# =============================================================================
"""Tests for time_range_utils.py."""
import datetime
import unittest

from recidiviz.calculator.pipeline.utils.time_range_utils import TimeRange, TimeRangeDiff


class TestTimeRange(unittest.TestCase):
    """Tests for TimeRange"""

    def setUp(self) -> None:
        self.negative_day_range = TimeRange(
            lower_bound_inclusive_date=datetime.date(2019, 2, 3),
            upper_bound_exclusive_date=datetime.date(2019, 2, 2))

        self.zero_day_range = TimeRange(
            lower_bound_inclusive_date=datetime.date(2019, 2, 3),
            upper_bound_exclusive_date=datetime.date(2019, 2, 3))

        self.one_day_range = TimeRange(
            lower_bound_inclusive_date=datetime.date(2019, 2, 3),
            upper_bound_exclusive_date=datetime.date(2019, 2, 4))

        self.single_month_range = TimeRange(
            lower_bound_inclusive_date=datetime.date(2019, 2, 1),
            upper_bound_exclusive_date=datetime.date(2019, 3, 1))

        self.multi_month_range = TimeRange(
            lower_bound_inclusive_date=datetime.date(2019, 2, 3),
            upper_bound_exclusive_date=datetime.date(2019, 4, 10))

    def test_get_months_range_overlaps_at_all(self):
        self.assertEqual([], self.negative_day_range.get_months_range_overlaps_at_all())
        self.assertEqual([], self.zero_day_range.get_months_range_overlaps_at_all())
        self.assertEqual([(2019, 2)], self.one_day_range.get_months_range_overlaps_at_all())
        self.assertEqual([(2019, 2)], self.single_month_range.get_months_range_overlaps_at_all())
        self.assertEqual([(2019, 2), (2019, 3), (2019, 4)],
                         self.multi_month_range.get_months_range_overlaps_at_all())

    def test_portion_overlapping_with_month(self):

        self.assertEqual(None, self.negative_day_range.portion_overlapping_with_month(2019, 2))

        self.assertEqual(None, self.zero_day_range.portion_overlapping_with_month(2019, 2))

        self.assertEqual(self.one_day_range,
                         self.one_day_range.portion_overlapping_with_month(2019, 2))

        self.assertEqual(self.single_month_range,
                         self.single_month_range.portion_overlapping_with_month(2019, 2))

        self.assertEqual(TimeRange(lower_bound_inclusive_date=datetime.date(2019, 2, 3),
                                   upper_bound_exclusive_date=datetime.date(2019, 3, 1)),
                         self.multi_month_range.portion_overlapping_with_month(2019, 2))

        self.assertEqual(TimeRange(lower_bound_inclusive_date=datetime.date(2019, 3, 1),
                                   upper_bound_exclusive_date=datetime.date(2019, 4, 1)),
                         self.multi_month_range.portion_overlapping_with_month(2019, 3))

        self.assertEqual(TimeRange(lower_bound_inclusive_date=datetime.date(2019, 4, 1),
                                   upper_bound_exclusive_date=datetime.date(2019, 4, 10)),
                         self.multi_month_range.portion_overlapping_with_month(2019, 4))


class TestTimeRangeDiff(unittest.TestCase):
    """Tests for TimeRangeDiff"""

    def test_non_overlapping_ranges(self):
        range_1 = TimeRange.for_month(2019, 2)
        range_2 = TimeRange.for_month(2019, 3)

        time_range_diff = TimeRangeDiff(range_1, range_2)

        self.assertEqual(None, time_range_diff.overlapping_range)
        self.assertEqual([range_1], time_range_diff.range_1_non_overlapping_parts)
        self.assertEqual([range_2], time_range_diff.range_2_non_overlapping_parts)

    def test_exactly_overlapping_ranges(self):
        range_1 = TimeRange.for_month(2019, 2)
        range_2 = TimeRange.for_month(2019, 2)

        time_range_diff = TimeRangeDiff(range_1, range_2)

        self.assertEqual(range_1, time_range_diff.overlapping_range)
        self.assertEqual([], time_range_diff.range_1_non_overlapping_parts)
        self.assertEqual([], time_range_diff.range_2_non_overlapping_parts)

    def test_range_fully_overlaps_other(self):
        range_1 = TimeRange(datetime.date(2019, 2, 5), datetime.date(2019, 5, 2))
        range_2 = TimeRange(datetime.date(2019, 3, 1), datetime.date(2019, 3, 5))

        time_range_diff = TimeRangeDiff(range_1, range_2)

        self.assertEqual(range_2, time_range_diff.overlapping_range)
        self.assertEqual(
            [TimeRange(datetime.date(2019, 2, 5), datetime.date(2019, 3, 1)),
             TimeRange(datetime.date(2019, 3, 5), datetime.date(2019, 5, 2))],
            time_range_diff.range_1_non_overlapping_parts)
        self.assertEqual([], time_range_diff.range_2_non_overlapping_parts)

        time_range_diff = TimeRangeDiff(range_2, range_1)
        self.assertEqual(range_2, time_range_diff.overlapping_range)
        self.assertEqual([], time_range_diff.range_1_non_overlapping_parts)
        self.assertEqual(
            [TimeRange(datetime.date(2019, 2, 5), datetime.date(2019, 3, 1)),
             TimeRange(datetime.date(2019, 3, 5), datetime.date(2019, 5, 2))],
            time_range_diff.range_2_non_overlapping_parts)

    def test_partially_overlapping_ranges(self):
        range_1 = TimeRange(datetime.date(2019, 2, 5), datetime.date(2019, 5, 2))
        range_2 = TimeRange(datetime.date(2019, 3, 1), datetime.date(2019, 6, 5))

        time_range_diff = TimeRangeDiff(range_1, range_2)

        self.assertEqual(TimeRange(datetime.date(2019, 3, 1), datetime.date(2019, 5, 2)),
                         time_range_diff.overlapping_range)
        self.assertEqual(
            [TimeRange(datetime.date(2019, 2, 5), datetime.date(2019, 3, 1))],
            time_range_diff.range_1_non_overlapping_parts)
        self.assertEqual(
            [TimeRange(datetime.date(2019, 5, 2), datetime.date(2019, 6, 5))],
            time_range_diff.range_2_non_overlapping_parts)

        time_range_diff = TimeRangeDiff(range_2, range_1)
        self.assertEqual(TimeRange(datetime.date(2019, 3, 1), datetime.date(2019, 5, 2)),
                         time_range_diff.overlapping_range)
        self.assertEqual(
            [TimeRange(datetime.date(2019, 5, 2), datetime.date(2019, 6, 5))],
            time_range_diff.range_1_non_overlapping_parts)
        self.assertEqual(
            [TimeRange(datetime.date(2019, 2, 5), datetime.date(2019, 3, 1))],
            time_range_diff.range_2_non_overlapping_parts)
