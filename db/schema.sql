--
-- PostgreSQL database dump
--

\restrict 8yghBE68puhEM8nUlcekG5X0imIFkmY3kzPea9U6KuldG6kChGNadDO2gCyE7i4

-- Dumped from database version 17.6
-- Dumped by pg_dump version 18.4

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: app; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA app;


--
-- Name: core; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA core;


--
-- Name: log_metric_value_change(); Type: FUNCTION; Schema: core; Owner: -
--

CREATE FUNCTION core.log_metric_value_change() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
  IF TG_OP = 'INSERT' THEN
    INSERT INTO core.metric_value_audit (metric_value_id, change_type, old_value, new_value)
    VALUES (NEW.id, 'insert', NULL, NEW.value);
  ELSIF TG_OP = 'UPDATE' AND NEW.value IS DISTINCT FROM OLD.value THEN
    INSERT INTO core.metric_value_audit (metric_value_id, change_type, old_value, new_value)
    VALUES (NEW.id, 'update', OLD.value, NEW.value);
  END IF;
  RETURN NEW;
END;
$$;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: accounts; Type: TABLE; Schema: app; Owner: -
--

CREATE TABLE app.accounts (
    user_id uuid NOT NULL,
    type text NOT NULL,
    provider text NOT NULL,
    provider_account_id text NOT NULL,
    refresh_token text,
    access_token text,
    expires_at integer,
    token_type text,
    scope text,
    id_token text,
    session_state text
);


--
-- Name: agency_requests; Type: TABLE; Schema: app; Owner: -
--

