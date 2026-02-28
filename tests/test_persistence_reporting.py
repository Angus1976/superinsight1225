"""
Tests for the persistence validation reporting module.

Property 41: Frontend Data Persistence Verification
  - Submitted data SHALL be verifiable in the database and SHALL match
    the submitted values with correct data integrity.

Property 42: Persistence Failure Detailed Reporting
  - Failure reports SHALL identify the specific form and field that
    failed to persist correctly.

Validates: Requirements 15.3, 15.4, 15.7
"""

import json
import pytest
from uuid import uuid4, UUID as PyUUID
from datetime import datetime, timezone

from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

from tests.persistence_reporting import (
    PersistenceFailure,
    FormResult,
    PersistenceReport,
    compare_values,
    validate_persistence,
    generate_persistence_report,
    export_report_json,
)


# ── Hypothesis strategies ───────────────────────────────────────────────────

json_primitives = st.one_of(
    st.text(min_size=0, max_size=50),
    st.integers(min_value=-10_000, max_value=10_000),
    st.floats(allow_nan=False, allow_infinity=False, min_value=-1e6, max_value=1e6),
    st.booleans(),
    st.none(),
)

field_name_st = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz_",
    min_size=1,
    max_size=20,
)

form_data_st = st.dictionaries(
    keys=field_name_st,
    values=json_primitives,
    min_size=1,
    max_size=8,
)

form_id_st = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz",
    min_size=3,
    max_size=15,
)


# ═════════════════════════════════════════════════════════════════════════════
# Unit tests – compare_values
# ═════════════════════════════════════════════════════════════════════════════

class TestCompareValues:
    def test_equal_strings(self):
        assert compare_values("hello", "hello") is None

    def test_equal_ints(self):
        assert compare_values(42, 42) is None

    def test_equal_floats(self):
        assert compare_values(3.14, 3.14) is None

    def test_int_float_equivalence(self):
        assert compare_values(5, 5.0) is None

    def test_both_none(self):
        assert compare_values(None, None) is None

    def test_submitted_none_stored_not(self):
        err = compare_values(None, "abc")
        assert err is not None
        assert "mismatch" in err

    def test_submitted_not_none_stored_none(self):
        err = compare_values("abc", None)
        assert err is not None

    def test_different_strings(self):
        err = compare_values("foo", "bar")
        assert err is not None
        assert "mismatch" in err

    def test_numeric_mismatch(self):
        err = compare_values(1, 2)
        assert err is not None
        assert "numeric mismatch" in err


# ═════════════════════════════════════════════════════════════════════════════
# Unit tests – validate_persistence
# ═════════════════════════════════════════════════════════════════════════════

class TestValidatePersistence:
    def test_all_fields_match(self):
        submitted = {"name": "Task A", "count": 10}
        stored = {"name": "Task A", "count": 10}
        result = validate_persistence("form1", submitted, stored)
        assert result.total_fields == 2
        assert result.passed_fields == 2
        assert result.failed_fields == 0
        assert result.failures == []

    def test_one_field_mismatch(self):
        submitted = {"name": "Task A", "count": 10}
        stored = {"name": "Task A", "count": 99}
        result = validate_persistence("form1", submitted, stored)
        assert result.failed_fields == 1
        assert len(result.failures) == 1
        assert result.failures[0].field_name == "count"
        assert result.failures[0].form_id == "form1"

    def test_missing_stored_field(self):
        submitted = {"name": "Task A", "extra": "val"}
        stored = {"name": "Task A"}
        result = validate_persistence("form1", submitted, stored)
        assert result.failed_fields == 1
        assert result.failures[0].field_name == "extra"

    def test_empty_submitted(self):
        result = validate_persistence("form1", {}, {"name": "x"})
        assert result.total_fields == 0
        assert result.passed_fields == 0

    def test_invalid_submitted_type(self):
        result = validate_persistence("form1", "not a dict", {})
        assert result.total_fields == 0

    def test_invalid_stored_type(self):
        result = validate_persistence("form1", {"a": 1}, "not a dict")
        assert result.total_fields == 0

    def test_success_rate_all_pass(self):
        submitted = {"a": 1, "b": 2}
        stored = {"a": 1, "b": 2}
        result = validate_persistence("f", submitted, stored)
        assert result.success_rate == 1.0

    def test_success_rate_half_pass(self):
        submitted = {"a": 1, "b": 2}
        stored = {"a": 1, "b": 99}
        result = validate_persistence("f", submitted, stored)
        assert result.success_rate == pytest.approx(0.5)

    def test_success_rate_empty(self):
        result = validate_persistence("f", {}, {})
        assert result.success_rate == 0.0


# ═════════════════════════════════════════════════════════════════════════════
# Unit tests – generate_persistence_report
# ═════════════════════════════════════════════════════════════════════════════

