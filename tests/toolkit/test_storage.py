"""
Unit tests for the Storage Adapter Layer.

Validates Requirements 4.1–4.6:
  4.1 Tabular + schema → PostgreSQL
  4.2 Embeddings / semantic search → vector DB
  4.3 Dense relationships → graph DB
  4.4 Store + retrieve → semantically equivalent
  4.5 Lineage from source through all transformations
  4.6 Primary failure → cache locally and sync when restored
"""

import pytest

from src.toolkit.models.data_profile import DataProfile, StructureInfo
from src.toolkit.models.enums import DataStructure
from src.toolkit.models.processing_plan import Requirements, StorageType
from src.toolkit.storage.adapters import (
    DocumentDBAdapter,
    GraphDBAdapter,
    PostgreSQLAdapter,
    TimeSeriesAdapter,
    VectorDBAdapter,
)
from src.toolkit.storage.base import StorageAdapter
from src.toolkit.storage.lineage import LineageTracker
from src.toolkit.storage.storage_abstraction import StorageAbstraction


# -----------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------

def _tabular_profile() -> DataProfile:
    return DataProfile(
        structure_info=StructureInfo(
            data_structure=DataStructure.TABULAR,
            column_schema={"id": "int", "name": "str"},
        ),
    )


def _vector_profile() -> DataProfile:
    return DataProfile(
        structure_info=StructureInfo(data_structure=DataStructure.TEXT),
    )


def _graph_profile() -> DataProfile:
    return DataProfile(
        structure_info=StructureInfo(
            data_structure=DataStructure.GRAPH,
            relationships=[{"from": "A", "to": "B"}],
        ),
    )


def _timeseries_profile() -> DataProfile:
    return DataProfile(
        structure_info=StructureInfo(data_structure=DataStructure.TIME_SERIES),
    )


def _hierarchical_profile() -> DataProfile:
    return DataProfile(
        structure_info=StructureInfo(data_structure=DataStructure.HIERARCHICAL),
    )


# -----------------------------------------------------------------------
# Storage Selection  (Req 4.1, 4.2, 4.3)
# -----------------------------------------------------------------------

class TestStorageSelection:
    """Intelligent storage selection based on data profile."""

    def test_tabular_with_schema_selects_postgresql(self):
        """Req 4.1: tabular + schema → PostgreSQL."""
        sa = StorageAbstraction()
        adapter = sa.select_storage(_tabular_profile())
        assert adapter.storage_type == StorageType.POSTGRESQL

    def test_semantic_search_selects_vector_db(self):
        """Req 4.2: needs_semantic_search → vector DB."""
        sa = StorageAbstraction()
        reqs = Requirements(needs_semantic_search=True)
        adapter = sa.select_storage(_vector_profile(), reqs)
        assert adapter.storage_type == StorageType.VECTOR_DB

    def test_graph_data_selects_graph_db(self):
        """Req 4.3: graph structure → graph DB."""
        sa = StorageAbstraction()
        adapter = sa.select_storage(_graph_profile())
        assert adapter.storage_type == StorageType.GRAPH_DB

    def test_time_series_selects_timeseries_db(self):
        sa = StorageAbstraction()
        adapter = sa.select_storage(_timeseries_profile())
        assert adapter.storage_type == StorageType.TIME_SERIES_DB

    def test_hierarchical_selects_document_db(self):
        sa = StorageAbstraction()
        adapter = sa.select_storage(_hierarchical_profile())
        assert adapter.storage_type == StorageType.DOCUMENT_DB

    def test_flexible_schema_requirement_selects_document_db(self):
        sa = StorageAbstraction()
        reqs = Requirements(needs_flexible_schema=True)
        adapter = sa.select_storage(DataProfile(), reqs)
        assert adapter.storage_type == StorageType.DOCUMENT_DB

    def test_time_range_requirement_selects_timeseries(self):
        sa = StorageAbstraction()
        reqs = Requirements(needs_time_range_queries=True)
        adapter = sa.select_storage(DataProfile(), reqs)
        assert adapter.storage_type == StorageType.TIME_SERIES_DB

    def test_no_match_falls_back_to_postgresql(self):
        sa = StorageAbstraction()
        adapter = sa.select_storage(DataProfile())
        assert adapter.storage_type == StorageType.POSTGRESQL

    def test_selection_is_deterministic(self):
        """Same inputs → same adapter type."""
        sa = StorageAbstraction()
        profile = _tabular_profile()
        a1 = sa.select_storage(profile)
        a2 = sa.select_storage(profile)
        assert a1.storage_type == a2.storage_type


# -----------------------------------------------------------------------
# Adapter round-trip  (Req 4.4)
# -----------------------------------------------------------------------

