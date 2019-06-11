# Recidiviz - a data platform for criminal justice reform
# Copyright (C) 2019 Recidiviz, Inc.
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

"""Converts an ingest_info proto StateIncarcerationPeriod to a
persistence entity."""

from recidiviz.common.constants.state.state_incarceration import \
    StateIncarcerationType
from recidiviz.common.constants.state.state_incarceration_period import \
    StateIncarcerationPeriodStatus, StateIncarcerationFacilitySecurityLevel, \
    StateIncarcerationPeriodAdmissionReason, \
    StateIncarcerationPeriodReleaseReason
from recidiviz.common.ingest_metadata import IngestMetadata
from recidiviz.common.str_field_utils import parse_date, normalize
from recidiviz.ingest.models.ingest_info_pb2 import StateIncarcerationPeriod
from recidiviz.persistence.entity.state import entities
from recidiviz.persistence.ingest_info_converter.utils.converter_utils import \
    fn, parse_external_id, parse_region_code_with_override
from recidiviz.persistence.ingest_info_converter.utils.enum_mappings import \
    EnumMappings


def copy_fields_to_builder(
        incarceration_period_builder: entities.StateIncarcerationPeriod.Builder,
        proto: StateIncarcerationPeriod,
        metadata: IngestMetadata) -> None:
    """Mutates the provided |incarceration_period_builder| by converting an
    ingest_info proto StateIncarcerationPeriod.

    Note: This will not copy children into the Builder!
    """
    new = incarceration_period_builder

    enum_fields = {
        'status': StateIncarcerationPeriodStatus,
        'incarceration_type': StateIncarcerationType,
        'facility_security_level': StateIncarcerationFacilitySecurityLevel,
        'admission_reason': StateIncarcerationPeriodAdmissionReason,
        'projected_release_reason': StateIncarcerationPeriodReleaseReason,
        'release_reason': StateIncarcerationPeriodReleaseReason
    }
    enum_mappings = EnumMappings(proto, enum_fields, metadata.enum_overrides)

    # enum values
    new.status = enum_mappings.get(StateIncarcerationPeriodStatus)
    new.status_raw_text = fn(normalize, 'status', proto)
    new.incarceration_type = enum_mappings.get(StateIncarcerationType)
    new.incarceration_type_raw_text = fn(normalize, 'incarceration_type', proto)
    new.facility_security_level = enum_mappings.get(
        StateIncarcerationFacilitySecurityLevel)
    new.facility_security_level_raw_text = fn(normalize,
                                              'facility_security_level',
                                              proto)
    new.admission_reason = enum_mappings.get(
        StateIncarcerationPeriodAdmissionReason)
    new.admission_reason_raw_text = fn(normalize, 'admission_reason', proto)
    new.projected_release_reason = enum_mappings.get(
        StateIncarcerationPeriodReleaseReason,
        field_name='projected_release_reason')
    new.projected_release_reason_raw_text = fn(normalize,
                                               'projected_release_reason',
                                               proto)
    new.release_reason = enum_mappings.get(
        StateIncarcerationPeriodReleaseReason, field_name='release_reason')
    new.release_reason_raw_text = fn(normalize, 'release_reason', proto)

    # 1-to-1 mappings
    new.external_id = fn(parse_external_id,
                         'state_incarceration_period_id',
                         proto)

    new.admission_date = fn(parse_date, 'admission_date', proto)
    new.release_date = fn(parse_date, 'release_date', proto)
    new.state_code = parse_region_code_with_override(
        proto, 'state_code', metadata)
    new.county_code = fn(normalize, 'county_code', proto)
    new.facility = fn(normalize, 'facility', proto)
    new.housing_unit = fn(normalize, 'housing_unit', proto)