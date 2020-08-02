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
"""All views that populate the data in the publilc dashboards."""
from typing import List

from recidiviz.big_query.big_query_view import BigQueryViewBuilder
from recidiviz.calculator.query.state.views.public_dashboard.incarceration import incarceration_views
from recidiviz.calculator.query.state.views.public_dashboard.racial_disparity import racial_disparity_views
from recidiviz.calculator.query.state.views.public_dashboard.sentencing import sentencing_views
from recidiviz.calculator.query.state.views.public_dashboard.supervision import supervision_views

PUBLIC_DASHBOARD_VIEW_BUILDERS: List[BigQueryViewBuilder] = (
    incarceration_views.INCARCERATION_VIEW_BUILDERS +
    racial_disparity_views.RACIAL_DISPARITY_VIEW_BUILDERS +
    sentencing_views.SENTENCING_VIEW_BUILDERS +
    supervision_views.SUPERVISION_VIEW_BUILDERS
)
