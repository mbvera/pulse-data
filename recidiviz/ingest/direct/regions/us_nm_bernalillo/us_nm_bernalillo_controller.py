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

"""Direct ingest controller implementation for us_nm_bernalillo."""
import re
from datetime import datetime
from typing import List, Optional, cast, Iterator

import attr
import pandas as pd

from recidiviz import IngestInfo
from recidiviz.common.constants.bond import BondStatus, BondType
from recidiviz.common.constants.county.booking import CustodyStatus
from recidiviz.common.constants.person_characteristics import Ethnicity, Race
from recidiviz.common.ingest_metadata import SystemLevel, IngestMetadata
from recidiviz.ingest.direct.controllers.csv_gcsfs_direct_ingest_controller \
    import CsvGcsfsDirectIngestController
from recidiviz.ingest.direct.controllers.gcsfs_direct_ingest_controller import \
    GcsfsFileContentsHandle
from recidiviz.ingest.direct.controllers.gcsfs_direct_ingest_utils import \
    GcsfsIngestArgs, filename_parts_from_path
from recidiviz.ingest.direct.errors import DirectIngestError, \
    DirectIngestErrorType
from recidiviz.persistence import persistence


class UsNmBernalilloController(CsvGcsfsDirectIngestController):
    """Direct ingest controller implementation for us_nm_bernalillo."""

    def __init__(self,
                 ingest_directory_path: Optional[str] = 'us-nm-bernalillo',
                 storage_directory_path: Optional[str] = None,
                 max_delay_sec_between_files: Optional[int] = None):
        super(UsNmBernalilloController, self).__init__(
            'us_nm_bernalillo',
            SystemLevel.COUNTY,
            ingest_directory_path,
            storage_directory_path,
            max_delay_sec_between_files)

    def _get_file_tag_rank_list(self) -> List[str]:
        return ['MDC_VERA']

    class DataFrameContentsHandle(GcsfsFileContentsHandle):
        def __init__(self, local_path, df):
            super().__init__(local_path)
            self.df = df

        def get_contents_iterator(self) -> Iterator[str]:
            return self.df.to_csv(index=False)

    def _parse(self,
               args: GcsfsIngestArgs,
               contents_handle: GcsfsFileContentsHandle) -> IngestInfo:
        # Preprocess raw data.
        df = pd.read_csv(contents_handle.local_file_path, dtype=str,
                         lineterminator='\r').fillna('')
        df['PERSON ID'] = df['PERSON ID'].replace(r'\n', '', regex=True)
        ingest_info = super()._parse(args,
                                     self.DataFrameContentsHandle(
                                         contents_handle.local_file_path, df))

        self._postprocess_ingest_info(ingest_info)

        return ingest_info

    def _file_meets_file_line_limit(
            self, _contents_handle: GcsfsFileContentsHandle) -> bool:
        """The CSV files must be processed all at once, so do not split."""
        return True

    def _get_ingest_metadata(self, args: GcsfsIngestArgs) -> IngestMetadata:
        parts = filename_parts_from_path(args.file_path)
        ingest_time = datetime.strptime(cast(str, parts.filename_suffix),
                                        '%Y%m%d_%H')

        return attr.evolve(super()._get_ingest_metadata(args),
                           ingest_time=ingest_time)

    def _do_cleanup(self, args: GcsfsIngestArgs):
        """If this job is the last for the day, call infer_release before
        continuing to further jobs."""
        self.fs.mv_path_to_processed_path(args.file_path)

        if self._is_last_job_for_day(args):
            persistence.infer_release_on_open_bookings(
                self.region.region_code,
                self._get_ingest_metadata(args).ingest_time,
                CustodyStatus.INFERRED_RELEASE)

        parts = filename_parts_from_path(args.file_path)
        self._move_processed_files_to_storage_as_necessary(
            last_processed_date_str=parts.date_str)

    def _postprocess_ingest_info(self, ingest_info):
        """Validate the ingest info and extract some fields (e.g., charge)
        that are packed as HTML into a single field.
        """

        def replace_html_tags(in_str, replacement=''):
            return re.sub(r'<[^>]*>', replacement, in_str)

        for person in ingest_info.people:
            if len(person.bookings) != 1:
                raise DirectIngestError(
                    msg="Person did not have exactly one booking as expected.",
                    error_type=DirectIngestErrorType.PARSE_ERROR)

            booking = person.bookings[0]

            if booking.arrest and booking.arrest.agency:
                booking.arrest.agency = replace_html_tags(booking.arrest.agency,
                                                          '/')

            if not booking.charges:
                continue

            if len(booking.charges) != 1:
                raise DirectIngestError(
                    msg="Booking did not have exactly one charge as expected.",
                    error_type=DirectIngestErrorType.PARSE_ERROR)

            charge = booking.charges[0]
            if charge.name:
                charge_html = charge.name
                booking.charges = []
                charges = charge_html.split('<TR>')[1:]
                for charge_row in charges:
                    try:
                        (_, case_number, charge_date, charge_status,
                         charge_names, _) = re.sub(
                             r'(<>)\1+', '<>', replace_html_tags(
                                 charge_row, '<>')).split('<>')
                    except ValueError as e:
                        if len(charge_html) == 255 or len(charge_html) == 254:
                            continue
                        raise e

                    if charge_status != 'In County':
                        booking.create_hold(jurisdiction_name=charge_status)
                    for charge_name in charge_names.split(';'):
                        booking.create_charge(
                            name=charge_name,
                            offense_date=charge_date,
                            case_number=case_number)

    def get_enum_overrides(self):
        overrides_builder = super().get_enum_overrides().to_builder()

        overrides_builder.add('MEXICAN', Ethnicity.HISPANIC, Race)
        overrides_builder.add('TO BE SET BY JUDGE', BondStatus.PENDING,
                              BondType)

        return overrides_builder.build()