CREATE TABLE app.agency_requests (
    id bigint NOT NULL,
    agency_id bigint,
    requested_name text,
    email text,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: agency_requests_id_seq; Type: SEQUENCE; Schema: app; Owner: -
--

ALTER TABLE app.agency_requests ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME app.agency_requests_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: conversion_events; Type: TABLE; Schema: app; Owner: -
--

CREATE TABLE app.conversion_events (
    id bigint NOT NULL,
    event_type text NOT NULL,
    agency_id bigint,
    user_id bigint,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT conversion_events_event_type_check CHECK ((event_type = ANY (ARRAY['wall_hit'::text, 'gate_view'::text, 'checkout_start'::text, 'paid'::text])))
);


--
-- Name: conversion_events_id_seq; Type: SEQUENCE; Schema: app; Owner: -
--

ALTER TABLE app.conversion_events ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME app.conversion_events_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: sessions; Type: TABLE; Schema: app; Owner: -
--

CREATE TABLE app.sessions (
    session_token text NOT NULL,
    user_id uuid NOT NULL,
    expires timestamp with time zone NOT NULL
);


--
-- Name: users; Type: TABLE; Schema: app; Owner: -
--

CREATE TABLE app.users (
    id bigint NOT NULL,
    email text NOT NULL,
    auth_provider text,
    subscription_status text,
    subscription_source text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    auth_id uuid DEFAULT gen_random_uuid() NOT NULL,
    name text,
    image text,
    email_verified timestamp with time zone,
    CONSTRAINT users_subscription_status_check CHECK ((subscription_status = ANY (ARRAY['active'::text, 'inactive'::text, 'trialing'::text, 'past_due'::text])))
);


--
-- Name: users_id_seq; Type: SEQUENCE; Schema: app; Owner: -
--

ALTER TABLE app.users ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME app.users_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: verification_token; Type: TABLE; Schema: app; Owner: -
--

CREATE TABLE app.verification_token (
    identifier text NOT NULL,
    token text NOT NULL,
    expires timestamp with time zone NOT NULL
);


--
-- Name: watchlists; Type: TABLE; Schema: app; Owner: -
--

CREATE TABLE app.watchlists (
    user_id bigint NOT NULL,
    agency_id bigint NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: agencies; Type: TABLE; Schema: core; Owner: -
--

CREATE TABLE core.agencies (
    id bigint NOT NULL,
    slug text NOT NULL,
    legal_name text NOT NULL,
    short_name text,
    country text DEFAULT 'CA'::text NOT NULL,
    subdivision text NOT NULL,
    service_area_population integer,
    primary_modes text[],
    fiscal_year_end_month smallint DEFAULT 12 NOT NULL,
    currency text DEFAULT 'CAD'::text NOT NULL,
    parent_agency_id bigint,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT agencies_fiscal_year_end_month_check CHECK (((fiscal_year_end_month >= 1) AND (fiscal_year_end_month <= 12)))
);


--
-- Name: agencies_id_seq; Type: SEQUENCE; Schema: core; Owner: -
--

ALTER TABLE core.agencies ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME core.agencies_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: agency_modes; Type: TABLE; Schema: core; Owner: -
--

CREATE TABLE core.agency_modes (
    agency_id bigint NOT NULL,
    mode_id bigint NOT NULL,
    year_started smallint,
    status text DEFAULT 'active'::text NOT NULL,
    CONSTRAINT agency_modes_status_check CHECK ((status = ANY (ARRAY['active'::text, 'planned'::text, 'discontinued'::text])))
);


--
-- Name: feed_runs; Type: TABLE; Schema: core; Owner: -
--

CREATE TABLE core.feed_runs (
    id bigint NOT NULL,
    feed_id bigint NOT NULL,
    started_at timestamp with time zone,
    finished_at timestamp with time zone,
    status text,
    rows_fetched integer,
    schema_fingerprint text,
    last_good_at timestamp with time zone,
    message text,
    CONSTRAINT feed_runs_status_check CHECK ((status = ANY (ARRAY['ok'::text, 'stalled'::text, 'schema_break'::text, 'error'::text])))
);


--
-- Name: feed_runs_id_seq; Type: SEQUENCE; Schema: core; Owner: -
--

ALTER TABLE core.feed_runs ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME core.feed_runs_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: metric_equations; Type: TABLE; Schema: core; Owner: -
--

CREATE TABLE core.metric_equations (
    equation_code text NOT NULL,
    kind text NOT NULL,
    defines text,
    display text NOT NULL,
    CONSTRAINT metric_equations_kind_check CHECK ((kind = ANY (ARRAY['sum'::text, 'ratio'::text])))
);


--
-- Name: metric_ranks; Type: TABLE; Schema: core; Owner: -
--

CREATE TABLE core.metric_ranks (
    id bigint NOT NULL,
    agency_id bigint NOT NULL,
    metric_id bigint NOT NULL,
    reporting_period_id bigint NOT NULL,
    comparison_set text NOT NULL,
    rank integer,
    denominator integer,
    direction text,
    computed_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT metric_ranks_comparison_set_check CHECK ((comparison_set = ANY (ARRAY['all'::text, 'subdivision'::text])))
);


--
-- Name: metric_ranks_id_seq; Type: SEQUENCE; Schema: core; Owner: -
--

ALTER TABLE core.metric_ranks ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME core.metric_ranks_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: metric_value_audit; Type: TABLE; Schema: core; Owner: -
--

CREATE TABLE core.metric_value_audit (
    id bigint NOT NULL,
    metric_value_id bigint NOT NULL,
    changed_at timestamp with time zone DEFAULT now() NOT NULL,
    changed_by text DEFAULT CURRENT_USER NOT NULL,
    change_type text NOT NULL,
    old_value numeric,
    new_value numeric,
    reason text
);


--
-- Name: metric_value_audit_id_seq; Type: SEQUENCE; Schema: core; Owner: -
--

ALTER TABLE core.metric_value_audit ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME core.metric_value_audit_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: metric_value_derivation_inputs; Type: TABLE; Schema: core; Owner: -
--

CREATE TABLE core.metric_value_derivation_inputs (
    derivation_id bigint NOT NULL,
    input_metric_value_id bigint NOT NULL
);


--
-- Name: metric_value_derivations; Type: TABLE; Schema: core; Owner: -
--

CREATE TABLE core.metric_value_derivations (
    id bigint NOT NULL,
    metric_value_id bigint NOT NULL,
    equation_code text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: metric_value_derivations_id_seq; Type: SEQUENCE; Schema: core; Owner: -
--

ALTER TABLE core.metric_value_derivations ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME core.metric_value_derivations_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: metric_value_sources; Type: TABLE; Schema: core; Owner: -
--

CREATE TABLE core.metric_value_sources (
    metric_value_id bigint NOT NULL,
    source_document_id bigint NOT NULL,
    page_number integer,
    table_reference text,
    extraction_method text,
    confidence numeric,
    CONSTRAINT metric_value_sources_confidence_check CHECK (((confidence >= (0)::numeric) AND (confidence <= (1)::numeric))),
    CONSTRAINT metric_value_sources_extraction_method_check CHECK ((extraction_method = ANY (ARRAY['manual'::text, 'llm_assisted'::text, 'structured_import'::text, 'statcan_passthrough'::text])))
);


--
-- Name: metric_values; Type: TABLE; Schema: core; Owner: -
--

CREATE TABLE core.metric_values (
    id bigint NOT NULL,
    agency_id bigint NOT NULL,
    metric_id bigint NOT NULL,
    reporting_period_id bigint NOT NULL,
    mode_id bigint,
    service_scope text NOT NULL,
    value numeric NOT NULL,
    unit text NOT NULL,
    currency text,
    quality text NOT NULL,
    comparable_flag boolean DEFAULT true NOT NULL,
    crosscheck_value numeric,
    crosscheck_source_document_id bigint,
    restatement_of_id bigint,
    is_current boolean DEFAULT true NOT NULL,
    notes text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT metric_values_quality_check CHECK ((quality = ANY (ARRAY['verified'::text, 'preliminary'::text, 'estimated'::text, 'imputed'::text]))),
    CONSTRAINT metric_values_service_scope_check CHECK ((service_scope = ANY (ARRAY['conventional'::text, 'specialized'::text, 'total'::text, 'system_wide'::text])))
);


--
-- Name: metric_values_id_seq; Type: SEQUENCE; Schema: core; Owner: -
--

ALTER TABLE core.metric_values ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME core.metric_values_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: metrics; Type: TABLE; Schema: core; Owner: -
--

CREATE TABLE core.metrics (
    id bigint NOT NULL,
    code text NOT NULL,
    display_name text NOT NULL,
    description text,
    unit text NOT NULL,
    unit_type text,
    applicable_modes text[],
    is_derived boolean DEFAULT false NOT NULL,
    formula text,
    higher_is_better boolean,
    cuta_reference text,
    ntd_reference text,
    CONSTRAINT metrics_unit_type_check CHECK ((unit_type = ANY (ARRAY['count'::text, 'ratio'::text, 'currency'::text, 'time'::text, 'distance'::text])))
);


--
-- Name: metrics_id_seq; Type: SEQUENCE; Schema: core; Owner: -
--

ALTER TABLE core.metrics ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME core.metrics_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: modes; Type: TABLE; Schema: core; Owner: -
--

CREATE TABLE core.modes (
    id bigint NOT NULL,
    code text NOT NULL,
    display_name text NOT NULL,
    description text,
    capacity_weight smallint
);


--
-- Name: modes_id_seq; Type: SEQUENCE; Schema: core; Owner: -
--

ALTER TABLE core.modes ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME core.modes_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: pending_values; Type: TABLE; Schema: core; Owner: -
--

CREATE TABLE core.pending_values (
    id bigint NOT NULL,
    agency_id bigint NOT NULL,
    metric_id bigint NOT NULL,
    reporting_period_id bigint NOT NULL,
    mode_id bigint,
    service_scope text NOT NULL,
    value numeric NOT NULL,
    unit text NOT NULL,
    currency text,
    quality text NOT NULL,
    comparable_flag boolean DEFAULT true NOT NULL,
    crosscheck_value numeric,
    source_document_id bigint,
    page_number integer,
    table_reference text,
    extraction_method text,
    confidence numeric,
    review_status text DEFAULT 'pending'::text NOT NULL,
    flags text[],
    reviewer_notes text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT pending_values_confidence_check CHECK (((confidence >= (0)::numeric) AND (confidence <= (1)::numeric))),
    CONSTRAINT pending_values_extraction_method_check CHECK ((extraction_method = ANY (ARRAY['manual'::text, 'llm_assisted'::text, 'structured_import'::text, 'statcan_passthrough'::text]))),
    CONSTRAINT pending_values_quality_check CHECK ((quality = ANY (ARRAY['verified'::text, 'preliminary'::text, 'estimated'::text, 'imputed'::text]))),
    CONSTRAINT pending_values_review_status_check CHECK ((review_status = ANY (ARRAY['pending'::text, 'approved'::text, 'rejected'::text, 'needs_edit'::text]))),
    CONSTRAINT pending_values_service_scope_check CHECK ((service_scope = ANY (ARRAY['conventional'::text, 'specialized'::text, 'total'::text, 'system_wide'::text])))
);


--
-- Name: pending_values_id_seq; Type: SEQUENCE; Schema: core; Owner: -
--

ALTER TABLE core.pending_values ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME core.pending_values_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: reporting_periods; Type: TABLE; Schema: core; Owner: -
--

CREATE TABLE core.reporting_periods (
    id bigint NOT NULL,
    period_type text NOT NULL,
    start_date date NOT NULL,
    end_date date NOT NULL,
    label text NOT NULL,
    CONSTRAINT reporting_periods_period_type_check CHECK ((period_type = ANY (ARRAY['monthly'::text, 'quarterly'::text, 'annual_calendar'::text, 'annual_fiscal'::text, 'ytd'::text])))
);


--
-- Name: reporting_periods_id_seq; Type: SEQUENCE; Schema: core; Owner: -
--

ALTER TABLE core.reporting_periods ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME core.reporting_periods_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: source_documents; Type: TABLE; Schema: core; Owner: -
--

CREATE TABLE core.source_documents (
    id bigint NOT NULL,
    agency_id bigint,
    document_type text NOT NULL,
    title text,
    publication_date date,
    source_url text,
    archive_uri text,
    file_hash text,
    license text,
    retrieved_at timestamp with time zone,
    verified_at timestamp with time zone,
    verified_by text,
    CONSTRAINT source_documents_document_type_check CHECK ((document_type = ANY (ARRAY['annual_report'::text, 'quarterly_update'::text, 'budget'::text, 'ceo_report'::text, 'board_report'::text, 'statcan_table'::text, 'open_data_csv'::text, 'gtfs'::text, 'manual_entry'::text, 'press_release'::text]))),
    CONSTRAINT source_documents_license_check CHECK ((license = ANY (ARRAY['statcan_open'::text, 'ogl_toronto'::text, 'ogl_ottawa'::text, 'ogl_calgary'::text, 'ogl_edmonton'::text, 'ogl_montreal'::text, 'ogl_metrovancouver'::text, 'ogl_mississauga'::text, 'ogl_hamilton'::text, 'public_document'::text])))
);


--
-- Name: source_documents_id_seq; Type: SEQUENCE; Schema: core; Owner: -
--

ALTER TABLE core.source_documents ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME core.source_documents_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: source_feeds; Type: TABLE; Schema: core; Owner: -
--

CREATE TABLE core.source_feeds (
    id bigint NOT NULL,
    code text NOT NULL,
    display_name text NOT NULL,
    tier smallint,
    expected_cadence text,
    enabled boolean DEFAULT true NOT NULL,
    CONSTRAINT source_feeds_expected_cadence_check CHECK ((expected_cadence = ANY (ARRAY['monthly'::text, 'quarterly'::text, 'annual'::text])))
);


--
-- Name: source_feeds_id_seq; Type: SEQUENCE; Schema: core; Owner: -
--

ALTER TABLE core.source_feeds ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME core.source_feeds_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: accounts accounts_pkey; Type: CONSTRAINT; Schema: app; Owner: -
--

ALTER TABLE ONLY app.accounts
    ADD CONSTRAINT accounts_pkey PRIMARY KEY (provider, provider_account_id);


--
-- Name: agency_requests agency_requests_pkey; Type: CONSTRAINT; Schema: app; Owner: -
--

ALTER TABLE ONLY app.agency_requests
    ADD CONSTRAINT agency_requests_pkey PRIMARY KEY (id);


--
-- Name: conversion_events conversion_events_pkey; Type: CONSTRAINT; Schema: app; Owner: -
--

ALTER TABLE ONLY app.conversion_events
    ADD CONSTRAINT conversion_events_pkey PRIMARY KEY (id);


--
-- Name: sessions sessions_pkey; Type: CONSTRAINT; Schema: app; Owner: -
--

ALTER TABLE ONLY app.sessions
    ADD CONSTRAINT sessions_pkey PRIMARY KEY (session_token);


--
-- Name: users users_auth_id_key; Type: CONSTRAINT; Schema: app; Owner: -
--

ALTER TABLE ONLY app.users
    ADD CONSTRAINT users_auth_id_key UNIQUE (auth_id);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: app; Owner: -
--

ALTER TABLE ONLY app.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: app; Owner: -
--

ALTER TABLE ONLY app.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: verification_token verification_token_pkey; Type: CONSTRAINT; Schema: app; Owner: -
--

ALTER TABLE ONLY app.verification_token
    ADD CONSTRAINT verification_token_pkey PRIMARY KEY (identifier, token);


--
-- Name: watchlists watchlists_pkey; Type: CONSTRAINT; Schema: app; Owner: -
--

ALTER TABLE ONLY app.watchlists
    ADD CONSTRAINT watchlists_pkey PRIMARY KEY (user_id, agency_id);


--
-- Name: agencies agencies_pkey; Type: CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.agencies
    ADD CONSTRAINT agencies_pkey PRIMARY KEY (id);


--
-- Name: agencies agencies_slug_key; Type: CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.agencies
    ADD CONSTRAINT agencies_slug_key UNIQUE (slug);


--
-- Name: agency_modes agency_modes_pkey; Type: CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.agency_modes
    ADD CONSTRAINT agency_modes_pkey PRIMARY KEY (agency_id, mode_id);


--
-- Name: feed_runs feed_runs_pkey; Type: CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.feed_runs
    ADD CONSTRAINT feed_runs_pkey PRIMARY KEY (id);


--
-- Name: metric_equations metric_equations_pkey; Type: CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.metric_equations
    ADD CONSTRAINT metric_equations_pkey PRIMARY KEY (equation_code);


--
-- Name: metric_ranks metric_ranks_pkey; Type: CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.metric_ranks
    ADD CONSTRAINT metric_ranks_pkey PRIMARY KEY (id);


--
-- Name: metric_value_audit metric_value_audit_pkey; Type: CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.metric_value_audit
    ADD CONSTRAINT metric_value_audit_pkey PRIMARY KEY (id);


--
-- Name: metric_value_derivation_inputs metric_value_derivation_inputs_pkey; Type: CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.metric_value_derivation_inputs
    ADD CONSTRAINT metric_value_derivation_inputs_pkey PRIMARY KEY (derivation_id, input_metric_value_id);


--
-- Name: metric_value_derivations metric_value_derivations_pkey; Type: CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.metric_value_derivations
    ADD CONSTRAINT metric_value_derivations_pkey PRIMARY KEY (id);


--
-- Name: metric_value_sources metric_value_sources_pkey; Type: CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.metric_value_sources
    ADD CONSTRAINT metric_value_sources_pkey PRIMARY KEY (metric_value_id, source_document_id);


--
-- Name: metric_values metric_values_pkey; Type: CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.metric_values
    ADD CONSTRAINT metric_values_pkey PRIMARY KEY (id);


--
-- Name: metrics metrics_code_key; Type: CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.metrics
    ADD CONSTRAINT metrics_code_key UNIQUE (code);


--
-- Name: metrics metrics_pkey; Type: CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.metrics
    ADD CONSTRAINT metrics_pkey PRIMARY KEY (id);


--
-- Name: modes modes_code_key; Type: CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.modes
    ADD CONSTRAINT modes_code_key UNIQUE (code);


--
-- Name: modes modes_pkey; Type: CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.modes
    ADD CONSTRAINT modes_pkey PRIMARY KEY (id);


--
-- Name: pending_values pending_values_pkey; Type: CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.pending_values
    ADD CONSTRAINT pending_values_pkey PRIMARY KEY (id);


--
-- Name: reporting_periods reporting_periods_period_type_start_date_end_date_key; Type: CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.reporting_periods
    ADD CONSTRAINT reporting_periods_period_type_start_date_end_date_key UNIQUE (period_type, start_date, end_date);


--
-- Name: reporting_periods reporting_periods_pkey; Type: CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.reporting_periods
    ADD CONSTRAINT reporting_periods_pkey PRIMARY KEY (id);


--
-- Name: source_documents source_documents_pkey; Type: CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.source_documents
    ADD CONSTRAINT source_documents_pkey PRIMARY KEY (id);


--
-- Name: source_feeds source_feeds_code_key; Type: CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.source_feeds
    ADD CONSTRAINT source_feeds_code_key UNIQUE (code);


--
-- Name: source_feeds source_feeds_pkey; Type: CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.source_feeds
    ADD CONSTRAINT source_feeds_pkey PRIMARY KEY (id);


--
-- Name: agencies_parent_idx; Type: INDEX; Schema: core; Owner: -
--

CREATE INDEX agencies_parent_idx ON core.agencies USING btree (parent_agency_id);


--
-- Name: agencies_subdivision_idx; Type: INDEX; Schema: core; Owner: -
--

CREATE INDEX agencies_subdivision_idx ON core.agencies USING btree (subdivision);


--
-- Name: metric_value_derivations_value_idx; Type: INDEX; Schema: core; Owner: -
--

CREATE UNIQUE INDEX metric_value_derivations_value_idx ON core.metric_value_derivations USING btree (metric_value_id);


--
-- Name: metric_values_cohort_idx; Type: INDEX; Schema: core; Owner: -
--

CREATE INDEX metric_values_cohort_idx ON core.metric_values USING btree (metric_id, reporting_period_id);


--
-- Name: metric_values_lookup_idx; Type: INDEX; Schema: core; Owner: -
--

CREATE INDEX metric_values_lookup_idx ON core.metric_values USING btree (agency_id, metric_id, reporting_period_id);


--
-- Name: one_current_value; Type: INDEX; Schema: core; Owner: -
--

CREATE UNIQUE INDEX one_current_value ON core.metric_values USING btree (agency_id, metric_id, reporting_period_id, mode_id, service_scope) NULLS NOT DISTINCT WHERE is_current;


--
-- Name: metric_values metric_values_audit; Type: TRIGGER; Schema: core; Owner: -
--

CREATE TRIGGER metric_values_audit AFTER INSERT OR UPDATE ON core.metric_values FOR EACH ROW EXECUTE FUNCTION core.log_metric_value_change();


--
-- Name: accounts accounts_user_id_fkey; Type: FK CONSTRAINT; Schema: app; Owner: -
--

ALTER TABLE ONLY app.accounts
    ADD CONSTRAINT accounts_user_id_fkey FOREIGN KEY (user_id) REFERENCES app.users(auth_id) ON DELETE CASCADE;


--
-- Name: agency_requests agency_requests_agency_id_fkey; Type: FK CONSTRAINT; Schema: app; Owner: -
--

ALTER TABLE ONLY app.agency_requests
    ADD CONSTRAINT agency_requests_agency_id_fkey FOREIGN KEY (agency_id) REFERENCES core.agencies(id) ON DELETE SET NULL;


--
-- Name: conversion_events conversion_events_agency_id_fkey; Type: FK CONSTRAINT; Schema: app; Owner: -
--

ALTER TABLE ONLY app.conversion_events
    ADD CONSTRAINT conversion_events_agency_id_fkey FOREIGN KEY (agency_id) REFERENCES core.agencies(id) ON DELETE SET NULL;


--
-- Name: conversion_events conversion_events_user_id_fkey; Type: FK CONSTRAINT; Schema: app; Owner: -
--

ALTER TABLE ONLY app.conversion_events
    ADD CONSTRAINT conversion_events_user_id_fkey FOREIGN KEY (user_id) REFERENCES app.users(id) ON DELETE SET NULL;


--
-- Name: sessions sessions_user_id_fkey; Type: FK CONSTRAINT; Schema: app; Owner: -
--

ALTER TABLE ONLY app.sessions
    ADD CONSTRAINT sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES app.users(auth_id) ON DELETE CASCADE;


--
-- Name: watchlists watchlists_agency_id_fkey; Type: FK CONSTRAINT; Schema: app; Owner: -
--

ALTER TABLE ONLY app.watchlists
    ADD CONSTRAINT watchlists_agency_id_fkey FOREIGN KEY (agency_id) REFERENCES core.agencies(id) ON DELETE CASCADE;


--
-- Name: watchlists watchlists_user_id_fkey; Type: FK CONSTRAINT; Schema: app; Owner: -
--

ALTER TABLE ONLY app.watchlists
    ADD CONSTRAINT watchlists_user_id_fkey FOREIGN KEY (user_id) REFERENCES app.users(id) ON DELETE CASCADE;


--
-- Name: agencies agencies_parent_agency_id_fkey; Type: FK CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.agencies
    ADD CONSTRAINT agencies_parent_agency_id_fkey FOREIGN KEY (parent_agency_id) REFERENCES core.agencies(id);


--
-- Name: agency_modes agency_modes_agency_id_fkey; Type: FK CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.agency_modes
    ADD CONSTRAINT agency_modes_agency_id_fkey FOREIGN KEY (agency_id) REFERENCES core.agencies(id) ON DELETE CASCADE;


--
-- Name: agency_modes agency_modes_mode_id_fkey; Type: FK CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.agency_modes
    ADD CONSTRAINT agency_modes_mode_id_fkey FOREIGN KEY (mode_id) REFERENCES core.modes(id);


--
-- Name: feed_runs feed_runs_feed_id_fkey; Type: FK CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.feed_runs
    ADD CONSTRAINT feed_runs_feed_id_fkey FOREIGN KEY (feed_id) REFERENCES core.source_feeds(id) ON DELETE CASCADE;


--
-- Name: metric_equations metric_equations_defines_fkey; Type: FK CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.metric_equations
    ADD CONSTRAINT metric_equations_defines_fkey FOREIGN KEY (defines) REFERENCES core.metrics(code);


--
-- Name: metric_ranks metric_ranks_agency_id_fkey; Type: FK CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.metric_ranks
    ADD CONSTRAINT metric_ranks_agency_id_fkey FOREIGN KEY (agency_id) REFERENCES core.agencies(id) ON DELETE CASCADE;


--
-- Name: metric_ranks metric_ranks_metric_id_fkey; Type: FK CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.metric_ranks
    ADD CONSTRAINT metric_ranks_metric_id_fkey FOREIGN KEY (metric_id) REFERENCES core.metrics(id);


--
-- Name: metric_ranks metric_ranks_reporting_period_id_fkey; Type: FK CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.metric_ranks
    ADD CONSTRAINT metric_ranks_reporting_period_id_fkey FOREIGN KEY (reporting_period_id) REFERENCES core.reporting_periods(id);


--
-- Name: metric_value_audit metric_value_audit_metric_value_id_fkey; Type: FK CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.metric_value_audit
    ADD CONSTRAINT metric_value_audit_metric_value_id_fkey FOREIGN KEY (metric_value_id) REFERENCES core.metric_values(id) ON DELETE CASCADE;


--
-- Name: metric_value_derivation_inputs metric_value_derivation_inputs_derivation_id_fkey; Type: FK CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.metric_value_derivation_inputs
    ADD CONSTRAINT metric_value_derivation_inputs_derivation_id_fkey FOREIGN KEY (derivation_id) REFERENCES core.metric_value_derivations(id) ON DELETE CASCADE;


--
-- Name: metric_value_derivation_inputs metric_value_derivation_inputs_input_metric_value_id_fkey; Type: FK CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.metric_value_derivation_inputs
    ADD CONSTRAINT metric_value_derivation_inputs_input_metric_value_id_fkey FOREIGN KEY (input_metric_value_id) REFERENCES core.metric_values(id) ON DELETE CASCADE;


--
-- Name: metric_value_derivations metric_value_derivations_metric_value_id_fkey; Type: FK CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.metric_value_derivations
    ADD CONSTRAINT metric_value_derivations_metric_value_id_fkey FOREIGN KEY (metric_value_id) REFERENCES core.metric_values(id) ON DELETE CASCADE;


--
-- Name: metric_value_sources metric_value_sources_metric_value_id_fkey; Type: FK CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.metric_value_sources
    ADD CONSTRAINT metric_value_sources_metric_value_id_fkey FOREIGN KEY (metric_value_id) REFERENCES core.metric_values(id) ON DELETE CASCADE;


--
-- Name: metric_value_sources metric_value_sources_source_document_id_fkey; Type: FK CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.metric_value_sources
    ADD CONSTRAINT metric_value_sources_source_document_id_fkey FOREIGN KEY (source_document_id) REFERENCES core.source_documents(id) ON DELETE CASCADE;


--
-- Name: metric_values metric_values_agency_id_fkey; Type: FK CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.metric_values
    ADD CONSTRAINT metric_values_agency_id_fkey FOREIGN KEY (agency_id) REFERENCES core.agencies(id) ON DELETE CASCADE;


--
-- Name: metric_values metric_values_crosscheck_source_fk; Type: FK CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.metric_values
    ADD CONSTRAINT metric_values_crosscheck_source_fk FOREIGN KEY (crosscheck_source_document_id) REFERENCES core.source_documents(id) ON DELETE SET NULL;


--
-- Name: metric_values metric_values_metric_id_fkey; Type: FK CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.metric_values
    ADD CONSTRAINT metric_values_metric_id_fkey FOREIGN KEY (metric_id) REFERENCES core.metrics(id);


--
-- Name: metric_values metric_values_mode_id_fkey; Type: FK CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.metric_values
    ADD CONSTRAINT metric_values_mode_id_fkey FOREIGN KEY (mode_id) REFERENCES core.modes(id);


--
-- Name: metric_values metric_values_reporting_period_id_fkey; Type: FK CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.metric_values
    ADD CONSTRAINT metric_values_reporting_period_id_fkey FOREIGN KEY (reporting_period_id) REFERENCES core.reporting_periods(id);


--
-- Name: metric_values metric_values_restatement_of_id_fkey; Type: FK CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.metric_values
    ADD CONSTRAINT metric_values_restatement_of_id_fkey FOREIGN KEY (restatement_of_id) REFERENCES core.metric_values(id);


--
-- Name: pending_values pending_values_agency_id_fkey; Type: FK CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.pending_values
    ADD CONSTRAINT pending_values_agency_id_fkey FOREIGN KEY (agency_id) REFERENCES core.agencies(id) ON DELETE CASCADE;


--
-- Name: pending_values pending_values_metric_id_fkey; Type: FK CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.pending_values
    ADD CONSTRAINT pending_values_metric_id_fkey FOREIGN KEY (metric_id) REFERENCES core.metrics(id);


--
-- Name: pending_values pending_values_mode_id_fkey; Type: FK CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.pending_values
    ADD CONSTRAINT pending_values_mode_id_fkey FOREIGN KEY (mode_id) REFERENCES core.modes(id);


--
-- Name: pending_values pending_values_reporting_period_id_fkey; Type: FK CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.pending_values
    ADD CONSTRAINT pending_values_reporting_period_id_fkey FOREIGN KEY (reporting_period_id) REFERENCES core.reporting_periods(id);


--
-- Name: pending_values pending_values_source_document_id_fkey; Type: FK CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.pending_values
    ADD CONSTRAINT pending_values_source_document_id_fkey FOREIGN KEY (source_document_id) REFERENCES core.source_documents(id) ON DELETE SET NULL;


--
-- Name: source_documents source_documents_agency_id_fkey; Type: FK CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.source_documents
    ADD CONSTRAINT source_documents_agency_id_fkey FOREIGN KEY (agency_id) REFERENCES core.agencies(id) ON DELETE SET NULL;


--
-- Name: SCHEMA app; Type: ACL; Schema: -; Owner: -
--

GRANT USAGE ON SCHEMA app TO web_reader;


--
-- Name: SCHEMA core; Type: ACL; Schema: -; Owner: -
--

GRANT USAGE ON SCHEMA core TO web_reader;


--
-- Name: TABLE accounts; Type: ACL; Schema: app; Owner: -
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE app.accounts TO web_reader;


--
-- Name: TABLE agency_requests; Type: ACL; Schema: app; Owner: -
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE app.agency_requests TO web_reader;


--
-- Name: TABLE conversion_events; Type: ACL; Schema: app; Owner: -
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE app.conversion_events TO web_reader;


--
-- Name: TABLE sessions; Type: ACL; Schema: app; Owner: -
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE app.sessions TO web_reader;


--
-- Name: TABLE users; Type: ACL; Schema: app; Owner: -
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE app.users TO web_reader;


--
-- Name: TABLE verification_token; Type: ACL; Schema: app; Owner: -
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE app.verification_token TO web_reader;


--
-- Name: TABLE watchlists; Type: ACL; Schema: app; Owner: -
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE app.watchlists TO web_reader;


--
-- Name: TABLE agencies; Type: ACL; Schema: core; Owner: -
--

GRANT SELECT ON TABLE core.agencies TO web_reader;


--
-- Name: TABLE agency_modes; Type: ACL; Schema: core; Owner: -
--

GRANT SELECT ON TABLE core.agency_modes TO web_reader;


--
-- Name: TABLE feed_runs; Type: ACL; Schema: core; Owner: -
--

GRANT SELECT ON TABLE core.feed_runs TO web_reader;


--
-- Name: TABLE metric_equations; Type: ACL; Schema: core; Owner: -
--

GRANT SELECT ON TABLE core.metric_equations TO web_reader;


--
-- Name: TABLE metric_ranks; Type: ACL; Schema: core; Owner: -
--

GRANT SELECT ON TABLE core.metric_ranks TO web_reader;


--
-- Name: TABLE metric_value_derivation_inputs; Type: ACL; Schema: core; Owner: -
--

GRANT SELECT ON TABLE core.metric_value_derivation_inputs TO web_reader;


--
-- Name: TABLE metric_value_derivations; Type: ACL; Schema: core; Owner: -
--

GRANT SELECT ON TABLE core.metric_value_derivations TO web_reader;


--
-- Name: TABLE metric_value_sources; Type: ACL; Schema: core; Owner: -
--

GRANT SELECT ON TABLE core.metric_value_sources TO web_reader;


--
-- Name: TABLE metric_values; Type: ACL; Schema: core; Owner: -
--

GRANT SELECT ON TABLE core.metric_values TO web_reader;


--
-- Name: TABLE metrics; Type: ACL; Schema: core; Owner: -
--

GRANT SELECT ON TABLE core.metrics TO web_reader;


--
-- Name: TABLE modes; Type: ACL; Schema: core; Owner: -
--

GRANT SELECT ON TABLE core.modes TO web_reader;


--
-- Name: TABLE reporting_periods; Type: ACL; Schema: core; Owner: -
--

GRANT SELECT ON TABLE core.reporting_periods TO web_reader;


--
-- Name: TABLE source_documents; Type: ACL; Schema: core; Owner: -
--

GRANT SELECT ON TABLE core.source_documents TO web_reader;


--
-- Name: TABLE source_feeds; Type: ACL; Schema: core; Owner: -
--

GRANT SELECT ON TABLE core.source_feeds TO web_reader;


--
-- PostgreSQL database dump complete
--

\unrestrict 8yghBE68puhEM8nUlcekG5X0imIFkmY3kzPea9U6KuldG6kChGNadDO2gCyE7i4