class TestAdapterRoundTrip:
    """Store + retrieve → semantically equivalent data."""

    @pytest.mark.parametrize("adapter_cls,payload", [
        (PostgreSQLAdapter, {"id": 1, "name": "Alice"}),
        (VectorDBAdapter, [0.1, 0.2, 0.3]),
        (GraphDBAdapter, {"label": "Person", "name": "Bob"}),
        (DocumentDBAdapter, {"nested": {"key": "value"}}),
        (TimeSeriesAdapter, [{"ts": 1, "val": 42}]),
    ])
    def test_store_and_retrieve(self, adapter_cls, payload):
        adapter = adapter_cls()
        result = adapter.store("d1", payload)
        assert result.success is True
        assert result.data_id == "d1"

        retrieved = adapter.retrieve("d1")
        assert retrieved.success is True
        # VectorDB wraps in {"embedding": ..., "metadata": ...}
        # GraphDB wraps in {"node": ..., "edges": ...}
        if isinstance(adapter, VectorDBAdapter):
            assert retrieved.data["embedding"] == payload
        elif isinstance(adapter, GraphDBAdapter):
            assert retrieved.data["node"] == payload
        else:
            assert retrieved.data == payload

    def test_retrieve_nonexistent_returns_failure(self):
        adapter = PostgreSQLAdapter()
        result = adapter.retrieve("missing")
        assert result.success is False

    def test_delete_removes_data(self):
        adapter = DocumentDBAdapter()
        adapter.store("x", {"a": 1})
        assert adapter.delete("x") is True
        assert adapter.retrieve("x").success is False

    def test_delete_nonexistent_returns_false(self):
        adapter = PostgreSQLAdapter()
        assert adapter.delete("nope") is False


# -----------------------------------------------------------------------
# Unified store/retrieve via StorageAbstraction  (Req 4.4)
# -----------------------------------------------------------------------

class TestStorageAbstractionRoundTrip:
    """Store and retrieve through the unified abstraction layer."""

    def test_store_and_retrieve_via_abstraction(self):
        sa = StorageAbstraction()
        adapter = sa.get_adapter(StorageType.POSTGRESQL)
        payload = {"col": "value"}

        store_result = sa.store_data(payload, adapter, data_id="r1", source_label="test")
        assert store_result.success is True

        retrieve_result = sa.retrieve_data("r1", adapter)
        assert retrieve_result.success is True
        assert retrieve_result.data == payload

    def test_retrieve_nonexistent_returns_failure(self):
        sa = StorageAbstraction()
        adapter = sa.get_adapter(StorageType.POSTGRESQL)
        result = sa.retrieve_data("missing", adapter)
        assert result.success is False


# -----------------------------------------------------------------------
# Lineage tracking  (Req 4.5)
# -----------------------------------------------------------------------

class TestLineageTracking:
    """Lineage from source through all transformations to storage."""

    def test_full_lineage_chain(self):
        sa = StorageAbstraction()
        adapter = sa.get_adapter(StorageType.POSTGRESQL)

        sa.store_data({"x": 1}, adapter, data_id="L1", source_label="upload.csv")
        sa.record_transformation("L1", "clean")
        sa.record_transformation("L1", "normalize")

        graph = sa.track_lineage("L1")
        assert graph is not None
        assert graph.data_id == "L1"
        assert graph.source_node is not None
        assert graph.source_node.label == "upload.csv"
        assert len(graph.transformation_nodes) == 2
        assert graph.storage_node is not None

    def test_lineage_edges_connect_all_nodes(self):
        sa = StorageAbstraction()
        adapter = sa.get_adapter(StorageType.DOCUMENT_DB)

        sa.store_data("doc", adapter, data_id="L2", source_label="api")
        sa.record_transformation("L2", "parse")

        graph = sa.track_lineage("L2")
        assert len(graph.edges) == len(graph.nodes) - 1

    def test_no_lineage_for_unknown_id(self):
        sa = StorageAbstraction()
        assert sa.track_lineage("unknown") is None


class TestLineageTracker:
    """Direct LineageTracker unit tests."""

    def test_record_source_creates_graph(self):
        lt = LineageTracker()
        lt.record_source("d1", "file.csv")
        graph = lt.get_lineage("d1")
        assert graph is not None
        assert len(graph.nodes) == 1
        assert graph.source_node.label == "file.csv"

    def test_transformation_without_source_is_noop(self):
        lt = LineageTracker()
        lt.record_transformation("nope", "stage1")
        assert lt.get_lineage("nope") is None

    def test_has_lineage(self):
        lt = LineageTracker()
        assert lt.has_lineage("x") is False
        lt.record_source("x", "src")
        assert lt.has_lineage("x") is True