class TestGeneratePersistenceReport:
    def test_all_forms_pass(self):
        results = [
            validate_persistence("f1", {"a": 1}, {"a": 1}),
            validate_persistence("f2", {"b": 2}, {"b": 2}),
        ]
        report = generate_persistence_report(results)
        assert report.total_forms == 2
        assert report.tested_forms == 2
        assert report.successful_persistence == 2
        assert report.failed_persistence == 0
        assert report.failures == []
        assert report.overall_success_rate == 1.0

    def test_one_form_fails(self):
        results = [
            validate_persistence("f1", {"a": 1}, {"a": 1}),
            validate_persistence("f2", {"b": 2}, {"b": 99}),
        ]
        report = generate_persistence_report(results)
        assert report.successful_persistence == 1
        assert report.failed_persistence == 1
        assert len(report.failures) == 1
        assert report.failures[0].form_id == "f2"

    def test_all_forms_fail(self):
        results = [
            validate_persistence("f1", {"a": 1}, {"a": 0}),
            validate_persistence("f2", {"b": 2}, {"b": 0}),
        ]
        report = generate_persistence_report(results)
        assert report.successful_persistence == 0
        assert report.failed_persistence == 2
        assert report.overall_success_rate == 0.0

    def test_empty_results(self):
        report = generate_persistence_report([])
        assert report.total_forms == 0
        assert report.tested_forms == 0
        assert report.overall_success_rate == 0.0

    def test_total_forms_override(self):
        results = [validate_persistence("f1", {"a": 1}, {"a": 1})]
        report = generate_persistence_report(results, total_forms=5)
        assert report.total_forms == 5
        assert report.tested_forms == 1

    def test_generated_at_populated(self):
        report = generate_persistence_report([])
        assert report.generated_at != ""

    def test_form_results_preserved(self):
        results = [
            validate_persistence("f1", {"a": 1, "b": 2}, {"a": 1, "b": 2}),
        ]
        report = generate_persistence_report(results)
        assert len(report.form_results) == 1
        assert report.form_results[0].form_id == "f1"


# ═════════════════════════════════════════════════════════════════════════════
# Unit tests – export_report_json
# ═════════════════════════════════════════════════════════════════════════════

class TestExportReportJson:
    def test_valid_json(self):
        results = [validate_persistence("f1", {"a": 1}, {"a": 1})]
        report = generate_persistence_report(results)
        raw = export_report_json(report)
        data = json.loads(raw)
        assert data["total_forms"] == 1
        assert data["overall_success_rate"] == 1.0

    def test_failure_details_in_json(self):
        results = [validate_persistence("f1", {"x": "a"}, {"x": "b"})]
        report = generate_persistence_report(results)
        raw = export_report_json(report)
        data = json.loads(raw)
        assert len(data["failures"]) == 1
        assert data["failures"][0]["field_name"] == "x"
        assert data["failures"][0]["form_id"] == "f1"

    def test_form_success_rate_in_json(self):
        results = [
            validate_persistence("f1", {"a": 1, "b": 2}, {"a": 1, "b": 99}),
        ]
        report = generate_persistence_report(results)
        raw = export_report_json(report)
        data = json.loads(raw)
        assert data["form_results"][0]["success_rate"] == pytest.approx(0.5)


# ═════════════════════════════════════════════════════════════════════════════
# Property-based tests
# ═════════════════════════════════════════════════════════════════════════════

class TestProperty41PersistenceVerification:
    """
    **Validates: Requirements 15.3, 15.4**

    Property 41: Frontend Data Persistence Verification
    For any frontend form submission, the submitted data SHALL be
    verifiable in the database and SHALL match the submitted values.
    """

    @given(data=form_data_st)
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_identical_data_always_passes(self, data):
        """When stored data equals submitted data, all fields pass."""
        result = validate_persistence("prop_form", data, dict(data))
        assert result.failed_fields == 0
        assert result.passed_fields == result.total_fields
        assert result.success_rate == 1.0

    @given(data=form_data_st, extra_key=field_name_st, extra_val=json_primitives)
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_extra_stored_fields_do_not_cause_failure(self, data, extra_key, extra_val):
        """Extra columns in DB that weren't submitted don't count as failures."""
        stored = dict(data)
        stored[extra_key + "_extra"] = extra_val
        result = validate_persistence("prop_form", data, stored)
        assert result.failed_fields == 0

    @given(data=form_data_st)
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_empty_stored_detects_all_failures(self, data):
        """If nothing was stored, every non-None submitted field is a failure."""
        result = validate_persistence("prop_form", data, {})
        non_none_count = sum(1 for v in data.values() if v is not None)
        assert result.failed_fields == non_none_count


