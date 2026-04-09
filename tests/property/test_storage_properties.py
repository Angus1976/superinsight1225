"""
Property-based tests for the Storage Adapter Layer.

Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5
"""

from hypothesis import given, settings, strategies as st

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
from src.toolkit.storage.lineage import LineageTracker
from src.toolkit.storage.storage_abstraction import StorageAbstraction


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

@st.composite
def tabular_profiles_with_schema(draw):
    """DataProfile: TABULAR structure with a non-empty column_schema."""
    cols = draw(st.dictionaries(
        keys=st.text(min_size=1, max_size=10),
        values=st.sampled_from(["int", "str", "float", "bool"]),
        min_size=1, max_size=5,
    ))
    return DataProfile(
        structure_info=StructureInfo(
            data_structure=DataStructure.TABULAR,
            column_schema=cols,
        ),
    )


@st.composite
def graph_profiles(draw):
    """DataProfile: GRAPH structure or with relationships."""
    use_graph_structure = draw(st.booleans())
    if use_graph_structure:
        return DataProfile(
            structure_info=StructureInfo(data_structure=DataStructure.GRAPH),
        )
    rels = draw(st.lists(
        st.fixed_dictionaries({"from": st.text(min_size=1, max_size=5),
                               "to": st.text(min_size=1, max_size=5)}),
        min_size=1, max_size=3,
    ))
    return DataProfile(
        structure_info=StructureInfo(relationships=rels),
    )


def hierarchical_profiles():
    """DataProfile: HIERARCHICAL structure."""
    return st.just(DataProfile(
        structure_info=StructureInfo(data_structure=DataStructure.HIERARCHICAL),
    ))


def time_series_profiles():
    """DataProfile: TIME_SERIES structure."""
    return st.just(DataProfile(
        structure_info=StructureInfo(data_structure=DataStructure.TIME_SERIES),
    ))


storable_values = st.one_of(
    st.dictionaries(
        keys=st.text(min_size=1, max_size=10),
        values=st.one_of(st.integers(), st.text(max_size=20), st.floats(allow_nan=False)),
        min_size=1, max_size=5,
    ),
    st.lists(st.integers(), min_size=1, max_size=10),
    st.text(min_size=1, max_size=50),
)


stage_names_strategy = st.lists(
    st.text(
        alphabet=st.characters(whitelist_categories=("L", "N")),
        min_size=1, max_size=15,
    ),
    min_size=1, max_size=5,
)


# ---------------------------------------------------------------------------
# Property 8: Storage Selection Correctness
# Validates: Requirements 4.1, 4.2, 4.3
#
# Given a DataProfile with specific characteristics and matching
# Requirements, select_storage returns the correct adapter type.
# ---------------------------------------------------------------------------

