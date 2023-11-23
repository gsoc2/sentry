from datetime import datetime, timedelta
from typing import Sequence
from unittest.mock import patch

import pytest
from django.utils import timezone

from sentry.models.organization import Organization
from sentry.models.project import Project
from sentry.sentry_metrics.querying.metadata import get_cache_key_for_code_location
from sentry.sentry_metrics.querying.utils import get_redis_client_for_metrics_meta
from sentry.testutils.cases import MetricsAPIBaseTestCase
from sentry.testutils.helpers.datetime import freeze_time
from sentry.testutils.silo import region_silo_test
from sentry.utils import json

pytestmark = pytest.mark.sentry_metrics


@freeze_time("2023-11-21T10:30:30.000Z")
@region_silo_test(stable=True)
class OrganizationDDMMetaEndpointTest(MetricsAPIBaseTestCase):
    endpoint = "sentry-api-0-organization-ddm-meta"

    def setUp(self):
        super().setUp()
        self.login_as(user=self.user)
        self.redis_client = get_redis_client_for_metrics_meta()
        self.current_time = timezone.now()

    def _mock_code_location(self, filename) -> str:
        code_location = {
            "function": "foo",
            "module": "bar",
            "filename": filename,
            "abs_path": f"/usr/src/foo/{filename}",
            "lineno": 10,
        }

        return json.dumps(code_location)

    def _store_code_location(
        self, organization_id: int, project_id: int, metric_mri: str, timestamp: int, value: str
    ):
        cache_key = get_cache_key_for_code_location(
            organization_id, project_id, metric_mri, timestamp
        )
        self.redis_client.sadd(cache_key, value)

    def _round_to_day(self, time: datetime) -> int:
        return int(time.timestamp() / 86400) * 86400

    def _store_code_locations(
        self,
        organization: Organization,
        projects: Sequence[Project],
        metric_mris: Sequence[str],
        days: int,
    ):
        timestamps = [
            self._round_to_day(self.current_time - timedelta(days=day)) for day in range(0, days)
        ]
        for project in projects:
            for metric_mri in metric_mris:
                for timestamp in timestamps:
                    self._store_code_location(
                        organization.id,
                        project.id,
                        metric_mri,
                        timestamp,
                        self._mock_code_location("script.py"),
                    )
                    self._store_code_location(
                        organization.id,
                        project.id,
                        metric_mri,
                        timestamp,
                        self._mock_code_location("main.py"),
                    )

    def test_get_locations_with_stats_period(self):
        projects = [self.create_project(name="project_1")]
        mris = [
            "d:custom/sentry.process_profile.track_outcome@second",
        ]

        # We specify two days, since we are querying a stats period of 1 day, thus from one day to another.
        self._store_code_locations(self.organization, projects, mris, 2)

        response = self.get_success_response(
            self.organization.slug,
            metric=mris,
            project=[project.id for project in projects],
            statsPeriod="1d",
        )
        metrics = response.data["metrics"]

        assert len(metrics) == 2

        assert metrics[0]["mri"] == mris[0]
        assert metrics[0]["timestamp"] == self._round_to_day(self.current_time - timedelta(days=1))

        assert metrics[1]["mri"] == mris[0]
        assert metrics[1]["timestamp"] == self._round_to_day(self.current_time)

        code_locations = metrics[0]["frames"]
        assert len(code_locations) == 2
        for index, filename in enumerate(("main.py", "script.py")):
            assert code_locations[index]["filename"] == filename

        code_locations = metrics[0]["frames"]
        assert len(code_locations) == 2
        for index, filename in enumerate(("main.py", "script.py")):
            assert code_locations[index]["filename"] == filename

    def test_get_locations_with_start_and_end(self):
        projects = [self.create_project(name="project_1")]
        mris = [
            "d:custom/sentry.process_profile.track_outcome@second",
        ]

        # We specify two days, since we are querying a stats period of 1 day, thus from one day to another.
        self._store_code_locations(self.organization, projects, mris, 2)

        response = self.get_success_response(
            self.organization.slug,
            metric=mris,
            project=[project.id for project in projects],
            # We use an interval of 1 day but shifted by 1 day in the past.
            start=(self.current_time - timedelta(days=2)).isoformat(),
            end=(self.current_time - timedelta(days=1)).isoformat(),
        )
        metrics = response.data["metrics"]

        assert len(metrics) == 1

        assert metrics[0]["mri"] == mris[0]
        assert metrics[0]["timestamp"] == self._round_to_day(self.current_time - timedelta(days=1))

        code_locations = metrics[0]["frames"]
        assert len(code_locations) == 2
        for index, filename in enumerate(("main.py", "script.py")):
            assert code_locations[index]["filename"] == filename

    def test_get_locations_with_start_and_end_and_no_data(self):
        projects = [self.create_project(name="project_1")]
        mris = ["d:custom/sentry.process_profile.track_outcome@second"]

        # We specify two days, since we are querying a stats period of 1 day, thus from one day to another.
        self._store_code_locations(self.organization, projects, mris, 2)

        response = self.get_success_response(
            self.organization.slug,
            metric=mris,
            project=[project.id for project in projects],
            # We use an interval outside which we have no data.
            start=(self.current_time - timedelta(days=3)).isoformat(),
            end=(self.current_time - timedelta(days=2)).isoformat(),
        )
        metrics = response.data["metrics"]

        assert len(metrics) == 0

    @patch("sentry.sentry_metrics.querying.metadata.CodeLocationsFetcher._get_code_locations")
    @patch("sentry.sentry_metrics.querying.metadata.CodeLocationsFetcher.BATCH_SIZE", 10)
    def test_get_locations_batching(self, get_code_locations_mock):
        get_code_locations_mock.return_value = []

        projects = [self.create_project(name="project_1")]
        mris = ["d:custom/sentry.process_profile.track_outcome@second"]

        self.get_success_response(
            self.organization.slug,
            metric=mris,
            project=[project.id for project in projects],
            statsPeriod="90d",
        )

        # With a window of 90 days, it means that we are actually requesting 91 days, thus we have 10 batches of 10
        # elements each.
        assert len(get_code_locations_mock.mock_calls) == 10

    def test_get_locations_with_incomplete_location(self):
        project = self.create_project(name="project_1")
        mri = "d:custom/sentry.process_profile.track_outcome@second"

        self._store_code_location(
            self.organization.id,
            project.id,
            mri,
            self._round_to_day(self.current_time),
            '{"lineno": 10}',
        )

        response = self.get_success_response(
            self.organization.slug,
            metric=[mri],
            project=[project.id],
            statsPeriod="1d",
        )
        metrics = response.data["metrics"]

        assert len(metrics) == 1

        assert metrics[0]["mri"] == mri
        assert metrics[0]["timestamp"] == self._round_to_day(self.current_time)

        code_locations = metrics[0]["frames"]
        assert len(code_locations) == 1
        assert code_locations[0]["lineno"] == 10
        # We check that all the remaining elements are `None`.
        del code_locations[0]["lineno"]
        for value in code_locations[0].values():
            assert value is None

    def test_get_locations_with_corrupted_location(self):
        project = self.create_project(name="project_1")
        mri = "d:custom/sentry.process_profile.track_outcome@second"

        self._store_code_location(
            self.organization.id,
            project.id,
            mri,
            self._round_to_day(self.current_time),
            '}"invalid": "json"{',
        )

        self.get_error_response(
            self.organization.slug,
            metric=[mri],
            project=[project.id],
            statsPeriod="1d",
            status_code=500,
        )

    @patch("sentry.sentry_metrics.querying.metadata.CodeLocationsFetcher.MAXIMUM_KEYS", 50)
    def test_get_locations_with_too_many_combinations(self):
        project = self.create_project(name="project_1")
        mri = "d:custom/sentry.process_profile.track_outcome@second"

        self.get_error_response(
            self.organization.slug,
            metric=[mri],
            project=[project.id],
            statsPeriod="90d",
            status_code=500,
        )
