# Implementation Plan: Intelligent Data Toolkit Framework

## Overview

Python backend (FastAPI + Celery), React/TypeScript frontend. Five-layer architecture: Profiling → Routing → Orchestration → Storage → UI.

## Tasks

- [x] 1. Data Profiling Layer (Layer 1)
  - [x] 1.1 Create core data models and interfaces
    - Define `DataProfile`, `BasicInfo`, `QualityMetrics`, `StructureInfo`, `SemanticInfo` in `src/toolkit/models/`
    - Implement `DataProfiler`, `TypeDetector`, `QualityAnalyzer`, `SemanticAnalyzer` interfaces
    - _Requirements: 1.1, 1.2, 1.3_
  - [x] 1.2 Write property tests for DataProfiler
    - **Property 1: Data Profile Completeness** — valid source → non-null basic info + quality metrics
    - **Property 2: Fingerprint Determinism** — same source → identical fingerprints
    - **Property 3: Semantic Detection for Text** — text content → non-null language and domain
    - **Validates: Requirements 1.1, 1.2, 1.3, 1.4**
  - [x] 1.3 Implement profiling algorithms
    - Staged profiling: quick (< 10s), sampling (< 30s), full analysis
    - Partial profile on timeout, fingerprint generation
    - _Requirements: 1.4, 1.5_
  - [x] 1.4 Write property test for PII detection
    - **Property 13: PII Detection** — data with PII patterns → flagged sensitive fields
    - **Validates: Requirement 8.2**

- [x] 2. Intelligent Routing Layer (Layer 2)
  - [x] 2.1 Implement StrategyRouter, RuleEngine, and CostEstimator
    - Rule-based filtering + ML-based ranking + cost optimization
    - Default strategy fallback, explainable recommendations
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 7.1_
  - [x] 2.2 Write property tests for routing
    - **Property 4: Processing Plan Completeness** — valid profile → non-empty strategies, explanation, costs
    - **Property 5: Strategy Determinism** — same inputs → same ProcessingPlan
    - **Property 12: Cost Estimation Accuracy** — estimates within 20% of actual
    - **Validates: Requirements 2.1, 2.2, 2.3, 2.5, 7.1, 7.2**

- [x] 3. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Tool Orchestration Layer (Layer 3)
  - [x] 4.1 Implement ToolRegistry with hot-plugging
    - Tool registration, discovery, version management, dependency resolution
    - _Requirements: 3.1, 3.2_
  - [x] 4.2 Write property test for tool registration
    - **Property 6: Tool Registration Round-Trip** — register tool → discoverable by capabilities
    - **Validates: Requirement 3.1**
  - [x] 4.3 Implement PipelineExecutor
    - Dependency-ordered stage execution, pause/resume/cancel, retry with backoff
    - Real-time progress events, intermediate result caching
    - _Requirements: 3.3, 3.4, 3.5, 3.6, 5.1, 5.2, 5.3, 5.4_
  - [x] 4.4 Write property tests for pipeline execution
    - **Property 7: Pipeline Dependency Ordering** — stages execute in valid topological order
    - **Property 11: Pipeline Execution Invariants** — every stage emits progress, produces output, caches result
    - **Validates: Requirements 3.3, 5.1, 5.2, 5.3**

- [x] 5. Storage Adapter Layer (Layer 4)
  - [x] 5.1 Implement StorageAbstraction and adapters
    - PostgreSQL, pgvector, Neo4j, MongoDB, TimescaleDB adapters
    - Unified query interface, intelligent storage selection, lineage tracking
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_
  - [x] 5.2 Write property tests for storage
    - **Property 8: Storage Selection Correctness** — tabular→PG, embeddings→vector, relationships→graph
    - **Property 9: Storage Round-Trip** — store + retrieve → semantically equivalent data
    - **Property 10: Lineage Completeness** — lineage traces back to source through all stages
    - **Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5**

- [x] 6. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Security and Audit
  - [x] 7.1 Implement encryption at rest/in transit and audit trail
    - Data encryption, RBAC, audit logging for all operations
    - _Requirements: 8.1, 8.3_
  - [x] 7.2 Write property test for audit trail
    - **Property 14: Audit Trail Completeness** — any operation → audit log with user, type, timestamp
    - **Validates: Requirement 8.3**

- [x] 8. User Interface Layer (Layer 5)
  - [x] 8.1 Create i18n setup and shared components
    - Configure react-i18next with zh/en namespaces, Ant Design layout
    - _Requirements: 6.1_
  - [x] 8.2 Implement data upload and strategy configuration pages
    - Drag-and-drop upload, data preview, strategy recommendation with explanation
    - Visual strategy customization, real-time cost estimation
    - _Requirements: 6.2, 6.5_
  - [x] 8.3 Implement monitoring and results pages
    - Real-time progress with stage breakdown, pause/resume controls
    - Results visualization (tables, charts), export (CSV, JSON, Excel, PDF)
    - _Requirements: 6.3, 6.4_

- [x] 9. Integration and wiring
  - [x] 9.1 Wire all layers end-to-end
    - Connect Upload → Profiling → Routing → Orchestration → Storage → Results
    - FastAPI endpoints, Celery async tasks, WebSocket progress updates
    - _Requirements: 1.1–8.3_
  - [x] 9.2 Write integration tests
    - End-to-end: Excel upload → profile → route → execute → store → query
    - End-to-end: PDF upload → chunk → embed → vector store → semantic search
    - _Requirements: 1.1–8.3_

- [x] 10. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Backend: Python 3.10+, FastAPI, Celery, Redis
- Frontend: React 18+, TypeScript, react-i18next, Ant Design
- All 14 correctness properties covered by property test tasks
- All 8 requirements covered by implementation tasks