class TestStorageSelectionCorrectness:
    """**Validates: Requirements 4.1, 4.2, 4.3**"""

    @given(profile=tabular_profiles_with_schema())
    @settings(deadline=5000)
    def test_tabular_with_schema_selects_postgresql(self, profile: DataProfile):
        sa = StorageAbstraction()
        adapter = sa.select_storage(profile)
        assert isinstance(adapter, PostgreSQLAdapter), (
            f"Tabular data with schema should select PostgreSQL, got {type(adapter).__name__}"
        )

    @given(data=st.data())
    @settings(deadline=5000)
    def test_semantic_search_selects_vector_db(self, data):
        profile = DataProfile()
        reqs = Requirements(needs_semantic_search=True)
        sa = StorageAbstraction()
        adapter = sa.select_storage(profile, reqs)
        assert isinstance(adapter, VectorDBAdapter), (
            f"needs_semantic_search should select VectorDB, got {type(adapter).__name__}"
        )

    @given(profile=graph_profiles())
    @settings(deadline=5000)
    def test_graph_or_relationships_selects_graph_db(self, profile: DataProfile):
        sa = StorageAbstraction()
        adapter = sa.select_storage(profile)
        assert isinstance(adapter, GraphDBAdapter), (
            f"Graph data should select GraphDB, got {type(adapter).__name__}"
        )

    @given(profile=hierarchical_profiles())
    @settings(deadline=5000)
    def test_hierarchical_selects_document_db(self, profile):
        sa = StorageAbstraction()
        adapter = sa.select_storage(profile)
        assert isinstance(adapter, DocumentDBAdapter), (
            f"Hierarchical data should select DocumentDB, got {type(adapter).__name__}"
        )

    @given(profile=time_series_profiles())
    @settings(deadline=5000)
    def test_time_series_selects_time_series_db(self, profile):
        sa = StorageAbstraction()
        adapter = sa.select_storage(profile)
        assert isinstance(adapter, TimeSeriesAdapter), (
            f"Time-series data should select TimeSeriesDB, got {type(adapter).__name__}"
        )

    @given(data=st.data())
    @settings(deadline=5000)
    def test_needs_flexible_schema_selects_document_db(self, data):
        profile = DataProfile()
        reqs = Requirements(needs_flexible_schema=True)
        sa = StorageAbstraction()
        adapter = sa.select_storage(profile, reqs)
        assert isinstance(adapter, DocumentDBAdapter), (
            f"needs_flexible_schema should select DocumentDB, got {type(adapter).__name__}"
        )

    @given(data=st.data())
    @settings(deadline=5000)
    def test_needs_graph_traversal_selects_graph_db(self, data):
        profile = DataProfile()
        reqs = Requirements(needs_graph_traversal=True)
        sa = StorageAbstraction()
        adapter = sa.select_storage(profile, reqs)
        assert isinstance(adapter, GraphDBAdapter), (
            f"needs_graph_traversal should select GraphDB, got {type(adapter).__name__}"
        )

    @given(data=st.data())
    @settings(deadline=5000)
    def test_needs_time_range_queries_selects_time_series(self, data):
        profile = DataProfile()
        reqs = Requirements(needs_time_range_queries=True)
        sa = StorageAbstraction()
        adapter = sa.select_storage(profile, reqs)
        assert isinstance(adapter, TimeSeriesAdapter), (
            f"needs_time_range_queries should select TimeSeriesDB, got {type(adapter).__name__}"
        )


# ---------------------------------------------------------------------------
# Property 9: Storage Round-Trip
# Validates: Requirement 4.4
#
# For any data stored via an adapter, retrieving it by the same ID
# returns semantically equivalent data.
# ---------------------------------------------------------------------------

class TestStorageRoundTrip:
    """**Validates: Requirement 4.4**"""

    @given(data=storable_values)
    @settings(deadline=5000)
    def test_postgresql_round_trip(self, data):
        adapter = PostgreSQLAdapter()
        data_id = "rt-pg"
        adapter.store(data_id, data)
        result = adapter.retrieve(data_id)

        assert result.success, "Retrieve must succeed after store"
        assert result.data == data, "Retrieved data must equal stored data"

    @given(data=storable_values)
    @settings(deadline=5000)
    def test_document_db_round_trip(self, data):
        adapter = DocumentDBAdapter()
        data_id = "rt-doc"
        adapter.store(data_id, data)
        result = adapter.retrieve(data_id)

        assert result.success, "Retrieve must succeed after store"
        assert result.data == data, "Retrieved data must equal stored data"

    @given(data=storable_values)
    @settings(deadline=5000)
    def test_time_series_round_trip(self, data):
        adapter = TimeSeriesAdapter()
        data_id = "rt-ts"
        adapter.store(data_id, data)
        result = adapter.retrieve(data_id)

        assert result.success, "Retrieve must succeed after store"
        assert result.data == data, "Retrieved data must equal stored data"

    @given(data=storable_values)
    @settings(deadline=5000)
    def test_storage_abstraction_round_trip(self, data):
        """End-to-end round-trip through StorageAbstraction."""
        sa = StorageAbstraction()
        adapter = sa.get_adapter(StorageType.POSTGRESQL)
        store_result = sa.store_data(data, adapter, data_id="rt-sa")

        assert store_result.success, "store_data must succeed"

        query_result = sa.retrieve_data("rt-sa", adapter)
        assert query_result.success, "retrieve_data must succeed"
        assert query_result.data == data, "Retrieved data must equal stored data"


