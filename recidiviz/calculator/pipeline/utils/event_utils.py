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
"""Utils for events that are a product of each pipeline's identifier step."""
import logging
from typing import Optional

import attr

from recidiviz.common.constants.state.state_assessment import StateAssessmentType


@attr.s
class AssessmentEventMixin:
    """Attribute that enables an event to be able to calculate the score bucket from assessment information."""
    @property
    def assessment_score_bucket(self) -> Optional[str]:
        """Calculates the assessment score bucket that applies to measurement.

        NOTE: Only LSIR and ORAS buckets are currently supported
        TODO(2742): Add calculation support for all supported StateAssessmentTypes

        Returns:
            A string representation of the assessment score for the person.
            None if the assessment type is not supported.
        """

        assessment_score = getattr(self, 'assessment_score')
        assessment_level = getattr(self, 'assessment_level')
        assessment_type = getattr(self, 'assessment_type')

        if not assessment_score or not assessment_type:
            # TODO(2853): Figure out more robust solution for not assessed people. Here we don't set assessment_type
            #  when someone is not assessed. This only works as desired because BQ doesn't rely on assessment_type at
            #  all.
            return 'NOT_ASSESSED'

        if assessment_type == StateAssessmentType.LSIR:
            if assessment_score < 24:
                return '0-23'
            if assessment_score <= 29:
                return '24-29'
            if assessment_score <= 38:
                return '30-38'
            return '39+'

        if assessment_type and assessment_type.value.startswith('ORAS'):
            if assessment_level:
                return assessment_level.value
            return None

        logging.warning("Assessment type %s is unsupported.", assessment_type)

        return None