# -----------------------------------------------------------------------
# Local cache fallback  (Req 4.6)
# -----------------------------------------------------------------------

class TestLocalCacheFallback:
    """On primary failure → cache locally and sync when restored."""

    def test_unavailable_adapter_caches_locally(self):
        sa = StorageAbstraction()
        adapter = sa.get_adapter(StorageType.POSTGRESQL)
        adapter._available = False  # simulate failure

        result = sa.store_data({"a": 1}, adapter, data_id="C1", source_label="src")
        assert result.success is True
        assert result.metadata.get("cached_locally") is True
        assert sa.cached_count == 1

    def test_retrieve_from_cache_when_adapter_down(self):
        sa = StorageAbstraction()
        adapter = sa.get_adapter(StorageType.POSTGRESQL)
        adapter._available = False

        sa.store_data({"b": 2}, adapter, data_id="C2", source_label="src")
        retrieved = sa.retrieve_data("C2", adapter)
        assert retrieved.success is True
        assert retrieved.data == {"b": 2}
        assert retrieved.metadata.get("from_cache") is True

    def test_sync_flushes_cache_when_restored(self):
        sa = StorageAbstraction()
        adapter = sa.get_adapter(StorageType.POSTGRESQL)
        adapter._available = False

        sa.store_data({"c": 3}, adapter, data_id="C3", source_label="src")
        assert sa.cached_count == 1

        # Restore availability
        adapter._available = True
        synced = sa.sync_cached_data()
        assert "C3" in synced
        assert sa.cached_count == 0

        # Data now retrievable from adapter
        result = adapter.retrieve("C3")
        assert result.success is True
        assert result.data == {"c": 3}

    def test_sync_skips_still_unavailable(self):
        sa = StorageAbstraction()
        adapter = sa.get_adapter(StorageType.POSTGRESQL)
        adapter._available = False

        sa.store_data("val", adapter, data_id="C4", source_label="src")
        synced = sa.sync_cached_data()
        assert synced == []
        assert sa.cached_count == 1


# -----------------------------------------------------------------------
# Adapter query tests
# -----------------------------------------------------------------------

class TestAdapterQueries:
    """Basic query functionality for each adapter."""

    def test_postgresql_query_by_table_prefix(self):
        adapter = PostgreSQLAdapter()
        adapter.store("users:1", {"name": "A"})
        adapter.store("users:2", {"name": "B"})
        adapter.store("orders:1", {"item": "X"})

        result = adapter.query({"table": "users"})
        assert result.record_count == 2

    def test_vector_query_top_k(self):
        adapter = VectorDBAdapter()
        for i in range(5):
            adapter.store(f"v{i}", [float(i)])
        result = adapter.query({"top_k": 3})
        assert result.record_count == 3

    def test_graph_query_connected_edges(self):
        adapter = GraphDBAdapter()
        adapter.store("n1", {"label": "A"}, edges=[
            {"source": "n1", "target": "n2"},
        ])
        adapter.store("n2", {"label": "B"})
        result = adapter.query({"start_node": "n1"})
        assert result.success is True
        assert result.record_count == 1

    def test_document_query_field_match(self):
        adapter = DocumentDBAdapter()
        adapter.store("d1", {"type": "invoice", "amount": 100})
        adapter.store("d2", {"type": "receipt", "amount": 50})
        result = adapter.query({"field": "type", "value": "invoice"})
        assert result.record_count == 1

    def test_timeseries_query_by_series_id(self):
        adapter = TimeSeriesAdapter()
        adapter.store("ts1", [{"ts": 1, "v": 10}])
        result = adapter.query({"series_id": "ts1"})
        assert result.success is True


# -----------------------------------------------------------------------
# Adapter availability
# -----------------------------------------------------------------------

class TestAdapterAvailability:
    def test_all_adapters_available_by_default(self):
        for cls in [PostgreSQLAdapter, VectorDBAdapter, GraphDBAdapter,
                    DocumentDBAdapter, TimeSeriesAdapter]:
            assert cls().is_available() is True


# -----------------------------------------------------------------------
# get_adapter
# -----------------------------------------------------------------------

class TestGetAdapter:
    def test_unsupported_type_raises(self):
        sa = StorageAbstraction()
        with pytest.raises(ValueError, match="Unsupported"):
            sa.get_adapter("invalid_type")  # type: ignore

    def test_same_type_returns_same_instance(self):
        sa = StorageAbstraction()
        a1 = sa.get_adapter(StorageType.POSTGRESQL)
        a2 = sa.get_adapter(StorageType.POSTGRESQL)
        assert a1 is a2
