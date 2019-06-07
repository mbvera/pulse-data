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
"""Base test class for testing subclasses of BaseHistoricalSnapshotUpdater"""
import datetime
from inspect import isclass
from types import ModuleType
from typing import Set, List
from unittest import TestCase

from more_itertools import one

from recidiviz import Session
from recidiviz.common.ingest_metadata import IngestMetadata, SystemLevel
from recidiviz.persistence.database.base_schema import Base
from recidiviz.persistence.database.database_entity import DatabaseEntity
from recidiviz.persistence.database.history.historical_snapshot_update import \
    update_historical_snapshots
from recidiviz.persistence.database.schema.schema_person_type import \
    SchemaPersonType
from recidiviz.persistence.database.schema_utils import \
    historical_table_class_from_obj
from recidiviz.persistence.persistence_utils import primary_key_name_from_obj, \
    primary_key_value_from_obj
from recidiviz.tests.utils import fakes


class BaseHistoricalSnapshotUpdaterTest(TestCase):
    """
    Base test class for testing subclasses of BaseHistoricalSnapshotUpdater
    """

    def setup_method(self, _test_method):
        fakes.use_in_memory_sqlite_database()

    @staticmethod
    def _commit_person(person: SchemaPersonType,
                       system_level: SystemLevel,
                       ingest_time: datetime.datetime):

        act_session = Session()
        merged_person = act_session.merge(person)

        metadata = IngestMetadata(region='somewhere',
                                  jurisdiction_id='12345',
                                  ingest_time=ingest_time,
                                  system_level=system_level)
        update_historical_snapshots(act_session, [merged_person], [], metadata)

        act_session.commit()
        act_session.close()

    def _check_all_non_history_schema_object_types_in_list(
            self,
            schema_objects: List[Base],
            schema: ModuleType,
            schema_object_type_names_to_ignore: List[str]) -> None:
        expected_schema_object_types = \
            self._get_all_non_history_schema_object_type_names_in_module(schema)

        expected_schema_object_types = \
            expected_schema_object_types.difference(
                set(schema_object_type_names_to_ignore))
        actual_schema_object_types = \
            {obj.__class__.__name__ for obj in schema_objects}

        self.assertEqual(expected_schema_object_types,
                         actual_schema_object_types)

    @staticmethod
    def _get_all_non_history_schema_object_type_names_in_module(
            schema: ModuleType) -> Set[str]:
        expected_schema_object_types = set()
        for attribute_name in dir(schema):
            attribute = getattr(schema, attribute_name)
            # Find all master (non-historical) schema object types
            if isclass(attribute) and attribute is not DatabaseEntity and \
                    issubclass(attribute, DatabaseEntity) \
                    and not attribute_name.endswith('History'):
                expected_schema_object_types.add(attribute_name)

        return expected_schema_object_types

    def _get_all_schema_objects_in_db(
            self,
            schema_person_type: SchemaPersonType,
            schema: ModuleType,
            schema_object_type_names_to_ignore: List[str]) -> List[Base]:
        """Generates a list of all schema objects stored in the database that
        can be reached from an object with the provided type.

        Args:
            schema_person_type: Class type of the root of the schema object
                graph (e.g. StatePerson).
            schema: The schema module that root_object_type is defined in.
            schema_object_type_names_to_ignore: type names for objects defined
                in the schema that we shouldn't assert are included in the
                object graph.

        Returns:
            A list of all schema objects that can be reached from the object
            graph rooted at the singular object of type |schema_person_type|.

        Throws:
            If more than one object of type |schema_person_type| exists in the
            DB.
        """

        session = Session()
        person = one(session.query(schema_person_type).all())

        schema_objects: Set[Base] = {person}
        unprocessed = list([person])
        while unprocessed:
            schema_object = unprocessed.pop()

            related_entities = []
            for relationship_name \
                    in schema_object.get_relationship_property_names():
                related = getattr(schema_object, relationship_name)

                # Relationship can return either a list or a single item
                if isinstance(related, Base):
                    related_entities.append(related)
                if isinstance(related, list):
                    related_entities.extend(related)

                for obj in related_entities:
                    if obj not in schema_objects:
                        schema_objects.add(obj)
                        unprocessed.append(obj)

        session.close()

        self._check_all_non_history_schema_object_types_in_list(
            list(schema_objects), schema, schema_object_type_names_to_ignore)

        return list(schema_objects)

    def _assert_expected_snapshots_for_schema_object(
            self,
            expected_schema_object: Base,
            ingest_times: List[datetime.date]) -> None:
        """
        Assert that we have expected history snapshots for the given schema
        object that has been ingested at the provided |ingest_times|.
        """
        history_table_class = \
            historical_table_class_from_obj(expected_schema_object)
        self.assertIsNotNone(history_table_class)

        schema_obj_primary_key_col_name = \
            primary_key_name_from_obj(expected_schema_object)
        schema_obj_primary_key_value = \
            primary_key_value_from_obj(expected_schema_object)

        self.assertIsNotNone(schema_obj_primary_key_value)
        self.assertEqual(type(schema_obj_primary_key_value), int)

        schema_obj_foreign_key_column_in_history_table = \
            getattr(history_table_class, schema_obj_primary_key_col_name, None)

        self.assertIsNotNone(schema_obj_foreign_key_column_in_history_table)

        assert_session = Session()
        history_snapshots: List[Base] = \
            assert_session.query(history_table_class).filter(
                schema_obj_foreign_key_column_in_history_table
                == schema_obj_primary_key_value
            ).all()

        self.assertEqual(len(history_snapshots), len(ingest_times))

        history_snapshots.sort(key=lambda snapshot: snapshot.valid_from)

        for i, history_snapshot in enumerate(history_snapshots):
            expected_valid_from = ingest_times[i]
            expected_valid_to = ingest_times[i+1] \
                if i < len(ingest_times) - 1 else None
            self.assertEqual(expected_valid_from, history_snapshot.valid_from)
            self.assertEqual(expected_valid_to, history_snapshot.valid_to)

        last_history_snapshot = history_snapshots[-1]
        assert last_history_snapshot is not None

        self._assert_schema_object_and_historical_snapshot_match(
            expected_schema_object,
            last_history_snapshot)

        assert_session.close()

    def _assert_schema_object_and_historical_snapshot_match(
            self, schema_object: Base, historical_snapshot: Base) -> None:
        shared_property_names = \
            type(schema_object).get_column_property_names().intersection(
                type(historical_snapshot).get_column_property_names())
        for column_property_name in shared_property_names:
            expected_col_value = getattr(schema_object, column_property_name)
            historical_col_value = getattr(
                historical_snapshot, column_property_name)
            self.assertEqual(expected_col_value, historical_col_value)
