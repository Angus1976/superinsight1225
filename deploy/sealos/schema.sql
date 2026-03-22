--
-- PostgreSQL database dump
--


-- Dumped from database version 15.17 (Debian 15.17-1.pgdg12+1)
-- Dumped by pg_dump version 15.17 (Debian 15.17-1.pgdg12+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: vector; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;


--
-- Name: action; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.action AS ENUM (
    'VIEW',
    'EDIT',
    'DELETE',
    'TRANSFER',
    'REVIEW',
    'ANNOTATE',
    'ENHANCE',
    'TRIAL'
);


--
-- Name: annotationtype; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.annotationtype AS ENUM (
    'CLASSIFICATION',
    'ENTITY_RECOGNITION',
    'RELATION_EXTRACTION',
    'SENTIMENT_ANALYSIS',
    'CUSTOM'
);


--
-- Name: changetype; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.changetype AS ENUM (
    'INITIAL',
    'ANNOTATION',
    'ENHANCEMENT',
    'CORRECTION',
    'MERGE'
);


--
-- Name: datastage; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.datastage AS ENUM (
    'TEMP_TABLE',
    'SAMPLE_LIBRARY',
    'DATA_SOURCE',
    'ANNOTATED',
    'ENHANCED'
);


--
-- Name: datastate; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.datastate AS ENUM (
    'RAW',
    'STRUCTURED',
    'TEMP_STORED',
    'UNDER_REVIEW',
    'REJECTED',
    'APPROVED',
    'IN_SAMPLE_LIBRARY',
    'ANNOTATION_PENDING',
    'ANNOTATING',
    'ANNOTATED',
    'ENHANCING',
    'ENHANCED',
    'TRIAL_CALCULATION',
    'ARCHIVED'
);


--
-- Name: enhancementtype; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.enhancementtype AS ENUM (
    'DATA_AUGMENTATION',
    'QUALITY_IMPROVEMENT',
    'NOISE_REDUCTION',
    'FEATURE_EXTRACTION',
    'NORMALIZATION'
);


--
-- Name: jobstatus; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.jobstatus AS ENUM (
    'QUEUED',
    'RUNNING',
    'COMPLETED',
    'FAILED',
    'CANCELLED'
);


--
-- Name: operationresult; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.operationresult AS ENUM (
    'SUCCESS',
    'FAILURE',
    'PARTIAL'
);


--
-- Name: operationtype; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.operationtype AS ENUM (
    'CREATE',
    'READ',
    'UPDATE',
    'DELETE',
    'TRANSFER',
    'STATE_CHANGE'
);


--
-- Name: resourcetype; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.resourcetype AS ENUM (
    'TEMP_DATA',
    'SAMPLE',
    'ANNOTATION_TASK',
    'ANNOTATED_DATA',
    'ENHANCED_DATA',
    'TRIAL'
);


--
-- Name: reviewstatus; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.reviewstatus AS ENUM (
    'PENDING',
    'IN_PROGRESS',
    'APPROVED',
    'REJECTED'
);


--
-- Name: taskstatus; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.taskstatus AS ENUM (
    'CREATED',
    'IN_PROGRESS',
    'COMPLETED',
    'CANCELLED'
);


--
-- Name: trialstatus; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.trialstatus AS ENUM (
    'CREATED',
    'RUNNING',
    'COMPLETED',
    'FAILED'
);


SET default_table_access_method = heap;

--
-- Name: ai_access_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ai_access_logs (
    id integer NOT NULL,
    tenant_id character varying(100) NOT NULL,
    user_id character varying(100) NOT NULL,
    user_role character varying(50),
    event_type character varying(50) NOT NULL,
    resource_id character varying(200),
    resource_name character varying(255),
    api_key_id character varying(100),
    request_type character varying(50),
    success boolean DEFAULT true NOT NULL,
    error_message text,
    details jsonb DEFAULT '{}'::jsonb NOT NULL,
    duration_ms integer,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: ai_access_logs_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.ai_access_logs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: ai_access_logs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.ai_access_logs_id_seq OWNED BY public.ai_access_logs.id;


--
-- Name: ai_audit_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ai_audit_logs (
    id character varying(36) NOT NULL,
    gateway_id character varying(36) NOT NULL,
    tenant_id character varying(36) NOT NULL,
    event_type character varying(50) NOT NULL,
    resource character varying(255) NOT NULL,
    action character varying(50) NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    user_identifier character varying(255),
    channel character varying(50),
    success boolean DEFAULT true NOT NULL,
    error_message text,
    "timestamp" timestamp with time zone DEFAULT now() NOT NULL,
    signature character varying(255) NOT NULL
);


--
-- Name: ai_data_source_config; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ai_data_source_config (
    id character varying NOT NULL,
    label character varying NOT NULL,
    description character varying DEFAULT ''::character varying,
    enabled boolean DEFAULT true,
    access_mode character varying DEFAULT 'read'::character varying,
    config json DEFAULT '{}'::json,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: ai_data_source_role_permission; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ai_data_source_role_permission (
    id integer NOT NULL,
    role character varying(50) NOT NULL,
    source_id character varying(100) NOT NULL,
    allowed boolean DEFAULT false NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: ai_data_source_role_permission_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.ai_data_source_role_permission_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: ai_data_source_role_permission_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.ai_data_source_role_permission_id_seq OWNED BY public.ai_data_source_role_permission.id;


--
-- Name: ai_gateways; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ai_gateways (
    id character varying(36) NOT NULL,
    name character varying(255) NOT NULL,
    gateway_type character varying(50) NOT NULL,
    tenant_id character varying(36) NOT NULL,
    status character varying(20) DEFAULT 'inactive'::character varying NOT NULL,
    configuration jsonb DEFAULT '{}'::jsonb NOT NULL,
    api_key_hash character varying(255) NOT NULL,
    api_secret_hash character varying(255) NOT NULL,
    rate_limit_per_minute integer DEFAULT 60 NOT NULL,
    quota_per_day integer DEFAULT 10000 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    last_active_at timestamp with time zone
);


--
-- Name: ai_skill_role_permission; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ai_skill_role_permission (
    id integer NOT NULL,
    role character varying(50) NOT NULL,
    skill_id character varying(100) NOT NULL,
    allowed boolean DEFAULT false NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: ai_skill_role_permission_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.ai_skill_role_permission_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: ai_skill_role_permission_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.ai_skill_role_permission_id_seq OWNED BY public.ai_skill_role_permission.id;


--
-- Name: ai_skills; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ai_skills (
    id character varying(36) NOT NULL,
    gateway_id character varying(36) NOT NULL,
    name character varying(255) NOT NULL,
    version character varying(50) NOT NULL,
    code_path character varying(500) NOT NULL,
    configuration jsonb DEFAULT '{}'::jsonb NOT NULL,
    dependencies jsonb DEFAULT '[]'::jsonb NOT NULL,
    status character varying(20) DEFAULT 'pending'::character varying NOT NULL,
    deployed_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: ai_workflows; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ai_workflows (
    id character varying(36) NOT NULL,
    name character varying(255) NOT NULL,
    description text DEFAULT ''::text,
    status character varying(20) DEFAULT 'enabled'::character varying NOT NULL,
    is_preset boolean DEFAULT false NOT NULL,
    skill_ids jsonb DEFAULT '[]'::jsonb NOT NULL,
    data_source_auth jsonb DEFAULT '[]'::jsonb NOT NULL,
    output_modes jsonb DEFAULT '[]'::jsonb NOT NULL,
    visible_roles jsonb DEFAULT '[]'::jsonb NOT NULL,
    preset_prompt text,
    name_en character varying(255),
    description_en text,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    created_by character varying(100)
);


--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alembic_version (
    version_num character varying(128) NOT NULL
);


--
-- Name: annotation_tasks; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.annotation_tasks (
    id uuid NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    sample_ids jsonb NOT NULL,
    annotation_type public.annotationtype NOT NULL,
    instructions text NOT NULL,
    status public.taskstatus DEFAULT 'CREATED'::public.taskstatus NOT NULL,
    created_by character varying(255) NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    assigned_to jsonb DEFAULT '[]'::jsonb NOT NULL,
    deadline timestamp without time zone,
    completed_at timestamp without time zone,
    progress_total integer DEFAULT 0 NOT NULL,
    progress_completed integer DEFAULT 0 NOT NULL,
    progress_in_progress integer DEFAULT 0 NOT NULL,
    annotations jsonb DEFAULT '[]'::jsonb NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    lock_version integer DEFAULT 1 NOT NULL,
    CONSTRAINT check_progress_completed_positive CHECK ((progress_completed >= 0)),
    CONSTRAINT check_progress_in_progress_positive CHECK ((progress_in_progress >= 0)),
    CONSTRAINT check_progress_total_positive CHECK ((progress_total >= 0))
);


--
-- Name: approval_requests; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.approval_requests (
    id character varying(36) NOT NULL,
    transfer_request jsonb NOT NULL,
    requester_id character varying(36) NOT NULL,
    requester_role character varying(20) NOT NULL,
    status character varying(20) DEFAULT 'pending'::character varying NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    expires_at timestamp without time zone NOT NULL,
    approver_id character varying(36),
    approved_at timestamp without time zone,
    comment text
);


--
-- Name: audit_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.audit_logs (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid,
    tenant_id character varying(255) DEFAULT 'system'::character varying,
    action character varying(100),
    resource_type character varying(100),
    resource_id character varying(255),
    ip_address character varying(45),
    user_agent text,
    details json,
    "timestamp" timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: data_lifecycle_audit_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.data_lifecycle_audit_logs (
    id uuid NOT NULL,
    operation_type public.operationtype NOT NULL,
    user_id character varying(255) NOT NULL,
    resource_type public.resourcetype NOT NULL,
    resource_id character varying(255) NOT NULL,
    action public.action NOT NULL,
    result public.operationresult NOT NULL,
    duration integer NOT NULL,
    error text,
    details jsonb DEFAULT '{}'::jsonb NOT NULL,
    ip_address character varying(45),
    user_agent character varying(500),
    "timestamp" timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: data_sources; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.data_sources (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    tenant_id character varying(100) NOT NULL,
    name character varying(200) NOT NULL,
    description text,
    source_type character varying(50) NOT NULL,
    status character varying(50) DEFAULT 'active'::character varying NOT NULL,
    connection_config jsonb DEFAULT '{}'::jsonb NOT NULL,
    schema_config jsonb DEFAULT '{}'::jsonb,
    pool_size integer DEFAULT 5,
    max_overflow integer DEFAULT 10,
    connection_timeout integer DEFAULT 30,
    last_health_check timestamp with time zone,
    health_check_status character varying(50),
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    created_by character varying(100)
);


--
-- Name: datalake_metrics; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.datalake_metrics (
    id uuid NOT NULL,
    source_id uuid NOT NULL,
    tenant_id character varying(100) NOT NULL,
    metric_type character varying(50) NOT NULL,
    metric_data jsonb NOT NULL,
    recorded_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: enhanced_data; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.enhanced_data (
    id uuid NOT NULL,
    original_data_id character varying(255) NOT NULL,
    enhancement_job_id uuid NOT NULL,
    content jsonb NOT NULL,
    enhancement_type public.enhancementtype NOT NULL,
    quality_improvement double precision NOT NULL,
    quality_overall double precision NOT NULL,
    quality_completeness double precision NOT NULL,
    quality_accuracy double precision NOT NULL,
    quality_consistency double precision NOT NULL,
    version integer DEFAULT 1 NOT NULL,
    parameters jsonb DEFAULT '{}'::jsonb NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT check_enhanced_quality_accuracy_range CHECK (((quality_accuracy >= (0)::double precision) AND (quality_accuracy <= (1)::double precision))),
    CONSTRAINT check_enhanced_quality_completeness_range CHECK (((quality_completeness >= (0)::double precision) AND (quality_completeness <= (1)::double precision))),
    CONSTRAINT check_enhanced_quality_consistency_range CHECK (((quality_consistency >= (0)::double precision) AND (quality_consistency <= (1)::double precision))),
    CONSTRAINT check_enhanced_quality_overall_range CHECK (((quality_overall >= (0)::double precision) AND (quality_overall <= (1)::double precision))),
    CONSTRAINT check_enhanced_version_positive CHECK ((version > 0))
);


--
-- Name: label_studio_projects; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.label_studio_projects (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    task_id uuid,
    label_studio_project_id integer,
    label_studio_project_name character varying(255),
    status character varying(50) DEFAULT 'pending'::character varying,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    tenant_id character varying(255) DEFAULT 'system'::character varying
);


--
-- Name: llm_application_bindings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.llm_application_bindings (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    llm_config_id uuid NOT NULL,
    application_id uuid NOT NULL,
    priority integer NOT NULL,
    max_retries integer DEFAULT 3 NOT NULL,
    timeout_seconds integer DEFAULT 30 NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    CONSTRAINT llm_application_bindings_max_retries_check CHECK (((max_retries >= 0) AND (max_retries <= 10))),
    CONSTRAINT llm_application_bindings_priority_check CHECK (((priority >= 1) AND (priority <= 99))),
    CONSTRAINT llm_application_bindings_timeout_seconds_check CHECK ((timeout_seconds > 0))
);


--
-- Name: llm_applications; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.llm_applications (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    code character varying(50) NOT NULL,
    name character varying(100) NOT NULL,
    description text,
    llm_usage_pattern text,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


--
-- Name: llm_configurations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.llm_configurations (
    id uuid NOT NULL,
    tenant_id uuid,
    config_data jsonb DEFAULT '{}'::jsonb NOT NULL,
    default_method character varying(50) DEFAULT 'local_ollama'::character varying NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    is_default boolean DEFAULT false NOT NULL,
    name character varying(255),
    description text,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    created_by uuid,
    updated_by uuid,
    provider character varying(50) NOT NULL
);


--
-- Name: llm_model_registry; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.llm_model_registry (
    id uuid NOT NULL,
    method character varying(50) NOT NULL,
    model_id character varying(100) NOT NULL,
    model_name character varying(255) NOT NULL,
    supports_chat boolean DEFAULT true NOT NULL,
    supports_completion boolean DEFAULT true NOT NULL,
    supports_embedding boolean DEFAULT false NOT NULL,
    supports_streaming boolean DEFAULT true NOT NULL,
    max_tokens integer,
    context_window integer,
    description text,
    model_metadata jsonb,
    is_available boolean DEFAULT true NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


--
-- Name: llm_usage_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.llm_usage_logs (
    id uuid NOT NULL,
    tenant_id uuid,
    user_id uuid,
    method character varying(50) NOT NULL,
    model character varying(100) NOT NULL,
    operation character varying(50) DEFAULT 'generate'::character varying NOT NULL,
    prompt_tokens integer DEFAULT 0 NOT NULL,
    completion_tokens integer DEFAULT 0 NOT NULL,
    total_tokens integer DEFAULT 0 NOT NULL,
    latency_ms double precision DEFAULT 0.0 NOT NULL,
    success boolean DEFAULT true NOT NULL,
    error_code character varying(50),
    error_message text,
    request_metadata jsonb,
    response_metadata jsonb,
    created_at timestamp without time zone DEFAULT now() NOT NULL
);


--
-- Name: permissions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.permissions (
    id uuid NOT NULL,
    user_id character varying(255) NOT NULL,
    resource_type public.resourcetype NOT NULL,
    resource_id character varying(255) NOT NULL,
    actions jsonb NOT NULL,
    granted_by character varying(255) NOT NULL,
    granted_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    expires_at timestamp without time zone,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL
);


--
-- Name: samples; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.samples (
    id uuid NOT NULL,
    data_id character varying(255) NOT NULL,
    content jsonb NOT NULL,
    category character varying(100) NOT NULL,
    quality_overall double precision NOT NULL,
    quality_completeness double precision NOT NULL,
    quality_accuracy double precision NOT NULL,
    quality_consistency double precision NOT NULL,
    version integer DEFAULT 1 NOT NULL,
    tags jsonb DEFAULT '[]'::jsonb NOT NULL,
    usage_count integer DEFAULT 0 NOT NULL,
    last_used_at timestamp without time zone,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    lock_version integer DEFAULT 1 NOT NULL,
    CONSTRAINT check_quality_accuracy_range CHECK (((quality_accuracy >= (0)::double precision) AND (quality_accuracy <= (1)::double precision))),
    CONSTRAINT check_quality_completeness_range CHECK (((quality_completeness >= (0)::double precision) AND (quality_completeness <= (1)::double precision))),
    CONSTRAINT check_quality_consistency_range CHECK (((quality_consistency >= (0)::double precision) AND (quality_consistency <= (1)::double precision))),
    CONSTRAINT check_quality_overall_range CHECK (((quality_overall >= (0)::double precision) AND (quality_overall <= (1)::double precision))),
    CONSTRAINT check_version_positive CHECK ((version > 0))
);


--
-- Name: semantic_records; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.semantic_records (
    id uuid NOT NULL,
    job_id uuid NOT NULL,
    record_type character varying(20) NOT NULL,
    content jsonb NOT NULL,
    confidence double precision DEFAULT 0.0 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: structured_records; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.structured_records (
    id uuid NOT NULL,
    job_id uuid NOT NULL,
    fields jsonb DEFAULT '{}'::jsonb NOT NULL,
    confidence double precision DEFAULT '0'::double precision NOT NULL,
    source_span text,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: structuring_jobs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.structuring_jobs (
    id uuid NOT NULL,
    tenant_id character varying(100) NOT NULL,
    file_name character varying(500) NOT NULL,
    file_path character varying(1000) NOT NULL,
    file_type character varying(20) NOT NULL,
    status character varying(30) DEFAULT 'pending'::character varying NOT NULL,
    raw_content text,
    inferred_schema jsonb,
    confirmed_schema jsonb,
    record_count integer DEFAULT 0 NOT NULL,
    error_message text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    processing_type character varying(20) DEFAULT 'structuring'::character varying NOT NULL,
    chunk_count integer,
    progress_info jsonb
);


--
-- Name: tasks; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tasks (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    title character varying(255) NOT NULL,
    description text,
    status character varying(50) DEFAULT 'pending'::character varying,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    created_by uuid,
    tenant_id character varying(255) DEFAULT 'system'::character varying,
    name character varying(255) NOT NULL,
    priority character varying(50) DEFAULT 'medium'::character varying,
    annotation_type character varying(50) DEFAULT 'custom'::character varying,
    assignee_id uuid,
    progress integer DEFAULT 0,
    total_items integer DEFAULT 1,
    completed_items integer DEFAULT 0,
    due_date timestamp without time zone,
    tags jsonb DEFAULT '[]'::jsonb,
    task_metadata jsonb DEFAULT '{}'::jsonb,
    document_id uuid,
    project_id character varying(100) DEFAULT 'default_project'::character varying NOT NULL,
    annotations jsonb DEFAULT '[]'::jsonb,
    ai_predictions jsonb DEFAULT '[]'::jsonb,
    quality_score double precision DEFAULT 0.0,
    sync_status character varying(50),
    sync_version integer DEFAULT 1,
    last_synced_at timestamp without time zone,
    sync_execution_id character varying(36),
    is_from_sync boolean DEFAULT false,
    sync_metadata jsonb DEFAULT '{}'::jsonb,
    label_studio_project_id character varying(50),
    label_studio_project_created_at timestamp without time zone,
    label_studio_sync_status character varying(50) DEFAULT 'pending'::character varying,
    label_studio_last_sync timestamp without time zone,
    label_studio_task_count integer DEFAULT 0,
    label_studio_annotation_count integer DEFAULT 0
);


--
-- Name: temp_data; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.temp_data (
    id uuid NOT NULL,
    source_document_id character varying(255) NOT NULL,
    content jsonb NOT NULL,
    state public.datastate NOT NULL,
    uploaded_by character varying(255) NOT NULL,
    uploaded_at timestamp without time zone NOT NULL,
    review_status public.reviewstatus,
    reviewed_by character varying(255),
    reviewed_at timestamp without time zone,
    rejection_reason text,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    lock_version integer DEFAULT 1 NOT NULL
);


--
-- Name: transfer_audit_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.transfer_audit_logs (
    id character varying(36) NOT NULL,
    user_id character varying(36) NOT NULL,
    user_role character varying(20) NOT NULL,
    operation character varying(50) NOT NULL,
    source_type character varying(20) NOT NULL,
    source_id character varying(36) NOT NULL,
    target_state character varying(30) NOT NULL,
    record_count integer NOT NULL,
    success boolean NOT NULL,
    error_message text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    id uuid NOT NULL,
    email character varying(255) NOT NULL,
    username character varying(100),
    name character varying(200),
    first_name character varying(100),
    last_name character varying(100),
    is_active boolean NOT NULL,
    is_verified boolean NOT NULL,
    is_superuser boolean NOT NULL,
    password_hash character varying(255),
    sso_id character varying(255),
    sso_provider character varying(50),
    sso_attributes json,
    avatar_url character varying(500),
    timezone character varying(50) NOT NULL,
    language character varying(10) NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    last_login_at timestamp without time zone,
    user_metadata json,
    full_name character varying(255),
    role character varying(50) DEFAULT 'viewer'::character varying,
    tenant_id character varying(100) DEFAULT 'default_tenant'::character varying,
    last_login timestamp with time zone
);


--
-- Name: vector_records; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.vector_records (
    id uuid NOT NULL,
    job_id uuid NOT NULL,
    chunk_index integer NOT NULL,
    chunk_text text NOT NULL,
    embedding public.vector(1536) NOT NULL,
    metadata jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: versions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.versions (
    id uuid NOT NULL,
    data_id character varying(255) NOT NULL,
    version_number integer NOT NULL,
    content jsonb NOT NULL,
    change_type public.changetype NOT NULL,
    description text,
    parent_version_id uuid,
    checksum character varying(64) NOT NULL,
    tags jsonb DEFAULT '[]'::jsonb NOT NULL,
    created_by character varying(255) NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    CONSTRAINT check_version_number_positive CHECK ((version_number > 0))
);


--
-- Name: ai_access_logs id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ai_access_logs ALTER COLUMN id SET DEFAULT nextval('public.ai_access_logs_id_seq'::regclass);


--
-- Name: ai_data_source_role_permission id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ai_data_source_role_permission ALTER COLUMN id SET DEFAULT nextval('public.ai_data_source_role_permission_id_seq'::regclass);


--
-- Name: ai_skill_role_permission id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ai_skill_role_permission ALTER COLUMN id SET DEFAULT nextval('public.ai_skill_role_permission_id_seq'::regclass);


--
-- Name: ai_access_logs ai_access_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ai_access_logs
    ADD CONSTRAINT ai_access_logs_pkey PRIMARY KEY (id);


--
-- Name: ai_audit_logs ai_audit_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ai_audit_logs
    ADD CONSTRAINT ai_audit_logs_pkey PRIMARY KEY (id);


--
-- Name: ai_data_source_config ai_data_source_config_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ai_data_source_config
    ADD CONSTRAINT ai_data_source_config_pkey PRIMARY KEY (id);


--
-- Name: ai_data_source_role_permission ai_data_source_role_permission_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ai_data_source_role_permission
    ADD CONSTRAINT ai_data_source_role_permission_pkey PRIMARY KEY (id);


--
-- Name: ai_gateways ai_gateways_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ai_gateways
    ADD CONSTRAINT ai_gateways_pkey PRIMARY KEY (id);


--
-- Name: ai_skill_role_permission ai_skill_role_permission_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ai_skill_role_permission
    ADD CONSTRAINT ai_skill_role_permission_pkey PRIMARY KEY (id);


--
-- Name: ai_skills ai_skills_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ai_skills
    ADD CONSTRAINT ai_skills_pkey PRIMARY KEY (id);


--
-- Name: ai_workflows ai_workflows_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ai_workflows
    ADD CONSTRAINT ai_workflows_name_key UNIQUE (name);


--
-- Name: ai_workflows ai_workflows_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ai_workflows
    ADD CONSTRAINT ai_workflows_pkey PRIMARY KEY (id);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: annotation_tasks annotation_tasks_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.annotation_tasks
    ADD CONSTRAINT annotation_tasks_pkey PRIMARY KEY (id);


--
-- Name: approval_requests approval_requests_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.approval_requests
    ADD CONSTRAINT approval_requests_pkey PRIMARY KEY (id);


--
-- Name: audit_logs audit_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT audit_logs_pkey PRIMARY KEY (id);


--
-- Name: data_lifecycle_audit_logs data_lifecycle_audit_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.data_lifecycle_audit_logs
    ADD CONSTRAINT data_lifecycle_audit_logs_pkey PRIMARY KEY (id);


--
-- Name: data_sources data_sources_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.data_sources
    ADD CONSTRAINT data_sources_pkey PRIMARY KEY (id);


--
-- Name: datalake_metrics datalake_metrics_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.datalake_metrics
    ADD CONSTRAINT datalake_metrics_pkey PRIMARY KEY (id);


--
-- Name: enhanced_data enhanced_data_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.enhanced_data
    ADD CONSTRAINT enhanced_data_pkey PRIMARY KEY (id);


--
-- Name: label_studio_projects label_studio_projects_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.label_studio_projects
    ADD CONSTRAINT label_studio_projects_pkey PRIMARY KEY (id);


--
-- Name: llm_application_bindings llm_application_bindings_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.llm_application_bindings
    ADD CONSTRAINT llm_application_bindings_pkey PRIMARY KEY (id);


--
-- Name: llm_applications llm_applications_code_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.llm_applications
    ADD CONSTRAINT llm_applications_code_key UNIQUE (code);


--
-- Name: llm_applications llm_applications_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.llm_applications
    ADD CONSTRAINT llm_applications_pkey PRIMARY KEY (id);


--
-- Name: llm_configurations llm_configurations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.llm_configurations
    ADD CONSTRAINT llm_configurations_pkey PRIMARY KEY (id);


--
-- Name: llm_model_registry llm_model_registry_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.llm_model_registry
    ADD CONSTRAINT llm_model_registry_pkey PRIMARY KEY (id);


--
-- Name: llm_usage_logs llm_usage_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.llm_usage_logs
    ADD CONSTRAINT llm_usage_logs_pkey PRIMARY KEY (id);


--
-- Name: permissions permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.permissions
    ADD CONSTRAINT permissions_pkey PRIMARY KEY (id);


--
-- Name: samples samples_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.samples
    ADD CONSTRAINT samples_pkey PRIMARY KEY (id);


--
-- Name: semantic_records semantic_records_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.semantic_records
    ADD CONSTRAINT semantic_records_pkey PRIMARY KEY (id);


--
-- Name: structured_records structured_records_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.structured_records
    ADD CONSTRAINT structured_records_pkey PRIMARY KEY (id);


--
-- Name: structuring_jobs structuring_jobs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.structuring_jobs
    ADD CONSTRAINT structuring_jobs_pkey PRIMARY KEY (id);


--
-- Name: tasks tasks_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_pkey PRIMARY KEY (id);


--
-- Name: temp_data temp_data_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.temp_data
    ADD CONSTRAINT temp_data_pkey PRIMARY KEY (id);


--
-- Name: transfer_audit_logs transfer_audit_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.transfer_audit_logs
    ADD CONSTRAINT transfer_audit_logs_pkey PRIMARY KEY (id);


--
-- Name: llm_application_bindings uq_app_priority; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.llm_application_bindings
    ADD CONSTRAINT uq_app_priority UNIQUE (application_id, priority);


--
-- Name: ai_skill_role_permission uq_role_skill; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ai_skill_role_permission
    ADD CONSTRAINT uq_role_skill UNIQUE (role, skill_id);


--
-- Name: ai_data_source_role_permission uq_role_source; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ai_data_source_role_permission
    ADD CONSTRAINT uq_role_source UNIQUE (role, source_id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: vector_records vector_records_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.vector_records
    ADD CONSTRAINT vector_records_pkey PRIMARY KEY (id);


--
-- Name: versions versions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.versions
    ADD CONSTRAINT versions_pkey PRIMARY KEY (id);


--
-- Name: idx_access_log_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_access_log_created_at ON public.ai_access_logs USING btree (created_at);


--
-- Name: idx_access_log_event_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_access_log_event_type ON public.ai_access_logs USING btree (event_type);


--
-- Name: idx_access_log_tenant_time; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_access_log_tenant_time ON public.ai_access_logs USING btree (tenant_id, created_at);


--
-- Name: idx_access_log_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_access_log_user ON public.ai_access_logs USING btree (user_id);


--
-- Name: idx_annotation_tasks_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_annotation_tasks_created_at ON public.annotation_tasks USING btree (created_at);


--
-- Name: idx_annotation_tasks_created_by; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_annotation_tasks_created_by ON public.annotation_tasks USING btree (created_by);


--
-- Name: idx_annotation_tasks_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_annotation_tasks_status ON public.annotation_tasks USING btree (status);


--
-- Name: idx_annotation_tasks_status_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_annotation_tasks_status_created ON public.annotation_tasks USING btree (status, created_by);


--
-- Name: idx_approval_requests_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_approval_requests_created_at ON public.approval_requests USING btree (created_at);


--
-- Name: idx_approval_requests_requester; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_approval_requests_requester ON public.approval_requests USING btree (requester_id);


--
-- Name: idx_approval_requests_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_approval_requests_status ON public.approval_requests USING btree (status);


--
-- Name: idx_bindings_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_bindings_active ON public.llm_application_bindings USING btree (is_active);


--
-- Name: idx_bindings_app_priority; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_bindings_app_priority ON public.llm_application_bindings USING btree (application_id, priority);


--
-- Name: idx_data_sources_tenant_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_data_sources_tenant_type ON public.data_sources USING btree (tenant_id, source_type);


--
-- Name: idx_datalake_metrics_source_recorded; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_datalake_metrics_source_recorded ON public.datalake_metrics USING btree (source_id, recorded_at);


--
-- Name: idx_datalake_metrics_tenant_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_datalake_metrics_tenant_type ON public.datalake_metrics USING btree (tenant_id, metric_type);


--
-- Name: idx_dl_audit_logs_operation_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_dl_audit_logs_operation_type ON public.data_lifecycle_audit_logs USING btree (operation_type);


--
-- Name: idx_dl_audit_logs_resource_timestamp; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_dl_audit_logs_resource_timestamp ON public.data_lifecycle_audit_logs USING btree (resource_type, "timestamp");


--
-- Name: idx_dl_audit_logs_resource_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_dl_audit_logs_resource_type ON public.data_lifecycle_audit_logs USING btree (resource_type);


--
-- Name: idx_dl_audit_logs_result; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_dl_audit_logs_result ON public.data_lifecycle_audit_logs USING btree (result);


--
-- Name: idx_dl_audit_logs_timestamp; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_dl_audit_logs_timestamp ON public.data_lifecycle_audit_logs USING btree ("timestamp");


--
-- Name: idx_dl_audit_logs_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_dl_audit_logs_user_id ON public.data_lifecycle_audit_logs USING btree (user_id);


--
-- Name: idx_dl_audit_logs_user_timestamp; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_dl_audit_logs_user_timestamp ON public.data_lifecycle_audit_logs USING btree (user_id, "timestamp");


--
-- Name: idx_enhanced_data_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_enhanced_data_created_at ON public.enhanced_data USING btree (created_at);


--
-- Name: idx_enhanced_data_original_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_enhanced_data_original_id ON public.enhanced_data USING btree (original_data_id);


--
-- Name: idx_llm_applications_code; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX idx_llm_applications_code ON public.llm_applications USING btree (code);


--
-- Name: idx_permissions_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_permissions_user_id ON public.permissions USING btree (user_id);


--
-- Name: idx_permissions_user_resource; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_permissions_user_resource ON public.permissions USING btree (user_id, resource_type, resource_id);


--
-- Name: idx_role_permission_role; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_role_permission_role ON public.ai_data_source_role_permission USING btree (role);


--
-- Name: idx_role_permission_source_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_role_permission_source_id ON public.ai_data_source_role_permission USING btree (source_id);


--
-- Name: idx_samples_category; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_samples_category ON public.samples USING btree (category);


--
-- Name: idx_samples_category_quality; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_samples_category_quality ON public.samples USING btree (category, quality_overall);


--
-- Name: idx_samples_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_samples_created_at ON public.samples USING btree (created_at);


--
-- Name: idx_semantic_records_job_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_semantic_records_job_id ON public.semantic_records USING btree (job_id);


--
-- Name: idx_skill_perm_role; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_skill_perm_role ON public.ai_skill_role_permission USING btree (role);


--
-- Name: idx_skill_perm_skill_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_skill_perm_skill_id ON public.ai_skill_role_permission USING btree (skill_id);


--
-- Name: idx_structured_records_job_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_structured_records_job_id ON public.structured_records USING btree (job_id);


--
-- Name: idx_structuring_jobs_tenant_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_structuring_jobs_tenant_status ON public.structuring_jobs USING btree (tenant_id, status);


--
-- Name: idx_tasks_assignee_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tasks_assignee_id ON public.tasks USING btree (assignee_id);


--
-- Name: idx_tasks_document_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tasks_document_id ON public.tasks USING btree (document_id);


--
-- Name: idx_tasks_label_studio_project_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tasks_label_studio_project_id ON public.tasks USING btree (label_studio_project_id);


--
-- Name: idx_tasks_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tasks_name ON public.tasks USING btree (name);


--
-- Name: idx_tasks_priority; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tasks_priority ON public.tasks USING btree (priority);


--
-- Name: idx_tasks_project_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tasks_project_id ON public.tasks USING btree (project_id);


--
-- Name: idx_temp_data_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_temp_data_created_at ON public.temp_data USING btree (created_at);


--
-- Name: idx_temp_data_state; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_temp_data_state ON public.temp_data USING btree (state);


--
-- Name: idx_temp_data_state_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_temp_data_state_user ON public.temp_data USING btree (state, uploaded_by);


--
-- Name: idx_temp_data_uploaded_by; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_temp_data_uploaded_by ON public.temp_data USING btree (uploaded_by);


--
-- Name: idx_transfer_audit_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_transfer_audit_created_at ON public.transfer_audit_logs USING btree (created_at);


--
-- Name: idx_transfer_audit_source; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_transfer_audit_source ON public.transfer_audit_logs USING btree (source_type, source_id);


--
-- Name: idx_transfer_audit_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_transfer_audit_user ON public.transfer_audit_logs USING btree (user_id);


--
-- Name: idx_vector_records_job_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_vector_records_job_id ON public.vector_records USING btree (job_id);


--
-- Name: idx_versions_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_versions_created_at ON public.versions USING btree (created_at);


--
-- Name: idx_versions_data_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_versions_data_id ON public.versions USING btree (data_id);


--
-- Name: idx_versions_data_id_version; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_versions_data_id_version ON public.versions USING btree (data_id, version_number);


--
-- Name: idx_workflow_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_workflow_name ON public.ai_workflows USING btree (name);


--
-- Name: idx_workflow_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_workflow_status ON public.ai_workflows USING btree (status);


--
-- Name: ix_ai_audit_logs_event_timestamp; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ai_audit_logs_event_timestamp ON public.ai_audit_logs USING btree (event_type, "timestamp");


--
-- Name: ix_ai_audit_logs_event_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ai_audit_logs_event_type ON public.ai_audit_logs USING btree (event_type);


--
-- Name: ix_ai_audit_logs_gateway_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ai_audit_logs_gateway_id ON public.ai_audit_logs USING btree (gateway_id);


--
-- Name: ix_ai_audit_logs_gateway_timestamp; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ai_audit_logs_gateway_timestamp ON public.ai_audit_logs USING btree (gateway_id, "timestamp");


--
-- Name: ix_ai_audit_logs_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ai_audit_logs_tenant_id ON public.ai_audit_logs USING btree (tenant_id);


--
-- Name: ix_ai_audit_logs_tenant_timestamp; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ai_audit_logs_tenant_timestamp ON public.ai_audit_logs USING btree (tenant_id, "timestamp");


--
-- Name: ix_ai_audit_logs_timestamp; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ai_audit_logs_timestamp ON public.ai_audit_logs USING btree ("timestamp");


--
-- Name: ix_ai_gateways_gateway_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ai_gateways_gateway_type ON public.ai_gateways USING btree (gateway_type);


--
-- Name: ix_ai_gateways_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ai_gateways_status ON public.ai_gateways USING btree (status);


--
-- Name: ix_ai_gateways_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ai_gateways_tenant_id ON public.ai_gateways USING btree (tenant_id);


--
-- Name: ix_ai_gateways_tenant_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ai_gateways_tenant_status ON public.ai_gateways USING btree (tenant_id, status);


--
-- Name: ix_ai_skills_gateway_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ai_skills_gateway_id ON public.ai_skills USING btree (gateway_id);


--
-- Name: ix_ai_skills_gateway_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ai_skills_gateway_status ON public.ai_skills USING btree (gateway_id, status);


--
-- Name: ix_ai_skills_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ai_skills_status ON public.ai_skills USING btree (status);


--
-- Name: ix_datalake_metrics_recorded_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_datalake_metrics_recorded_at ON public.datalake_metrics USING btree (recorded_at);


--
-- Name: ix_datalake_metrics_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_datalake_metrics_tenant_id ON public.datalake_metrics USING btree (tenant_id);


--
-- Name: ix_llm_config_method; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_llm_config_method ON public.llm_configurations USING btree (default_method);


--
-- Name: ix_llm_config_tenant_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_llm_config_tenant_active ON public.llm_configurations USING btree (tenant_id, is_active);


--
-- Name: ix_llm_config_tenant_default; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_llm_config_tenant_default ON public.llm_configurations USING btree (tenant_id, is_default);


--
-- Name: ix_llm_config_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_llm_config_tenant_id ON public.llm_configurations USING btree (tenant_id);


--
-- Name: ix_llm_model_available; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_llm_model_available ON public.llm_model_registry USING btree (is_available);


--
-- Name: ix_llm_model_method_id; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_llm_model_method_id ON public.llm_model_registry USING btree (method, model_id);


--
-- Name: ix_llm_usage_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_llm_usage_created_at ON public.llm_usage_logs USING btree (created_at);


--
-- Name: ix_llm_usage_method; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_llm_usage_method ON public.llm_usage_logs USING btree (method);


--
-- Name: ix_llm_usage_method_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_llm_usage_method_created ON public.llm_usage_logs USING btree (method, created_at);


--
-- Name: ix_llm_usage_model; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_llm_usage_model ON public.llm_usage_logs USING btree (model);


--
-- Name: ix_llm_usage_success; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_llm_usage_success ON public.llm_usage_logs USING btree (success, created_at);


--
-- Name: ix_llm_usage_tenant_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_llm_usage_tenant_created ON public.llm_usage_logs USING btree (tenant_id, created_at);


--
-- Name: ix_llm_usage_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_llm_usage_tenant_id ON public.llm_usage_logs USING btree (tenant_id);


--
-- Name: ix_llm_usage_user_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_llm_usage_user_created ON public.llm_usage_logs USING btree (user_id, created_at);


--
-- Name: ix_llm_usage_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_llm_usage_user_id ON public.llm_usage_logs USING btree (user_id);


--
-- Name: ix_structuring_jobs_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_structuring_jobs_tenant_id ON public.structuring_jobs USING btree (tenant_id);


--
-- Name: ix_users_email; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_users_email ON public.users USING btree (email);


--
-- Name: ix_users_sso_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_users_sso_id ON public.users USING btree (sso_id);


--
-- Name: ix_users_sso_provider; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_users_sso_provider ON public.users USING btree (sso_provider);


--
-- Name: ix_users_username; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_users_username ON public.users USING btree (username);


--
-- Name: ai_audit_logs ai_audit_logs_gateway_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ai_audit_logs
    ADD CONSTRAINT ai_audit_logs_gateway_id_fkey FOREIGN KEY (gateway_id) REFERENCES public.ai_gateways(id) ON DELETE CASCADE;


--
-- Name: ai_skills ai_skills_gateway_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ai_skills
    ADD CONSTRAINT ai_skills_gateway_id_fkey FOREIGN KEY (gateway_id) REFERENCES public.ai_gateways(id) ON DELETE CASCADE;


--
-- Name: datalake_metrics datalake_metrics_source_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.datalake_metrics
    ADD CONSTRAINT datalake_metrics_source_id_fkey FOREIGN KEY (source_id) REFERENCES public.data_sources(id) ON DELETE CASCADE;


--
-- Name: llm_application_bindings llm_application_bindings_application_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.llm_application_bindings
    ADD CONSTRAINT llm_application_bindings_application_id_fkey FOREIGN KEY (application_id) REFERENCES public.llm_applications(id) ON DELETE CASCADE;


--
-- Name: llm_application_bindings llm_application_bindings_llm_config_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.llm_application_bindings
    ADD CONSTRAINT llm_application_bindings_llm_config_id_fkey FOREIGN KEY (llm_config_id) REFERENCES public.llm_configurations(id) ON DELETE CASCADE;


--
-- Name: semantic_records semantic_records_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.semantic_records
    ADD CONSTRAINT semantic_records_job_id_fkey FOREIGN KEY (job_id) REFERENCES public.structuring_jobs(id) ON DELETE CASCADE;


--
-- Name: structured_records structured_records_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.structured_records
    ADD CONSTRAINT structured_records_job_id_fkey FOREIGN KEY (job_id) REFERENCES public.structuring_jobs(id) ON DELETE CASCADE;


--
-- Name: vector_records vector_records_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.vector_records
    ADD CONSTRAINT vector_records_job_id_fkey FOREIGN KEY (job_id) REFERENCES public.structuring_jobs(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--