# ---------------------------------------------------------------------------
# Property 10: Lineage Completeness
# Validates: Requirement 4.5
#
# For any data_id and list of transformation stage names, recording
# source → transformations → storage produces a lineage graph where:
#   - a source node exists
#   - all transformation nodes are present
#   - a storage node exists
#   - edges connect all nodes in order
#   - we can trace back from storage to source
# ---------------------------------------------------------------------------

class TestLineageCompleteness:
    """**Validates: Requirement 4.5**"""

    @given(stage_names=stage_names_strategy)
    @settings(deadline=5000)
    def test_lineage_has_all_nodes_and_edges(self, stage_names):
        tracker = LineageTracker()
        data_id = "lineage-test"

        tracker.record_source(data_id, "upload")
        for name in stage_names:
            tracker.record_transformation(data_id, name)
        tracker.record_storage(data_id, "postgresql")

        graph = tracker.get_lineage(data_id)
        assert graph is not None, "Lineage graph must exist"

        # Source node
        assert graph.source_node is not None, "Source node must exist"
        assert graph.source_node.node_type == "source"

        # Transformation nodes
        t_nodes = graph.transformation_nodes
        assert len(t_nodes) == len(stage_names), (
            f"Expected {len(stage_names)} transformation nodes, got {len(t_nodes)}"
        )
        for node, expected_name in zip(t_nodes, stage_names):
            assert node.label == expected_name

        # Storage node
        assert graph.storage_node is not None, "Storage node must exist"
        assert graph.storage_node.node_type == "storage"

        # Total: 1 source + N transformations + 1 storage
        expected_count = 1 + len(stage_names) + 1
        assert len(graph.nodes) == expected_count
        assert len(graph.edges) == expected_count - 1

    @given(stage_names=stage_names_strategy)
    @settings(deadline=5000)
    def test_lineage_edges_form_chain(self, stage_names):
        """Edges connect consecutive nodes from source to storage."""
        tracker = LineageTracker()
        data_id = "chain-test"

        tracker.record_source(data_id, "upload")
        for name in stage_names:
            tracker.record_transformation(data_id, name)
        tracker.record_storage(data_id, "postgresql")

        graph = tracker.get_lineage(data_id)
        assert graph is not None

        # Verify each edge connects consecutive nodes
        for i, edge in enumerate(graph.edges):
            assert edge.source_id == graph.nodes[i].node_id, (
                f"Edge {i} source must be node {i}"
            )
            assert edge.target_id == graph.nodes[i + 1].node_id, (
                f"Edge {i} target must be node {i+1}"
            )

    @given(stage_names=stage_names_strategy)
    @settings(deadline=5000)
    def test_lineage_traceable_from_storage_to_source(self, stage_names):
        """Can trace back from the storage node to the source node."""
        tracker = LineageTracker()
        data_id = "trace-test"

        tracker.record_source(data_id, "upload")
        for name in stage_names:
            tracker.record_transformation(data_id, name)
        tracker.record_storage(data_id, "postgresql")

        graph = tracker.get_lineage(data_id)
        assert graph is not None

        # Build reverse lookup: target_id → source_id
        reverse = {e.target_id: e.source_id for e in graph.edges}

        # Walk backwards from storage to source
        current = graph.storage_node.node_id
        visited = [current]
        while current in reverse:
            current = reverse[current]
            visited.append(current)

        assert visited[-1] == graph.source_node.node_id, (
            "Trace-back must reach the source node"
        )
        assert len(visited) == len(graph.nodes), (
            "Trace-back must visit every node exactly once"
        )