class TestProperty42FailureReporting:
    """
    **Validates: Requirements 15.7**

    Property 42: Persistence Failure Detailed Reporting
    For any data persistence failure, the failure report SHALL identify
    the specific form and field that failed to persist correctly.
    """

    @given(form_id=form_id_st, data=form_data_st)
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_failures_identify_form_and_field(self, form_id, data):
        """Every failure entry carries the correct form_id and field_name."""
        # Corrupt stored data so every field fails
        corrupted = {k: "__CORRUPTED__" for k in data}
        result = validate_persistence(form_id, data, corrupted)

        for failure in result.failures:
            assert failure.form_id == form_id
            assert failure.field_name in data
            assert failure.error_message != ""

    @given(form_id=form_id_st, data=form_data_st)
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_failure_report_includes_submitted_and_stored(self, form_id, data):
        """Each failure records both the submitted and stored values."""
        corrupted = {k: "__BAD__" for k in data}
        result = validate_persistence(form_id, data, corrupted)

        for failure in result.failures:
            assert failure.submitted_value == data[failure.field_name]
            assert failure.stored_value == "__BAD__"

    @given(
        results=st.lists(
            st.tuples(form_id_st, form_data_st),
            min_size=1,
            max_size=5,
        )
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_report_aggregates_all_failures(self, results):
        """The report collects failures from every form result."""
        form_results = []
        expected_failure_count = 0
        for fid, data in results:
            corrupted = {k: "__X__" for k in data}
            fr = validate_persistence(fid, data, corrupted)
            form_results.append(fr)
            expected_failure_count += fr.failed_fields

        report = generate_persistence_report(form_results)
        assert len(report.failures) == expected_failure_count
        # Every failure has a non-empty form_id and field_name
        for f in report.failures:
            assert f.form_id != ""
            assert f.field_name != ""


# ═════════════════════════════════════════════════════════════════════════════
# Integration test – real API persistence round-trip
# ═════════════════════════════════════════════════════════════════════════════

class TestPersistenceRoundTrip:
    """
    End-to-end validation: submit data via the API, read it back from
    the database, and run the persistence report.

    Uses the same SQLite in-memory approach as test_data_type_persistence.py.
    """

    @pytest.fixture()
    def env(self):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.pool import StaticPool
        from sqlalchemy.ext.compiler import compiles
        from sqlalchemy.dialects.postgresql import JSONB, INET
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from src.database.connection import Base, get_db_session
        from src.security.models import UserModel
        from src.security.controller import SecurityController
        from src.database.models import TaskModel

        @compiles(JSONB, "sqlite")
        def _jsonb(t, c, **kw):
            return "JSON"

        @compiles(INET, "sqlite")
        def _inet(t, c, **kw):
            return "VARCHAR(45)"

        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=engine)
        sf = sessionmaker(autocommit=False, autoflush=False, bind=engine)

        sc = SecurityController(secret_key="test-secret")
        with sf() as s:
            user = UserModel(
                id=uuid4(), username="tester", email="t@example.com",
                password_hash=sc.hash_password("Pass123!"),
                full_name="Tester", role="admin",
                tenant_id="test_tenant", is_active=True,
            )
            s.add(user)
            s.commit()
            s.refresh(user)

        from src.api.auth_simple import SimpleUser, get_current_user as gcu_simple
        from src.api.tasks import router as tasks_router
        from src.api.auth import router as auth_router, get_current_user as gcu_auth

        fake = SimpleUser(
            user_id=str(user.id), email=user.email,
            username=user.username, name=user.full_name,
            is_active=True, is_superuser=False,
        )
        fake.tenant_id = "test_tenant"

        app = FastAPI()
        app.include_router(tasks_router)
        app.include_router(auth_router)

        def _db():
            sess = sf()
            try:
                yield sess
            finally:
                sess.close()

        async def _user():
            return fake

        app.dependency_overrides[get_db_session] = _db
        app.dependency_overrides[gcu_simple] = _user
        app.dependency_overrides[gcu_auth] = _user

        yield TestClient(app), sf, TaskModel

        Base.metadata.drop_all(bind=engine)
        engine.dispose()

    def test_task_persistence_report(self, env):
        """Submit a task via API, verify DB, and generate report."""
        client, sf, TaskModel = env

        submitted = {"name": "Report task", "total_items": 42}
        resp = client.post("/api/tasks", json=submitted)
        assert resp.status_code == 200
        task_id = resp.json()["id"]

        with sf() as s:
            task = s.query(TaskModel).filter_by(id=PyUUID(task_id)).first()
            stored = {"name": task.name, "total_items": task.total_items}

        result = validate_persistence("taskCreate", submitted, stored)
        report = generate_persistence_report([result])

        assert report.successful_persistence == 1
        assert report.failed_persistence == 0
        assert report.overall_success_rate == 1.0

        raw = export_report_json(report)
        data = json.loads(raw)
        assert data["overall_success_rate"] == 1.0
