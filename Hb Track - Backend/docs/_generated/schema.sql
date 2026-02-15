-- Schema dump generated: 2026-02-14T15:01:05.151268+00:00Z
-- Source: localhost

--
-- PostgreSQL database dump
--

\restrict ho7fk19KMuJx0CDdjBtcmOh8HdW1wJfBLfZNAXKQ01TP4bKeGiJbzIYGrhTqyt9

-- Dumped from database version 12.22 (Debian 12.22-1.pgdg120+1)
-- Dumped by pg_dump version 18.1

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
-- Name: public; Type: SCHEMA; Schema: -; Owner: -
--

-- *not* creating schema, since initdb creates it


--
-- Name: SCHEMA public; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON SCHEMA public IS '';


--
-- Name: pg_trgm; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pg_trgm WITH SCHEMA public;


--
-- Name: EXTENSION pg_trgm; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION pg_trgm IS 'text similarity measurement and index searching based on trigrams';


--
-- Name: pgcrypto; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA public;


--
-- Name: EXTENSION pgcrypto; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION pgcrypto IS 'RDB1: Extensão para funções criptográficas, incluindo gen_random_uuid() usado em PKs UUID.';


--
-- Name: training_execution_outcome_enum; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.training_execution_outcome_enum AS ENUM (
    'on_time',
    'delayed',
    'canceled',
    'shortened',
    'extended'
);


--
-- Name: current_user(); Type: FUNCTION; Schema: app; Owner: -
--

CREATE FUNCTION app."current_user"() RETURNS uuid
    LANGUAGE plpgsql STABLE
    AS $$
        BEGIN
            -- Retorna o user_id do contexto da sessão
            -- Backend deve setar isso via: SET LOCAL app.current_user_id = '<uuid>';
            RETURN current_setting('app.current_user_id', true)::UUID;
        EXCEPTION
            WHEN OTHERS THEN
                RETURN NULL;
        END;
        $$;


--
-- Name: FUNCTION "current_user"(); Type: COMMENT; Schema: app; Owner: -
--

COMMENT ON FUNCTION app."current_user"() IS 'Função auxiliar: retorna UUID do usuário atual do contexto da sessão. Backend seta via SET LOCAL.';


--
-- Name: fn_audit_session_status(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_audit_session_status() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        BEGIN
            -- Apenas auditar se o status mudou
            IF OLD.status IS DISTINCT FROM NEW.status THEN
                INSERT INTO audit_logs (
                    organization_id,
                    user_id,
                    entity_type,
                    entity_id,
                    action,
                    changes,
                    metadata,
                    created_at
                ) VALUES (
                    NEW.organization_id,
                    NEW.updated_by_user_id,  -- Assumindo que existe campo updated_by_user_id
                    'training_session',
                    NEW.id,
                    'status_change',
                    jsonb_build_object(
                        'old_status', OLD.status,
                        'new_status', NEW.status
                    ),
                    jsonb_build_object(
                        'session_at', NEW.session_at,
                        'session_type', NEW.session_type,
                        'team_id', NEW.team_id
                    ),
                    NOW()
                );
            END IF;
            
            RETURN NEW;
        END;
        $$;


--
-- Name: FUNCTION fn_audit_session_status(); Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON FUNCTION public.fn_audit_session_status() IS 'Step 2: Registra mudanças de status de sessões de treino em audit_logs';


--
-- Name: fn_calculate_internal_load(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_calculate_internal_load() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        BEGIN
            -- Calcular internal_load: minutes_effective × session_rpe
            -- COALESCE garante 0 se algum valor for NULL
            NEW.internal_load := COALESCE(NEW.minutes_effective, 0) * COALESCE(NEW.session_rpe, 0);
            
            RETURN NEW;
        END;
        $$;


--
-- Name: FUNCTION fn_calculate_internal_load(); Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON FUNCTION public.fn_calculate_internal_load() IS 'Step 2: Calcula internal_load automaticamente como minutes_effective × session_rpe';


--
-- Name: fn_derive_phase_focus(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_derive_phase_focus() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        DECLARE
            v_threshold CONSTANT NUMERIC := 5;
        BEGIN
            -- Derivar phase_focus_attack (ataque posicional + técnico)
            NEW.phase_focus_attack := (
                COALESCE(NEW.focus_attack_positional_pct, 0) +
                COALESCE(NEW.focus_attack_technical_pct, 0)
            ) >= v_threshold;

            -- Derivar phase_focus_defense (defesa posicional + técnico)
            NEW.phase_focus_defense := (
                COALESCE(NEW.focus_defense_positional_pct, 0) +
                COALESCE(NEW.focus_defense_technical_pct, 0)
            ) >= v_threshold;

            -- Derivar phase_focus_transition_offense
            NEW.phase_focus_transition_offense := (
                COALESCE(NEW.focus_transition_offense_pct, 0)
            ) >= v_threshold;

            -- Derivar phase_focus_transition_defense
            NEW.phase_focus_transition_defense := (
                COALESCE(NEW.focus_transition_defense_pct, 0)
            ) >= v_threshold;

            RETURN NEW;
        END;
        $$;


--
-- Name: FUNCTION fn_derive_phase_focus(); Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON FUNCTION public.fn_derive_phase_focus() IS 'Step 3: Deriva automaticamente phase_focus_* baseado no threshold de 5%';


--
-- Name: fn_invalidate_analytics_cache(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_invalidate_analytics_cache() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        DECLARE
            v_session_month DATE;
            v_microcycle_id UUID;
        BEGIN
            -- Determinar valores OLD ou NEW dependendo da operação
            IF TG_OP = 'DELETE' THEN
                v_session_month := DATE_TRUNC('month', OLD.session_at);
                v_microcycle_id := OLD.microcycle_id;
            ELSE
                v_session_month := DATE_TRUNC('month', NEW.session_at);
                v_microcycle_id := NEW.microcycle_id;
            END IF;
            
            -- Invalidar cache weekly (se microcycle_id existir)
            IF v_microcycle_id IS NOT NULL THEN
                UPDATE training_analytics_cache
                SET cache_dirty = TRUE,
                    calculated_at = NULL
                WHERE microcycle_id = v_microcycle_id
                  AND granularity = 'weekly';
            END IF;
            
            -- Invalidar cache monthly
            UPDATE training_analytics_cache
            SET cache_dirty = TRUE,
                calculated_at = NULL
            WHERE month = v_session_month
              AND granularity = 'monthly';
            
            -- Retornar registro apropriado
            IF TG_OP = 'DELETE' THEN
                RETURN OLD;
            ELSE
                RETURN NEW;
            END IF;
        END;
        $$;


--
-- Name: FUNCTION fn_invalidate_analytics_cache(); Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON FUNCTION public.fn_invalidate_analytics_cache() IS 'Step 2: Invalida cache de analytics ao modificar sessões de treino (weekly/monthly)';


--
-- Name: fn_update_wellness_response_timestamp(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_update_wellness_response_timestamp() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        BEGIN
            -- Atualizar wellness_reminders quando atleta responder
            UPDATE wellness_reminders
            SET responded_at = NOW()
            WHERE training_session_id = NEW.training_session_id
              AND athlete_id = NEW.athlete_id
              AND responded_at IS NULL;
            
            RETURN NEW;
        END;
        $$;


--
-- Name: FUNCTION fn_update_wellness_response_timestamp(); Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON FUNCTION public.fn_update_wellness_response_timestamp() IS 'Step 2: Atualiza responded_at em wellness_reminders quando atleta responde wellness';


--
-- Name: tr_update_session_exercises_updated_at(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.tr_update_session_exercises_updated_at() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$;


--
-- Name: trg_auto_end_team_registrations_on_dispensada(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trg_auto_end_team_registrations_on_dispensada() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        BEGIN
            -- Se mudou de 'ativa' ou 'arquivada' para 'dispensada'
            IF OLD.state != 'dispensada' AND NEW.state = 'dispensada' THEN
                -- Encerra todos os team_registrations ativos desta atleta
                UPDATE team_registrations
                SET
                    end_at = now(),
                    updated_at = now()
                WHERE
                    athlete_id = NEW.id
                    AND end_at IS NULL
                    AND deleted_at IS NULL;

                -- Log: registra quantos vínculos foram encerrados
                RAISE NOTICE 'Atleta % mudou para dispensada. % team_registrations ativos foram encerrados automaticamente.',
                    NEW.id,
                    (SELECT COUNT(*) FROM team_registrations WHERE athlete_id = NEW.id AND end_at = now()::date);
            END IF;

            RETURN NEW;
        END;
        $$;


--
-- Name: FUNCTION trg_auto_end_team_registrations_on_dispensada(); Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON FUNCTION public.trg_auto_end_team_registrations_on_dispensada() IS 'RDB18.6: Encerra automaticamente todos team_registrations ativos quando atleta muda para state=dispensada.';


--
-- Name: trg_block_audit_logs_modification(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trg_block_audit_logs_modification() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        BEGIN
            RAISE EXCEPTION 'audit_logs é append-only. UPDATE e DELETE são bloqueados. Operação tentada: %', TG_OP;
        END;
        $$;


--
-- Name: FUNCTION trg_block_audit_logs_modification(); Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON FUNCTION public.trg_block_audit_logs_modification() IS 'RDB18.5: Bloqueia UPDATE e DELETE em audit_logs. Tabela append-only, absolutamente imutável.';


--
-- Name: trg_block_finished_match_update(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trg_block_finished_match_update() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        BEGIN
            -- Permite mudança de 'finished' para 'in_progress' (reabertura)
            IF OLD.status = 'finished' AND NEW.status != 'finished' THEN
                -- Permitir apenas mudança para 'in_progress' (reabertura)
                IF NEW.status = 'in_progress' THEN
                    -- Auditoria será feita pelo backend
                    RETURN NEW;
                ELSE
                    RAISE EXCEPTION 'Jogo finalizado só pode ser reaberto para status in_progress. Status atual: %, tentou mudar para: %',
                        OLD.status, NEW.status;
                END IF;
            END IF;

            -- Bloqueia qualquer UPDATE se status for 'finished' e não for reabertura
            IF OLD.status = 'finished' AND NEW.status = 'finished' THEN
                RAISE EXCEPTION 'Não é permitido alterar jogo com status finished. Use reabertura administrativa (status -> in_progress) para editar.';
            END IF;

            RETURN NEW;
        END;
        $$;


--
-- Name: FUNCTION trg_block_finished_match_update(); Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON FUNCTION public.trg_block_finished_match_update() IS 'RDB18.3: Bloqueia UPDATE em matches com status=finished. Exceção: reabertura para in_progress.';


--
-- Name: trg_block_physical_delete(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trg_block_physical_delete() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        BEGIN
            RAISE EXCEPTION 'DELETE físico bloqueado. Use soft delete (UPDATE deleted_at, deleted_reason) na tabela %.', TG_TABLE_NAME;
        END;
        $$;


--
-- Name: FUNCTION trg_block_physical_delete(); Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON FUNCTION public.trg_block_physical_delete() IS 'RDB18.4: Bloqueia DELETE físico em tabelas com soft delete. Força uso de deleted_at + deleted_reason.';


--
-- Name: trg_insert_default_session_templates(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trg_insert_default_session_templates() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        BEGIN
            -- Insert 4 default templates for new organization
            INSERT INTO session_templates (
                id, org_id, name, description, icon,
                focus_attack_positional_pct, focus_defense_positional_pct,
                focus_transition_offense_pct, focus_transition_defense_pct,
                focus_attack_technical_pct, focus_defense_technical_pct,
                focus_physical_pct, is_favorite
            ) VALUES
            (
                gen_random_uuid(), NEW.id,
                'Tático Ofensivo',
                'Foco em ataque posicional e transição ofensiva',
                'target',
                45.00, 10.00, 25.00, 5.00, 10.00, 0.00, 5.00, true
            ),
            (
                gen_random_uuid(), NEW.id,
                'Físico Intensivo',
                'Treino de alta intensidade física',
                'flame',
                10.00, 10.00, 5.00, 5.00, 0.00, 10.00, 60.00, true
            ),
            (
                gen_random_uuid(), NEW.id,
                'Balanceado',
                'Distribuição equilibrada entre todos os focos',
                'activity',
                15.00, 15.00, 15.00, 15.00, 10.00, 10.00, 20.00, false
            ),
            (
                gen_random_uuid(), NEW.id,
                'Defensivo',
                'Prioridade em defesa posicional e transição defensiva',
                'shield',
                5.00, 50.00, 0.00, 30.00, 5.00, 5.00, 5.00, false
            );
            
            RETURN NEW;
        END;
        $$;


--
-- Name: trg_set_athlete_age_at_registration(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trg_set_athlete_age_at_registration() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        BEGIN
            IF NEW.birth_date IS NOT NULL AND NEW.registered_at IS NOT NULL THEN
                NEW.athlete_age_at_registration = EXTRACT(YEAR FROM AGE(NEW.registered_at, NEW.birth_date));
            END IF;
            RETURN NEW;
        END;
        $$;


--
-- Name: FUNCTION trg_set_athlete_age_at_registration(); Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON FUNCTION public.trg_set_athlete_age_at_registration() IS 'RDB18.2: Calcula automaticamente athlete_age_at_registration quando birth_date ou registered_at mudam.';


--
-- Name: trg_set_updated_at(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trg_set_updated_at() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$;


--
-- Name: FUNCTION trg_set_updated_at(); Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON FUNCTION public.trg_set_updated_at() IS 'RDB18.1: Atualiza automaticamente updated_at em todas as tabelas de domínio.';


--
-- Name: update_updated_at_column(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.update_updated_at_column() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: advantage_states; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.advantage_states (
    code character varying(32) NOT NULL,
    delta_players smallint NOT NULL,
    description character varying(255)
);


--
-- Name: TABLE advantage_states; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.advantage_states IS 'Estados de vantagem numérica. Lookup table.';


--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


--
-- Name: athlete_badges; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.athlete_badges (
    id uuid DEFAULT public.gen_random_uuid() NOT NULL,
    athlete_id uuid NOT NULL,
    badge_type character varying(50) NOT NULL,
    month_reference date,
    earned_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_athlete_badges_type CHECK (((badge_type)::text = ANY ((ARRAY['wellness_champion_monthly'::character varying, 'wellness_streak_3months'::character varying])::text[])))
);


--
-- Name: TABLE athlete_badges; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.athlete_badges IS 'Step 3: Badges de gamificação para atletas (wellness_champion_monthly 90%+, wellness_streak_3months)';


--
-- Name: athletes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.athletes (
    id uuid DEFAULT public.gen_random_uuid() NOT NULL,
    person_id uuid NOT NULL,
    state character varying(20) DEFAULT 'ativa'::character varying NOT NULL,
    injured boolean DEFAULT false NOT NULL,
    medical_restriction boolean DEFAULT false NOT NULL,
    suspended_until date,
    load_restricted boolean DEFAULT false NOT NULL,
    athlete_name character varying(100) NOT NULL,
    birth_date date NOT NULL,
    athlete_nickname character varying(50),
    shirt_number integer,
    main_defensive_position_id integer,
    secondary_defensive_position_id integer,
    main_offensive_position_id integer,
    secondary_offensive_position_id integer,
    schooling_id integer,
    guardian_name character varying(100),
    guardian_phone character varying(20),
    athlete_photo_path character varying(500),
    registered_at timestamp with time zone DEFAULT now() NOT NULL,
    athlete_age_at_registration integer,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    deleted_reason text,
    organization_id uuid,
    CONSTRAINT ck_athletes_deleted_reason CHECK ((((deleted_at IS NULL) AND (deleted_reason IS NULL)) OR ((deleted_at IS NOT NULL) AND (deleted_reason IS NOT NULL)))),
    CONSTRAINT ck_athletes_shirt_number CHECK (((shirt_number IS NULL) OR ((shirt_number >= 1) AND (shirt_number <= 99)))),
    CONSTRAINT ck_athletes_state CHECK (((state)::text = ANY ((ARRAY['ativa'::character varying, 'dispensada'::character varying, 'arquivada'::character varying])::text[])))
);


--
-- Name: TABLE athletes; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.athletes IS 'Atletas. V1.2: estado base + flags (injured, medical_restriction, suspended_until, load_restricted).';


--
-- Name: COLUMN athletes.athlete_photo_path; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.athletes.athlete_photo_path IS 'DEPRECATED (31/12/2025): Use person_media para fotos de atletas. Este campo será removido em versão futura. Novo fluxo: POST /api/v1/persons/{person_id}/media com media_type=profile_photo';


--
-- Name: attendance; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.attendance (
    id uuid DEFAULT public.gen_random_uuid() NOT NULL,
    training_session_id uuid NOT NULL,
    team_registration_id uuid NOT NULL,
    athlete_id uuid NOT NULL,
    presence_status character varying(32) NOT NULL,
    minutes_effective smallint,
    comment text,
    source character varying(32) DEFAULT 'manual'::character varying NOT NULL,
    participation_type character varying(32),
    reason_absence character varying(32),
    is_medical_restriction boolean DEFAULT false,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by_user_id uuid NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    deleted_reason text,
    correction_by_user_id uuid,
    correction_at timestamp with time zone,
    CONSTRAINT ck_attendance_correction_fields CHECK ((((source)::text <> 'correction'::text) OR (((source)::text = 'correction'::text) AND (correction_by_user_id IS NOT NULL) AND (correction_at IS NOT NULL)))),
    CONSTRAINT ck_attendance_deleted_reason CHECK ((((deleted_at IS NULL) AND (deleted_reason IS NULL)) OR ((deleted_at IS NOT NULL) AND (deleted_reason IS NOT NULL)))),
    CONSTRAINT ck_attendance_participation_type CHECK (((participation_type IS NULL) OR ((participation_type)::text = ANY ((ARRAY['full'::character varying, 'partial'::character varying, 'adapted'::character varying, 'did_not_train'::character varying])::text[])))),
    CONSTRAINT ck_attendance_reason CHECK (((reason_absence IS NULL) OR ((reason_absence)::text = ANY ((ARRAY['medico'::character varying, 'escola'::character varying, 'familiar'::character varying, 'opcional'::character varying, 'outro'::character varying])::text[])))),
    CONSTRAINT ck_attendance_source CHECK (((source)::text = ANY ((ARRAY['manual'::character varying, 'import'::character varying, 'correction'::character varying])::text[]))),
    CONSTRAINT ck_attendance_status CHECK (((presence_status)::text = ANY ((ARRAY['present'::character varying, 'absent'::character varying])::text[])))
);


--
-- Name: TABLE attendance; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.attendance IS 'Presença por treino. V1.2: sem convocação formal; lista gerada por team_registrations ativos.';


--
-- Name: COLUMN attendance.correction_by_user_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.attendance.correction_by_user_id IS 'ID do usuário que realizou a correção (quando source=correction)';


--
-- Name: COLUMN attendance.correction_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.attendance.correction_at IS 'Timestamp da correção (quando source=correction)';


--
-- Name: CONSTRAINT ck_attendance_correction_fields ON attendance; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON CONSTRAINT ck_attendance_correction_fields ON public.attendance IS 'Garante que correções têm correction_by_user_id e correction_at preenchidos';


--
-- Name: audit_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.audit_logs (
    id uuid DEFAULT public.gen_random_uuid() NOT NULL,
    entity character varying(64) NOT NULL,
    entity_id uuid,
    action character varying(64) NOT NULL,
    actor_id uuid,
    context jsonb,
    old_value jsonb,
    new_value jsonb,
    justification text,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: TABLE audit_logs; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.audit_logs IS 'Logs de auditoria. R35: absolutamente imutável (RDB5: append-only).';


--
-- Name: categories; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.categories (
    id integer NOT NULL,
    name character varying(50) NOT NULL,
    max_age integer NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    CONSTRAINT ck_categories_max_age_positive CHECK ((max_age > 0))
);


--
-- Name: TABLE categories; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.categories IS 'Categorias esportivas. V1.2: sem min_age, apenas max_age.';


--
-- Name: categories_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.categories_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: categories_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.categories_id_seq OWNED BY public.categories.id;


--
-- Name: competition_matches; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.competition_matches (
    id uuid DEFAULT public.gen_random_uuid() NOT NULL,
    competition_id uuid NOT NULL,
    phase_id uuid,
    external_reference_id character varying(100),
    home_team_id uuid,
    away_team_id uuid,
    is_our_match boolean DEFAULT false,
    our_team_is_home boolean,
    linked_match_id uuid,
    match_date date,
    match_time time without time zone,
    match_datetime timestamp with time zone,
    location character varying(255),
    round_number integer,
    round_name character varying(100),
    home_score integer,
    away_score integer,
    home_score_extra integer,
    away_score_extra integer,
    home_score_penalties integer,
    away_score_penalties integer,
    status character varying(50) DEFAULT 'scheduled'::character varying,
    notes text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: TABLE competition_matches; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.competition_matches IS 'Jogos específicos de uma competição';


--
-- Name: competition_opponent_teams; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.competition_opponent_teams (
    id uuid DEFAULT public.gen_random_uuid() NOT NULL,
    competition_id uuid NOT NULL,
    name character varying(255) NOT NULL,
    short_name character varying(50),
    category character varying(50),
    city character varying(100),
    logo_url character varying(500),
    linked_team_id uuid,
    group_name character varying(50),
    stats jsonb DEFAULT '{"wins": 0, "draws": 0, "losses": 0, "played": 0, "points": 0, "goals_for": 0, "goals_against": 0, "goal_difference": 0}'::jsonb,
    status character varying(50) DEFAULT 'active'::character varying,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: TABLE competition_opponent_teams; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.competition_opponent_teams IS 'Times adversários em uma competição';


--
-- Name: competition_phases; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.competition_phases (
    id uuid DEFAULT public.gen_random_uuid() NOT NULL,
    competition_id uuid NOT NULL,
    name character varying(100) NOT NULL,
    phase_type character varying(50) NOT NULL,
    order_index integer DEFAULT 0 NOT NULL,
    is_olympic_cross boolean DEFAULT false,
    config jsonb DEFAULT '{}'::jsonb,
    status character varying(50) DEFAULT 'pending'::character varying,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: TABLE competition_phases; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.competition_phases IS 'Fases de uma competição (grupos, semifinais, finais, etc.)';


--
-- Name: competition_seasons; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.competition_seasons (
    id uuid DEFAULT public.gen_random_uuid() NOT NULL,
    competition_id uuid NOT NULL,
    season_id uuid NOT NULL,
    name character varying(100),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: TABLE competition_seasons; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.competition_seasons IS 'Vínculo competição ↔ temporada';


--
-- Name: competition_standings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.competition_standings (
    id uuid DEFAULT public.gen_random_uuid() NOT NULL,
    competition_id uuid NOT NULL,
    phase_id uuid,
    opponent_team_id uuid NOT NULL,
    "position" integer NOT NULL,
    group_name character varying(50),
    points integer DEFAULT 0,
    played integer DEFAULT 0,
    wins integer DEFAULT 0,
    draws integer DEFAULT 0,
    losses integer DEFAULT 0,
    goals_for integer DEFAULT 0,
    goals_against integer DEFAULT 0,
    goal_difference integer DEFAULT 0,
    recent_form character varying(10),
    qualification_status character varying(50),
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: TABLE competition_standings; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.competition_standings IS 'Classificação/standings de uma competição';


--
-- Name: competitions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.competitions (
    id uuid DEFAULT public.gen_random_uuid() NOT NULL,
    organization_id uuid NOT NULL,
    name character varying(200) NOT NULL,
    kind character varying(50),
    team_id uuid,
    season character varying(50),
    modality character varying(50) DEFAULT 'masculino'::character varying,
    competition_type character varying(50),
    format_details jsonb DEFAULT '{}'::jsonb,
    tiebreaker_criteria jsonb DEFAULT '["pontos", "saldo_gols", "gols_pro", "confronto_direto"]'::jsonb,
    points_per_win integer DEFAULT 2,
    status character varying(50) DEFAULT 'draft'::character varying,
    current_phase_id uuid,
    regulation_file_url character varying(500),
    regulation_notes text,
    created_by uuid,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    deleted_reason text,
    CONSTRAINT ck_competitions_deleted_reason CHECK ((((deleted_at IS NULL) AND (deleted_reason IS NULL)) OR ((deleted_at IS NOT NULL) AND (deleted_reason IS NOT NULL))))
);


--
-- Name: TABLE competitions; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.competitions IS 'Competições esportivas. Tabela principal do módulo de competições.';


--
-- Name: data_access_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.data_access_logs (
    id uuid DEFAULT public.gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    entity_type character varying(50) NOT NULL,
    entity_id uuid NOT NULL,
    athlete_id uuid,
    accessed_at timestamp with time zone DEFAULT now() NOT NULL,
    ip_address inet,
    user_agent text
);


--
-- Name: TABLE data_access_logs; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.data_access_logs IS 'Step 3: Log de auditoria LGPD - registra acesso de staff a dados de atletas (não self-access)';


--
-- Name: data_retention_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.data_retention_logs (
    id uuid DEFAULT public.gen_random_uuid() NOT NULL,
    table_name character varying(100) NOT NULL,
    records_anonymized integer NOT NULL,
    anonymized_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: TABLE data_retention_logs; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.data_retention_logs IS 'Step 3: Log de anonimização automática após 3 anos (política LGPD)';


--
-- Name: defensive_positions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.defensive_positions (
    id integer NOT NULL,
    code character varying(32) NOT NULL,
    name character varying(64) NOT NULL,
    abbreviation character varying(10),
    is_active boolean DEFAULT true NOT NULL
);


--
-- Name: TABLE defensive_positions; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.defensive_positions IS 'Posições defensivas. RD13: ID=5 é Goleira.';


--
-- Name: defensive_positions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.defensive_positions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: defensive_positions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.defensive_positions_id_seq OWNED BY public.defensive_positions.id;


--
-- Name: email_queue; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.email_queue (
    id uuid DEFAULT public.gen_random_uuid() NOT NULL,
    template_type character varying(50) NOT NULL,
    to_email character varying(255) NOT NULL,
    template_data jsonb NOT NULL,
    status character varying(20) NOT NULL,
    attempts integer NOT NULL,
    max_attempts integer NOT NULL,
    next_retry_at timestamp with time zone,
    last_error text,
    sent_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by_user_id uuid
);


--
-- Name: TABLE email_queue; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.email_queue IS 'Fila de emails com retry automático';


--
-- Name: COLUMN email_queue.template_type; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.email_queue.template_type IS 'invite, welcome, reset_password';


--
-- Name: COLUMN email_queue.template_data; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.email_queue.template_data IS 'Dados dinâmicos do template';


--
-- Name: COLUMN email_queue.status; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.email_queue.status IS 'pending, sent, failed, cancelled';


--
-- Name: COLUMN email_queue.attempts; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.email_queue.attempts IS 'Número de tentativas';


--
-- Name: COLUMN email_queue.max_attempts; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.email_queue.max_attempts IS 'Máximo de tentativas';


--
-- Name: COLUMN email_queue.next_retry_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.email_queue.next_retry_at IS 'Próxima tentativa';


--
-- Name: COLUMN email_queue.last_error; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.email_queue.last_error IS 'Última mensagem de erro';


--
-- Name: COLUMN email_queue.sent_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.email_queue.sent_at IS 'Quando foi enviado';


--
-- Name: event_subtypes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.event_subtypes (
    code character varying(64) NOT NULL,
    event_type_code character varying(64) NOT NULL,
    description character varying(255) NOT NULL
);


--
-- Name: TABLE event_subtypes; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.event_subtypes IS 'Subtipos de evento (shot_6m, shot_9m, shot_wing, turnover_pass, etc.).';


--
-- Name: event_types; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.event_types (
    code character varying(64) NOT NULL,
    description character varying(255) NOT NULL,
    is_shot boolean NOT NULL,
    is_possession_ending boolean NOT NULL
);


--
-- Name: TABLE event_types; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.event_types IS 'Tipos de evento (shot, goal, goalkeeper_save, turnover, foul, etc.).';


--
-- Name: exercise_favorites; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.exercise_favorites (
    user_id uuid NOT NULL,
    exercise_id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: TABLE exercise_favorites; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.exercise_favorites IS 'Step 3: Exercícios favoritados por usuário';


--
-- Name: exercise_tags; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.exercise_tags (
    id uuid DEFAULT public.gen_random_uuid() NOT NULL,
    name character varying(50) NOT NULL,
    parent_tag_id uuid,
    description text,
    display_order integer,
    is_active boolean DEFAULT false NOT NULL,
    suggested_by_user_id uuid,
    approved_by_admin_id uuid,
    approved_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: TABLE exercise_tags; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.exercise_tags IS 'Step 3: Tags hierárquicas de exercícios (Tático → Ataque Posicional, etc)';


--
-- Name: exercises; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.exercises (
    id uuid DEFAULT public.gen_random_uuid() NOT NULL,
    organization_id uuid NOT NULL,
    name character varying(200) NOT NULL,
    description text,
    tag_ids uuid[] DEFAULT '{}'::uuid[] NOT NULL,
    category character varying(100),
    media_url character varying(500),
    created_by_user_id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: TABLE exercises; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.exercises IS 'Step 3: Banco de exercícios com tags hierárquicas e busca GIN';


--
-- Name: export_jobs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.export_jobs (
    id uuid DEFAULT public.gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    export_type character varying(50) NOT NULL,
    params jsonb NOT NULL,
    params_hash character varying(64) NOT NULL,
    status character varying(20) DEFAULT 'pending'::character varying NOT NULL,
    file_url character varying(500),
    error_message text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    completed_at timestamp with time zone,
    CONSTRAINT ck_export_jobs_status CHECK (((status)::text = ANY ((ARRAY['pending'::character varying, 'processing'::character varying, 'completed'::character varying, 'failed'::character varying])::text[])))
);


--
-- Name: TABLE export_jobs; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.export_jobs IS 'Step 3: Jobs assíncronos de exportação PDF com cache por params_hash';


--
-- Name: export_rate_limits; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.export_rate_limits (
    user_id uuid NOT NULL,
    date date NOT NULL,
    count integer DEFAULT 0 NOT NULL
);


--
-- Name: TABLE export_rate_limits; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.export_rate_limits IS 'Step 3: Rate limiting de exportações - máximo 5 exports por dia por usuário';


--
-- Name: idempotency_keys; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.idempotency_keys (
    id uuid DEFAULT public.gen_random_uuid() NOT NULL,
    key character varying(255) NOT NULL,
    endpoint character varying(255) NOT NULL,
    request_hash character varying(64) NOT NULL,
    response_json jsonb,
    status_code integer,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    executed_at timestamp with time zone DEFAULT now() NOT NULL,
    script_name character varying(255),
    metadata jsonb
);


--
-- Name: TABLE idempotency_keys; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.idempotency_keys IS 'Controle de idempotência para retry seguro. FICHA.MD Fase 1.2';


--
-- Name: COLUMN idempotency_keys.key; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.idempotency_keys.key IS 'Chave única de idempotência fornecida pelo cliente (geralmente UUID)';


--
-- Name: COLUMN idempotency_keys.endpoint; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.idempotency_keys.endpoint IS 'Endpoint da API onde a chave foi utilizada';


--
-- Name: COLUMN idempotency_keys.request_hash; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.idempotency_keys.request_hash IS 'Hash SHA-256 do payload para validar consistência';


--
-- Name: COLUMN idempotency_keys.response_json; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.idempotency_keys.response_json IS 'Resposta completa para replay em caso de retry';


--
-- Name: COLUMN idempotency_keys.status_code; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.idempotency_keys.status_code IS 'Código HTTP da resposta armazenada';


--
-- Name: COLUMN idempotency_keys.created_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.idempotency_keys.created_at IS 'Data/hora do registro (para limpeza periódica)';


--
-- Name: match_events; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.match_events (
    id uuid DEFAULT public.gen_random_uuid() NOT NULL,
    match_id uuid NOT NULL,
    team_id uuid NOT NULL,
    opponent_team_id uuid,
    athlete_id uuid,
    assisting_athlete_id uuid,
    secondary_athlete_id uuid,
    period_number smallint NOT NULL,
    game_time_seconds integer NOT NULL,
    phase_of_play character varying(32) NOT NULL,
    possession_id uuid,
    advantage_state character varying(32) NOT NULL,
    score_our smallint NOT NULL,
    score_opponent smallint NOT NULL,
    event_type character varying(64) NOT NULL,
    event_subtype character varying(64),
    outcome character varying(64) NOT NULL,
    is_shot boolean NOT NULL,
    is_goal boolean NOT NULL,
    x_coord numeric(5,2),
    y_coord numeric(5,2),
    related_event_id uuid,
    source character varying(32) NOT NULL,
    notes text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by_user_id uuid NOT NULL,
    CONSTRAINT ck_match_events_period CHECK ((period_number >= 1)),
    CONSTRAINT ck_match_events_score_opponent CHECK ((score_opponent >= 0)),
    CONSTRAINT ck_match_events_score_our CHECK ((score_our >= 0)),
    CONSTRAINT ck_match_events_source CHECK (((source)::text = ANY ((ARRAY['live'::character varying, 'video'::character varying, 'post_game_correction'::character varying])::text[]))),
    CONSTRAINT ck_match_events_time CHECK ((game_time_seconds >= 0)),
    CONSTRAINT ck_match_events_x_coord CHECK (((x_coord IS NULL) OR ((x_coord >= (0)::numeric) AND (x_coord <= (100)::numeric)))),
    CONSTRAINT ck_match_events_y_coord CHECK (((y_coord IS NULL) OR ((y_coord >= (0)::numeric) AND (y_coord <= (100)::numeric))))
);


--
-- Name: TABLE match_events; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.match_events IS 'Eventos de jogo lance a lance. Coração analítico: reconstrói jogo, contexto tático e gera estatísticas.';


--
-- Name: match_periods; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.match_periods (
    id uuid DEFAULT public.gen_random_uuid() NOT NULL,
    match_id uuid NOT NULL,
    number smallint NOT NULL,
    duration_seconds integer NOT NULL,
    period_type character varying(32) NOT NULL,
    CONSTRAINT ck_match_periods_duration CHECK ((duration_seconds > 0)),
    CONSTRAINT ck_match_periods_number CHECK ((number >= 1)),
    CONSTRAINT ck_match_periods_type CHECK (((period_type)::text = ANY ((ARRAY['regular'::character varying, 'extra_time'::character varying, 'shootout_7m'::character varying])::text[])))
);


--
-- Name: TABLE match_periods; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.match_periods IS 'Estrutura de tempo dos jogos (1º tempo, 2º tempo, prorrogação, 7m).';


--
-- Name: match_possessions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.match_possessions (
    id uuid DEFAULT public.gen_random_uuid() NOT NULL,
    match_id uuid NOT NULL,
    team_id uuid NOT NULL,
    start_period_number smallint NOT NULL,
    start_time_seconds integer NOT NULL,
    end_period_number smallint NOT NULL,
    end_time_seconds integer NOT NULL,
    start_score_our smallint NOT NULL,
    start_score_opponent smallint NOT NULL,
    end_score_our smallint NOT NULL,
    end_score_opponent smallint NOT NULL,
    result character varying(32) NOT NULL,
    CONSTRAINT ck_match_possessions_end_period CHECK ((end_period_number >= start_period_number)),
    CONSTRAINT ck_match_possessions_end_time CHECK ((end_time_seconds >= 0)),
    CONSTRAINT ck_match_possessions_result CHECK (((result)::text = ANY ((ARRAY['goal'::character varying, 'turnover'::character varying, 'seven_meter_won'::character varying, 'time_over'::character varying])::text[]))),
    CONSTRAINT ck_match_possessions_start_period CHECK ((start_period_number >= 1)),
    CONSTRAINT ck_match_possessions_start_time CHECK ((start_time_seconds >= 0))
);


--
-- Name: TABLE match_possessions; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.match_possessions IS 'Sequências de posse de bola. Base para análise tática de eficiência.';


--
-- Name: match_roster; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.match_roster (
    id uuid DEFAULT public.gen_random_uuid() NOT NULL,
    match_id uuid NOT NULL,
    team_id uuid NOT NULL,
    athlete_id uuid NOT NULL,
    jersey_number smallint NOT NULL,
    is_starting boolean,
    is_goalkeeper boolean NOT NULL,
    is_available boolean NOT NULL,
    notes text,
    CONSTRAINT ck_match_roster_jersey CHECK ((jersey_number > 0))
);


--
-- Name: TABLE match_roster; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.match_roster IS 'Súmula/convocação oficial. Define quais atletas estão elegíveis para o jogo.';


--
-- Name: match_teams; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.match_teams (
    id uuid DEFAULT public.gen_random_uuid() NOT NULL,
    match_id uuid NOT NULL,
    team_id uuid NOT NULL,
    is_home boolean NOT NULL,
    is_our_team boolean NOT NULL
);


--
-- Name: TABLE match_teams; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.match_teams IS 'Ponte jogo ↔ equipes. Identifica quais equipes jogaram e com qual papel.';


--
-- Name: matches; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.matches (
    id uuid DEFAULT public.gen_random_uuid() NOT NULL,
    season_id uuid NOT NULL,
    competition_id uuid,
    match_date date NOT NULL,
    start_time time without time zone,
    venue character varying(120),
    phase character varying(32) NOT NULL,
    status character varying(32) NOT NULL,
    home_team_id uuid NOT NULL,
    away_team_id uuid NOT NULL,
    our_team_id uuid NOT NULL,
    final_score_home smallint,
    final_score_away smallint,
    notes text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by_user_id uuid NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    deleted_reason text,
    CONSTRAINT ck_matches_deleted_reason CHECK ((((deleted_at IS NULL) AND (deleted_reason IS NULL)) OR ((deleted_at IS NOT NULL) AND (deleted_reason IS NOT NULL)))),
    CONSTRAINT ck_matches_different_teams CHECK ((home_team_id <> away_team_id)),
    CONSTRAINT ck_matches_our_team CHECK (((our_team_id = home_team_id) OR (our_team_id = away_team_id))),
    CONSTRAINT ck_matches_phase CHECK (((phase)::text = ANY ((ARRAY['group'::character varying, 'semifinal'::character varying, 'final'::character varying, 'friendly'::character varying])::text[]))),
    CONSTRAINT ck_matches_score_away CHECK (((final_score_away IS NULL) OR (final_score_away >= 0))),
    CONSTRAINT ck_matches_score_home CHECK (((final_score_home IS NULL) OR (final_score_home >= 0))),
    CONSTRAINT ck_matches_status CHECK (((status)::text = ANY ((ARRAY['scheduled'::character varying, 'in_progress'::character varying, 'finished'::character varying, 'cancelled'::character varying])::text[])))
);


--
-- Name: TABLE matches; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.matches IS 'Jogos oficiais. Ponto de partida para convocação, súmula, eventos, estatísticas e relatórios.';


--
-- Name: medical_cases; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.medical_cases (
    id uuid DEFAULT public.gen_random_uuid() NOT NULL,
    athlete_id uuid NOT NULL,
    reason character varying(500),
    status character varying(50) DEFAULT 'ativo'::character varying,
    notes text,
    started_at timestamp with time zone DEFAULT now() NOT NULL,
    ended_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    deleted_reason text,
    organization_id uuid,
    created_by_user_id uuid,
    CONSTRAINT ck_medical_cases_deleted_reason CHECK ((((deleted_at IS NULL) AND (deleted_reason IS NULL)) OR ((deleted_at IS NOT NULL) AND (deleted_reason IS NOT NULL)))),
    CONSTRAINT medical_cases_status_check CHECK (((status)::text = ANY ((ARRAY['ativo'::character varying, 'resolvido'::character varying, 'em_acompanhamento'::character varying])::text[])))
);


--
-- Name: TABLE medical_cases; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.medical_cases IS 'Casos médicos de atletas. V1.2: RDB4 compliant (soft delete + deleted_reason).';


--
-- Name: notifications; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.notifications (
    id uuid DEFAULT public.gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    type character varying(50) NOT NULL,
    message text NOT NULL,
    notification_data jsonb,
    read_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: offensive_positions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.offensive_positions (
    id integer NOT NULL,
    code character varying(32) NOT NULL,
    name character varying(64) NOT NULL,
    abbreviation character varying(10),
    is_active boolean DEFAULT true NOT NULL
);


--
-- Name: TABLE offensive_positions; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.offensive_positions IS 'Posições ofensivas.';


--
-- Name: offensive_positions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.offensive_positions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: offensive_positions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.offensive_positions_id_seq OWNED BY public.offensive_positions.id;


--
-- Name: org_memberships; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.org_memberships (
    id uuid DEFAULT public.gen_random_uuid() NOT NULL,
    person_id uuid NOT NULL,
    role_id integer NOT NULL,
    organization_id uuid NOT NULL,
    start_at timestamp with time zone DEFAULT now() NOT NULL,
    end_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    deleted_reason text,
    created_by_user_id uuid,
    CONSTRAINT ck_org_memberships_deleted_reason CHECK ((((deleted_at IS NULL) AND (deleted_reason IS NULL)) OR ((deleted_at IS NOT NULL) AND (deleted_reason IS NOT NULL))))
);


--
-- Name: TABLE org_memberships; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.org_memberships IS 'Vínculos organizacionais (staff). V1.2: sem season_id; apenas org+person+role.';


--
-- Name: organizations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.organizations (
    id uuid DEFAULT public.gen_random_uuid() NOT NULL,
    name character varying(100) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    deleted_reason text,
    CONSTRAINT ck_organizations_deleted_reason CHECK ((((deleted_at IS NULL) AND (deleted_reason IS NULL)) OR ((deleted_at IS NOT NULL) AND (deleted_reason IS NOT NULL))))
);


--
-- Name: TABLE organizations; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.organizations IS 'Clubes/organizações esportivas. V1.2: suporta múltiplos clubes desde V1.';


--
-- Name: password_resets; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.password_resets (
    id uuid DEFAULT public.gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    token text NOT NULL,
    token_type text DEFAULT 'reset'::text NOT NULL,
    used boolean DEFAULT false NOT NULL,
    used_at timestamp with time zone,
    expires_at timestamp with time zone NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp with time zone,
    deleted_reason text,
    CONSTRAINT ck_password_resets_deleted_reason CHECK ((((deleted_at IS NULL) AND (deleted_reason IS NULL)) OR ((deleted_at IS NOT NULL) AND (deleted_reason IS NOT NULL)))),
    CONSTRAINT ck_password_resets_token_type CHECK ((token_type = ANY (ARRAY['reset'::text, 'welcome'::text])))
);


--
-- Name: TABLE password_resets; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.password_resets IS 'Email-based password reset tokens. R29: soft delete. Token expires in 24h.';


--
-- Name: permissions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.permissions (
    id smallint NOT NULL,
    code character varying(64) NOT NULL,
    description text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: TABLE permissions; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.permissions IS 'Permissões do sistema. R24: aplicadas via papel.';


--
-- Name: permissions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.permissions_id_seq
    AS smallint
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: permissions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.permissions_id_seq OWNED BY public.permissions.id;


--
-- Name: person_addresses; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.person_addresses (
    id uuid DEFAULT public.gen_random_uuid() NOT NULL,
    person_id uuid NOT NULL,
    address_type character varying(50) NOT NULL,
    street character varying(200) NOT NULL,
    number character varying(20),
    complement character varying(100),
    neighborhood character varying(100),
    city character varying(100) NOT NULL,
    state character varying(2) NOT NULL,
    postal_code character varying(10),
    country character varying(100) DEFAULT 'Brasil'::character varying NOT NULL,
    is_primary boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    deleted_reason text,
    created_by_user_id uuid,
    CONSTRAINT ck_person_addresses_deleted_reason CHECK ((((deleted_at IS NULL) AND (deleted_reason IS NULL)) OR ((deleted_at IS NOT NULL) AND (deleted_reason IS NOT NULL)))),
    CONSTRAINT ck_person_addresses_type CHECK (((address_type)::text = ANY ((ARRAY['residencial_1'::character varying, 'residencial_2'::character varying, 'comercial'::character varying, 'outro'::character varying])::text[])))
);


--
-- Name: TABLE person_addresses; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.person_addresses IS 'Endereços da pessoa. Suporta múltiplos endereços (residencial_1, residencial_2).';


--
-- Name: COLUMN person_addresses.created_by_user_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.person_addresses.created_by_user_id IS 'Usuário que criou o registro. R30/R31: auditoria obrigatória.';


--
-- Name: person_contacts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.person_contacts (
    id uuid DEFAULT public.gen_random_uuid() NOT NULL,
    person_id uuid NOT NULL,
    contact_type character varying(50) NOT NULL,
    contact_value character varying(200) NOT NULL,
    is_primary boolean DEFAULT false NOT NULL,
    is_verified boolean DEFAULT false NOT NULL,
    notes text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    deleted_reason text,
    created_by_user_id uuid,
    CONSTRAINT ck_person_contacts_deleted_reason CHECK ((((deleted_at IS NULL) AND (deleted_reason IS NULL)) OR ((deleted_at IS NOT NULL) AND (deleted_reason IS NOT NULL)))),
    CONSTRAINT ck_person_contacts_type CHECK (((contact_type)::text = ANY ((ARRAY['telefone'::character varying, 'email'::character varying, 'whatsapp'::character varying, 'outro'::character varying])::text[])))
);


--
-- Name: TABLE person_contacts; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.person_contacts IS 'Contatos da pessoa (telefone, email, whatsapp). Suporta múltiplos contatos por pessoa.';


--
-- Name: COLUMN person_contacts.created_by_user_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.person_contacts.created_by_user_id IS 'Usuário que criou o registro. R30/R31: auditoria obrigatória.';


--
-- Name: person_documents; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.person_documents (
    id uuid DEFAULT public.gen_random_uuid() NOT NULL,
    person_id uuid NOT NULL,
    document_type character varying(50) NOT NULL,
    document_number character varying(100) NOT NULL,
    issuing_authority character varying(100),
    issue_date date,
    expiry_date date,
    document_file_url text,
    is_verified boolean DEFAULT false NOT NULL,
    notes text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    deleted_reason text,
    created_by_user_id uuid,
    CONSTRAINT ck_person_documents_deleted_reason CHECK ((((deleted_at IS NULL) AND (deleted_reason IS NULL)) OR ((deleted_at IS NOT NULL) AND (deleted_reason IS NOT NULL)))),
    CONSTRAINT ck_person_documents_type CHECK (((document_type)::text = ANY ((ARRAY['cpf'::character varying, 'rg'::character varying, 'cnh'::character varying, 'passaporte'::character varying, 'certidao_nascimento'::character varying, 'titulo_eleitor'::character varying, 'outro'::character varying])::text[])))
);


--
-- Name: TABLE person_documents; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.person_documents IS 'Documentos oficiais da pessoa (CPF, RG, CNH, passaporte).';


--
-- Name: COLUMN person_documents.created_by_user_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.person_documents.created_by_user_id IS 'Usuário que criou o registro. R30/R31: auditoria obrigatória.';


--
-- Name: person_media; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.person_media (
    id uuid DEFAULT public.gen_random_uuid() NOT NULL,
    person_id uuid NOT NULL,
    media_type character varying(50) NOT NULL,
    file_url text NOT NULL,
    file_name character varying(255),
    file_size integer,
    mime_type character varying(100),
    is_primary boolean DEFAULT false NOT NULL,
    description text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    deleted_reason text,
    created_by_user_id uuid,
    CONSTRAINT ck_person_media_deleted_reason CHECK ((((deleted_at IS NULL) AND (deleted_reason IS NULL)) OR ((deleted_at IS NOT NULL) AND (deleted_reason IS NOT NULL)))),
    CONSTRAINT ck_person_media_type CHECK (((media_type)::text = ANY ((ARRAY['foto_perfil'::character varying, 'foto_documento'::character varying, 'video'::character varying, 'outro'::character varying])::text[])))
);


--
-- Name: TABLE person_media; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.person_media IS 'Mídias da pessoa (fotos de perfil, documentos digitalizados).';


--
-- Name: COLUMN person_media.created_by_user_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.person_media.created_by_user_id IS 'Usuário que criou o registro. R30/R31: auditoria obrigatória.';


--
-- Name: persons; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.persons (
    id uuid DEFAULT public.gen_random_uuid() NOT NULL,
    full_name text NOT NULL,
    birth_date date,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    deleted_reason text,
    first_name character varying(100) NOT NULL,
    last_name character varying(100) NOT NULL,
    gender character varying(20),
    nationality character varying(100) DEFAULT 'brasileira'::character varying,
    notes text,
    CONSTRAINT ck_persons_deleted_reason CHECK ((((deleted_at IS NULL) AND (deleted_reason IS NULL)) OR ((deleted_at IS NOT NULL) AND (deleted_reason IS NOT NULL)))),
    CONSTRAINT ck_persons_gender CHECK (((gender IS NULL) OR ((gender)::text = ANY ((ARRAY['masculino'::character varying, 'feminino'::character varying, 'outro'::character varying, 'prefiro_nao_dizer'::character varying])::text[]))))
);


--
-- Name: TABLE persons; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.persons IS 'R1: Pessoas físicas do sistema. Identidade básica (nome, gênero, nascimento). V1.2: normalizada.';


--
-- Name: COLUMN persons.first_name; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.persons.first_name IS 'Primeiro nome da pessoa';


--
-- Name: COLUMN persons.last_name; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.persons.last_name IS 'Sobrenome da pessoa';


--
-- Name: COLUMN persons.gender; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.persons.gender IS 'Gênero: masculino, feminino, outro, prefiro_nao_dizer';


--
-- Name: COLUMN persons.nationality; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.persons.nationality IS 'Nacionalidade (default: brasileira)';


--
-- Name: COLUMN persons.notes; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.persons.notes IS 'Observações gerais sobre a pessoa';


--
-- Name: phases_of_play; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.phases_of_play (
    code character varying(32) NOT NULL,
    description character varying(255) NOT NULL
);


--
-- Name: TABLE phases_of_play; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.phases_of_play IS 'Fases do jogo. Lookup table fixa com 4 fases.';


--
-- Name: refresh_tokens; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.refresh_tokens (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    token_hash character varying(255) NOT NULL,
    parent_id uuid,
    expires_at timestamp with time zone NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    revoked_at timestamp with time zone,
    ip_address inet,
    user_agent text
);


--
-- Name: role_permissions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.role_permissions (
    role_id smallint NOT NULL,
    permission_id smallint NOT NULL
);


--
-- Name: TABLE role_permissions; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.role_permissions IS 'Junction table: papéis ↔ permissões.';


--
-- Name: roles; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.roles (
    id smallint NOT NULL,
    code character varying(32) NOT NULL,
    name character varying(64) NOT NULL,
    description text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: TABLE roles; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.roles IS 'Papéis do sistema. R4: Dirigente, Coordenador, Treinador, Atleta.';


--
-- Name: roles_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.roles_id_seq
    AS smallint
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: roles_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.roles_id_seq OWNED BY public.roles.id;


--
-- Name: schooling_levels; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.schooling_levels (
    id integer NOT NULL,
    code character varying(32) NOT NULL,
    name character varying(64) NOT NULL,
    is_active boolean DEFAULT true NOT NULL
);


--
-- Name: TABLE schooling_levels; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.schooling_levels IS 'Níveis de escolaridade.';


--
-- Name: schooling_levels_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.schooling_levels_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: schooling_levels_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.schooling_levels_id_seq OWNED BY public.schooling_levels.id;


--
-- Name: seasons; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.seasons (
    id uuid DEFAULT public.gen_random_uuid() NOT NULL,
    team_id uuid NOT NULL,
    name character varying(120) NOT NULL,
    year integer NOT NULL,
    competition_type character varying(32),
    start_date date NOT NULL,
    end_date date NOT NULL,
    canceled_at timestamp with time zone,
    interrupted_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by_user_id uuid,
    deleted_at timestamp with time zone,
    deleted_reason text,
    CONSTRAINT ck_seasons_dates CHECK ((start_date < end_date)),
    CONSTRAINT ck_seasons_deleted_reason CHECK ((((deleted_at IS NULL) AND (deleted_reason IS NULL)) OR ((deleted_at IS NOT NULL) AND (deleted_reason IS NOT NULL))))
);


--
-- Name: TABLE seasons; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.seasons IS 'Temporadas por equipe. V1.2: team_id FK (não organization_id); múltiplas competições simultâneas.';


--
-- Name: COLUMN seasons.canceled_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.seasons.canceled_at IS 'RF5.1: Cancelamento pré-início (apenas se sem dados vinculados)';


--
-- Name: COLUMN seasons.interrupted_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.seasons.interrupted_at IS 'RF5.2: Interrupção pós-início (força maior)';


--
-- Name: session_templates; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.session_templates (
    id uuid NOT NULL,
    org_id uuid NOT NULL,
    name character varying(100) NOT NULL,
    description text,
    icon character varying(20) DEFAULT 'target'::character varying NOT NULL,
    focus_attack_positional_pct numeric(5,2) DEFAULT '0'::numeric NOT NULL,
    focus_defense_positional_pct numeric(5,2) DEFAULT '0'::numeric NOT NULL,
    focus_transition_offense_pct numeric(5,2) DEFAULT '0'::numeric NOT NULL,
    focus_transition_defense_pct numeric(5,2) DEFAULT '0'::numeric NOT NULL,
    focus_attack_technical_pct numeric(5,2) DEFAULT '0'::numeric NOT NULL,
    focus_defense_technical_pct numeric(5,2) DEFAULT '0'::numeric NOT NULL,
    focus_physical_pct numeric(5,2) DEFAULT '0'::numeric NOT NULL,
    is_favorite boolean DEFAULT false NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_by_membership_id uuid,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT chk_session_templates_icon CHECK (((icon)::text = ANY ((ARRAY['target'::character varying, 'activity'::character varying, 'bar-chart'::character varying, 'shield'::character varying, 'zap'::character varying, 'flame'::character varying])::text[]))),
    CONSTRAINT chk_session_templates_total_focus CHECK ((((((((focus_attack_positional_pct + focus_defense_positional_pct) + focus_transition_offense_pct) + focus_transition_defense_pct) + focus_attack_technical_pct) + focus_defense_technical_pct) + focus_physical_pct) <= (120)::numeric))
);


--
-- Name: team_memberships; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.team_memberships (
    id uuid DEFAULT public.gen_random_uuid() NOT NULL,
    person_id uuid NOT NULL,
    team_id uuid NOT NULL,
    org_membership_id uuid,
    start_at timestamp with time zone DEFAULT now() NOT NULL,
    end_at timestamp with time zone,
    status text DEFAULT 'pendente'::text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    deleted_reason text,
    resend_count integer DEFAULT 0 NOT NULL,
    CONSTRAINT check_team_memberships_status CHECK ((status = ANY (ARRAY['pendente'::text, 'ativo'::text, 'inativo'::text])))
);


--
-- Name: TABLE team_memberships; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.team_memberships IS 'Vínculo de staff (coordenadores/treinadores) com equipes específicas';


--
-- Name: COLUMN team_memberships.person_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.team_memberships.person_id IS 'Pessoa (staff)';


--
-- Name: COLUMN team_memberships.team_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.team_memberships.team_id IS 'Equipe';


--
-- Name: COLUMN team_memberships.org_membership_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.team_memberships.org_membership_id IS 'Referência ao cargo organizacional';


--
-- Name: COLUMN team_memberships.start_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.team_memberships.start_at IS 'Data de início do vínculo';


--
-- Name: COLUMN team_memberships.end_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.team_memberships.end_at IS 'Data de término; NULL = ativo';


--
-- Name: COLUMN team_memberships.status; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.team_memberships.status IS 'Status: pendente, ativo, inativo';


--
-- Name: team_registrations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.team_registrations (
    id uuid DEFAULT public.gen_random_uuid() NOT NULL,
    athlete_id uuid NOT NULL,
    team_id uuid NOT NULL,
    start_at timestamp with time zone DEFAULT now() NOT NULL,
    end_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    deleted_reason text,
    created_by_user_id uuid,
    CONSTRAINT ck_team_registrations_deleted_reason CHECK ((((deleted_at IS NULL) AND (deleted_reason IS NULL)) OR ((deleted_at IS NOT NULL) AND (deleted_reason IS NOT NULL))))
);


--
-- Name: TABLE team_registrations; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.team_registrations IS 'Vínculos de atletas com equipes. V1.2: múltiplos vínculos ativos simultâneos permitidos.';


--
-- Name: team_wellness_rankings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.team_wellness_rankings (
    id uuid DEFAULT public.gen_random_uuid() NOT NULL,
    team_id uuid NOT NULL,
    month_reference date NOT NULL,
    response_rate_pre numeric(5,2),
    response_rate_post numeric(5,2),
    avg_rate numeric(5,2),
    rank integer,
    athletes_90plus integer DEFAULT 0 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: TABLE team_wellness_rankings; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.team_wellness_rankings IS 'Step 3: Rankings mensais de equipes por taxa de resposta wellness';


--
-- Name: teams; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.teams (
    id uuid DEFAULT public.gen_random_uuid() NOT NULL,
    organization_id uuid NOT NULL,
    name character varying(120) NOT NULL,
    category_id integer NOT NULL,
    gender character varying(16) NOT NULL,
    is_our_team boolean DEFAULT true NOT NULL,
    active_from date,
    active_until date,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by_user_id uuid,
    deleted_at timestamp with time zone,
    deleted_reason text,
    season_id uuid,
    coach_membership_id uuid,
    created_by_membership_id uuid,
    alert_threshold_multiplier numeric(3,1) DEFAULT 2.0,
    CONSTRAINT ck_teams_active_dates CHECK (((active_from IS NULL) OR (active_until IS NULL) OR (active_from <= active_until))),
    CONSTRAINT ck_teams_deleted_reason CHECK ((((deleted_at IS NULL) AND (deleted_reason IS NULL)) OR ((deleted_at IS NOT NULL) AND (deleted_reason IS NOT NULL)))),
    CONSTRAINT ck_teams_gender CHECK (((gender)::text = ANY ((ARRAY['masculino'::character varying, 'feminino'::character varying])::text[]))),
    CONSTRAINT teams_alert_threshold_multiplier_check CHECK (((alert_threshold_multiplier >= 1.0) AND (alert_threshold_multiplier <= 3.0)))
);


--
-- Name: TABLE teams; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.teams IS 'Equipes esportivas. V1.2: sem season_id; gender obrigatório.';


--
-- Name: COLUMN teams.season_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.teams.season_id IS 'FK para seasons - vincula team a temporada específica';


--
-- Name: COLUMN teams.coach_membership_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.teams.coach_membership_id IS 'RF7 - Treinador principal atribuído à equipe';


--
-- Name: COLUMN teams.created_by_membership_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.teams.created_by_membership_id IS 'Auditoria - membership que criou a equipe';


--
-- Name: COLUMN teams.alert_threshold_multiplier; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.teams.alert_threshold_multiplier IS 'Step 3: Multiplicador para threshold de alertas (1.5 juvenis, 2.0 padrão, 2.5 adultos)';


--
-- Name: training_alerts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.training_alerts (
    id uuid DEFAULT public.gen_random_uuid() NOT NULL,
    team_id uuid NOT NULL,
    alert_type character varying(50) NOT NULL,
    severity character varying(20) NOT NULL,
    message text NOT NULL,
    alert_metadata jsonb,
    triggered_at timestamp with time zone DEFAULT now() NOT NULL,
    dismissed_at timestamp with time zone,
    dismissed_by_user_id uuid,
    CONSTRAINT ck_training_alerts_severity CHECK (((severity)::text = ANY ((ARRAY['warning'::character varying, 'critical'::character varying])::text[]))),
    CONSTRAINT ck_training_alerts_type CHECK (((alert_type)::text = ANY ((ARRAY['weekly_overload'::character varying, 'low_wellness_response'::character varying])::text[])))
);


--
-- Name: TABLE training_alerts; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.training_alerts IS 'Step 3: Alertas automáticos de sobrecarga semanal e baixa taxa de resposta wellness';


--
-- Name: training_analytics_cache; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.training_analytics_cache (
    id uuid DEFAULT public.gen_random_uuid() NOT NULL,
    team_id uuid NOT NULL,
    microcycle_id uuid,
    month date,
    granularity character varying(20) NOT NULL,
    total_sessions integer,
    avg_focus_attack_positional_pct numeric(5,2),
    avg_focus_defense_positional_pct numeric(5,2),
    avg_focus_transition_offense_pct numeric(5,2),
    avg_focus_transition_defense_pct numeric(5,2),
    avg_focus_attack_technical_pct numeric(5,2),
    avg_focus_defense_technical_pct numeric(5,2),
    avg_focus_physical_pct numeric(5,2),
    avg_rpe numeric(5,2),
    avg_internal_load numeric(10,2),
    total_internal_load numeric(12,2),
    attendance_rate numeric(5,2),
    wellness_response_rate_pre numeric(5,2),
    wellness_response_rate_post numeric(5,2),
    athletes_with_badges_count integer,
    deviation_count integer,
    threshold_mean numeric(10,2),
    threshold_stddev numeric(10,2),
    cache_dirty boolean DEFAULT true NOT NULL,
    calculated_at timestamp with time zone,
    CONSTRAINT ck_training_analytics_cache_granularity CHECK (((granularity)::text = ANY ((ARRAY['weekly'::character varying, 'monthly'::character varying])::text[])))
);


--
-- Name: TABLE training_analytics_cache; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.training_analytics_cache IS 'Step 3: Cache híbrido de analytics - weekly (granular) para mês corrente, monthly (agregado) para histórico';


--
-- Name: training_cycles; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.training_cycles (
    id uuid DEFAULT public.gen_random_uuid() NOT NULL,
    organization_id uuid NOT NULL,
    team_id uuid NOT NULL,
    type character varying NOT NULL,
    start_date date NOT NULL,
    end_date date NOT NULL,
    objective text,
    notes text,
    status character varying DEFAULT '''active'''::character varying NOT NULL,
    parent_cycle_id uuid,
    created_by_user_id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    deleted_reason text,
    CONSTRAINT check_cycle_dates CHECK ((start_date < end_date)),
    CONSTRAINT check_cycle_status CHECK (((status)::text = ANY ((ARRAY['active'::character varying, 'completed'::character varying, 'cancelled'::character varying])::text[]))),
    CONSTRAINT check_cycle_type CHECK (((type)::text = ANY ((ARRAY['macro'::character varying, 'meso'::character varying])::text[])))
);


--
-- Name: COLUMN training_cycles.type; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.training_cycles.type IS 'Tipo: ''macro'' ou ''meso''';


--
-- Name: COLUMN training_cycles.objective; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.training_cycles.objective IS 'Objetivo estratégico do ciclo';


--
-- Name: COLUMN training_cycles.status; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.training_cycles.status IS 'Status: active, completed, cancelled';


--
-- Name: COLUMN training_cycles.parent_cycle_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.training_cycles.parent_cycle_id IS 'FK para macrociclo (apenas mesociclos)';


--
-- Name: training_microcycles; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.training_microcycles (
    id uuid DEFAULT public.gen_random_uuid() NOT NULL,
    organization_id uuid NOT NULL,
    team_id uuid NOT NULL,
    week_start date NOT NULL,
    week_end date NOT NULL,
    cycle_id uuid,
    planned_focus_attack_positional_pct numeric(5,2),
    planned_focus_defense_positional_pct numeric(5,2),
    planned_focus_transition_offense_pct numeric(5,2),
    planned_focus_transition_defense_pct numeric(5,2),
    planned_focus_attack_technical_pct numeric(5,2),
    planned_focus_defense_technical_pct numeric(5,2),
    planned_focus_physical_pct numeric(5,2),
    planned_weekly_load integer,
    microcycle_type character varying,
    notes text,
    created_by_user_id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    deleted_reason text,
    CONSTRAINT check_microcycle_dates CHECK ((week_start < week_end))
);


--
-- Name: COLUMN training_microcycles.week_start; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.training_microcycles.week_start IS 'Início da semana (seg)';


--
-- Name: COLUMN training_microcycles.week_end; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.training_microcycles.week_end IS 'Fim da semana (dom)';


--
-- Name: COLUMN training_microcycles.cycle_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.training_microcycles.cycle_id IS 'FK para mesociclo';


--
-- Name: COLUMN training_microcycles.planned_focus_attack_positional_pct; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.training_microcycles.planned_focus_attack_positional_pct IS 'Percentual planejado de foco em ataque posicionado (0-100)';


--
-- Name: COLUMN training_microcycles.planned_focus_defense_positional_pct; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.training_microcycles.planned_focus_defense_positional_pct IS 'Percentual planejado de foco em defesa posicionada (0-100)';


--
-- Name: COLUMN training_microcycles.planned_focus_transition_offense_pct; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.training_microcycles.planned_focus_transition_offense_pct IS 'Percentual planejado de foco em transição ofensiva (0-100)';


--
-- Name: COLUMN training_microcycles.planned_focus_transition_defense_pct; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.training_microcycles.planned_focus_transition_defense_pct IS 'Percentual planejado de foco em transição defensiva (0-100)';


--
-- Name: COLUMN training_microcycles.planned_focus_attack_technical_pct; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.training_microcycles.planned_focus_attack_technical_pct IS 'Percentual planejado de foco em ataque técnico (0-100)';


--
-- Name: COLUMN training_microcycles.planned_focus_defense_technical_pct; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.training_microcycles.planned_focus_defense_technical_pct IS 'Percentual planejado de foco em defesa técnica (0-100)';


--
-- Name: COLUMN training_microcycles.planned_focus_physical_pct; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.training_microcycles.planned_focus_physical_pct IS 'Percentual planejado de foco em treino físico (0-100)';


--
-- Name: COLUMN training_microcycles.planned_weekly_load; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.training_microcycles.planned_weekly_load IS 'Carga planejada da semana (RPE × minutos)';


--
-- Name: COLUMN training_microcycles.microcycle_type; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.training_microcycles.microcycle_type IS 'Tipo: carga_alta, recuperacao, pre_jogo, etc.';


--
-- Name: training_session_exercises; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.training_session_exercises (
    id uuid DEFAULT public.gen_random_uuid() NOT NULL,
    session_id uuid NOT NULL,
    exercise_id uuid NOT NULL,
    order_index integer DEFAULT 0 NOT NULL,
    duration_minutes smallint,
    notes text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    CONSTRAINT ck_session_exercises_duration_positive CHECK (((duration_minutes IS NULL) OR (duration_minutes >= 0))),
    CONSTRAINT ck_session_exercises_order_positive CHECK ((order_index >= 0))
);


--
-- Name: TABLE training_session_exercises; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.training_session_exercises IS 'Vínculo entre sessões de treino e exercícios. ⚠️ Permite DUPLICATAS do mesmo exercício (circuitos/repetições).';


--
-- Name: training_sessions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.training_sessions (
    id uuid DEFAULT public.gen_random_uuid() NOT NULL,
    organization_id uuid NOT NULL,
    team_id uuid,
    season_id uuid,
    session_at timestamp with time zone NOT NULL,
    duration_planned_minutes smallint,
    location character varying(120),
    session_type character varying(32) NOT NULL,
    main_objective character varying(255),
    secondary_objective text,
    planned_load smallint,
    group_climate smallint,
    notes text,
    phase_focus_defense boolean DEFAULT false NOT NULL,
    phase_focus_attack boolean DEFAULT false NOT NULL,
    phase_focus_transition_offense boolean DEFAULT false NOT NULL,
    phase_focus_transition_defense boolean DEFAULT false NOT NULL,
    intensity_target smallint,
    session_block character varying(32),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by_user_id uuid NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    deleted_reason text,
    focus_attack_positional_pct numeric(5,2),
    focus_defense_positional_pct numeric(5,2),
    focus_transition_offense_pct numeric(5,2),
    focus_transition_defense_pct numeric(5,2),
    focus_attack_technical_pct numeric(5,2),
    focus_defense_technical_pct numeric(5,2),
    focus_physical_pct numeric(5,2),
    microcycle_id uuid,
    status character varying DEFAULT '''draft'''::character varying NOT NULL,
    closed_at timestamp with time zone,
    closed_by_user_id uuid,
    deviation_justification text,
    planning_deviation_flag boolean DEFAULT false NOT NULL,
    started_at timestamp with time zone,
    ended_at timestamp with time zone,
    duration_actual_minutes integer,
    execution_outcome public.training_execution_outcome_enum DEFAULT 'on_time'::public.training_execution_outcome_enum NOT NULL,
    delay_minutes integer,
    cancellation_reason text,
    post_review_completed_at timestamp with time zone,
    post_review_completed_by_user_id uuid,
    post_review_deadline_at timestamp with time zone,
    CONSTRAINT check_training_session_status CHECK (((status)::text = ANY ((ARRAY['draft'::character varying, 'scheduled'::character varying, 'in_progress'::character varying, 'pending_review'::character varying, 'readonly'::character varying])::text[]))),
    CONSTRAINT check_training_sessions_execution_outcome CHECK ((((execution_outcome = 'on_time'::public.training_execution_outcome_enum) AND (delay_minutes IS NULL) AND (cancellation_reason IS NULL) AND (duration_actual_minutes IS NULL)) OR ((execution_outcome = 'delayed'::public.training_execution_outcome_enum) AND (delay_minutes IS NOT NULL) AND (delay_minutes > 0) AND (cancellation_reason IS NULL)) OR ((execution_outcome = 'canceled'::public.training_execution_outcome_enum) AND (cancellation_reason IS NOT NULL) AND (delay_minutes IS NULL) AND (duration_actual_minutes IS NULL)) OR ((execution_outcome = ANY (ARRAY['shortened'::public.training_execution_outcome_enum, 'extended'::public.training_execution_outcome_enum])) AND (duration_actual_minutes IS NOT NULL) AND (duration_actual_minutes > 0) AND (delay_minutes IS NULL) AND (cancellation_reason IS NULL)))),
    CONSTRAINT ck_phase_focus_attack_consistency CHECK ((phase_focus_attack = ((COALESCE(focus_attack_positional_pct, (0)::numeric) + COALESCE(focus_attack_technical_pct, (0)::numeric)) >= (5)::numeric))),
    CONSTRAINT ck_phase_focus_defense_consistency CHECK ((phase_focus_defense = ((COALESCE(focus_defense_positional_pct, (0)::numeric) + COALESCE(focus_defense_technical_pct, (0)::numeric)) >= (5)::numeric))),
    CONSTRAINT ck_phase_focus_transition_defense_consistency CHECK ((phase_focus_transition_defense = (COALESCE(focus_transition_defense_pct, (0)::numeric) >= (5)::numeric))),
    CONSTRAINT ck_phase_focus_transition_offense_consistency CHECK ((phase_focus_transition_offense = (COALESCE(focus_transition_offense_pct, (0)::numeric) >= (5)::numeric))),
    CONSTRAINT ck_training_sessions_climate CHECK (((group_climate IS NULL) OR ((group_climate >= 1) AND (group_climate <= 5)))),
    CONSTRAINT ck_training_sessions_deleted_reason CHECK ((((deleted_at IS NULL) AND (deleted_reason IS NULL)) OR ((deleted_at IS NOT NULL) AND (deleted_reason IS NOT NULL)))),
    CONSTRAINT ck_training_sessions_focus_attack_positional_range CHECK (((focus_attack_positional_pct IS NULL) OR ((focus_attack_positional_pct >= (0)::numeric) AND (focus_attack_positional_pct <= (100)::numeric)))),
    CONSTRAINT ck_training_sessions_focus_attack_technical_range CHECK (((focus_attack_technical_pct IS NULL) OR ((focus_attack_technical_pct >= (0)::numeric) AND (focus_attack_technical_pct <= (100)::numeric)))),
    CONSTRAINT ck_training_sessions_focus_defense_positional_range CHECK (((focus_defense_positional_pct IS NULL) OR ((focus_defense_positional_pct >= (0)::numeric) AND (focus_defense_positional_pct <= (100)::numeric)))),
    CONSTRAINT ck_training_sessions_focus_defense_technical_range CHECK (((focus_defense_technical_pct IS NULL) OR ((focus_defense_technical_pct >= (0)::numeric) AND (focus_defense_technical_pct <= (100)::numeric)))),
    CONSTRAINT ck_training_sessions_focus_physical_range CHECK (((focus_physical_pct IS NULL) OR ((focus_physical_pct >= (0)::numeric) AND (focus_physical_pct <= (100)::numeric)))),
    CONSTRAINT ck_training_sessions_focus_total_sum CHECK ((((((((COALESCE(focus_attack_positional_pct, (0)::numeric) + COALESCE(focus_defense_positional_pct, (0)::numeric)) + COALESCE(focus_transition_offense_pct, (0)::numeric)) + COALESCE(focus_transition_defense_pct, (0)::numeric)) + COALESCE(focus_attack_technical_pct, (0)::numeric)) + COALESCE(focus_defense_technical_pct, (0)::numeric)) + COALESCE(focus_physical_pct, (0)::numeric)) <= (120)::numeric)),
    CONSTRAINT ck_training_sessions_focus_transition_defense_range CHECK (((focus_transition_defense_pct IS NULL) OR ((focus_transition_defense_pct >= (0)::numeric) AND (focus_transition_defense_pct <= (100)::numeric)))),
    CONSTRAINT ck_training_sessions_focus_transition_offense_range CHECK (((focus_transition_offense_pct IS NULL) OR ((focus_transition_offense_pct >= (0)::numeric) AND (focus_transition_offense_pct <= (100)::numeric)))),
    CONSTRAINT ck_training_sessions_intensity CHECK (((intensity_target IS NULL) OR ((intensity_target >= 1) AND (intensity_target <= 5)))),
    CONSTRAINT ck_training_sessions_type CHECK (((session_type)::text = ANY ((ARRAY['quadra'::character varying, 'fisico'::character varying, 'video'::character varying, 'reuniao'::character varying, 'teste'::character varying])::text[])))
);


--
-- Name: TABLE training_sessions; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.training_sessions IS 'Treinos. V1.2: team_id e season_id opcionais (treinos organizacionais, avaliações, captação).';


--
-- Name: COLUMN training_sessions.focus_attack_positional_pct; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.training_sessions.focus_attack_positional_pct IS 'Percentual aproximado (0-100) do tempo dedicado ao foco Ataque Posicionado. Usado em análise estratégica /statistics/teams.';


--
-- Name: COLUMN training_sessions.focus_defense_positional_pct; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.training_sessions.focus_defense_positional_pct IS 'Percentual aproximado (0-100) do tempo dedicado ao foco Defesa Posicionada. Usado em análise estratégica /statistics/teams.';


--
-- Name: COLUMN training_sessions.focus_transition_offense_pct; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.training_sessions.focus_transition_offense_pct IS 'Percentual aproximado (0-100) do tempo dedicado ao foco Transição Ofensiva. Usado em análise estratégica /statistics/teams.';


--
-- Name: COLUMN training_sessions.focus_transition_defense_pct; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.training_sessions.focus_transition_defense_pct IS 'Percentual aproximado (0-100) do tempo dedicado ao foco Transição Defensiva. Usado em análise estratégica /statistics/teams.';


--
-- Name: COLUMN training_sessions.focus_attack_technical_pct; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.training_sessions.focus_attack_technical_pct IS 'Percentual aproximado (0-100) do tempo dedicado ao foco Ataque Técnico. Usado em análise estratégica /statistics/teams.';


--
-- Name: COLUMN training_sessions.focus_defense_technical_pct; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.training_sessions.focus_defense_technical_pct IS 'Percentual aproximado (0-100) do tempo dedicado ao foco Defesa Técnica. Usado em análise estratégica /statistics/teams.';


--
-- Name: COLUMN training_sessions.focus_physical_pct; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.training_sessions.focus_physical_pct IS 'Percentual aproximado (0-100) do tempo dedicado ao foco Treino Físico. Usado em análise estratégica /statistics/teams.';


--
-- Name: COLUMN training_sessions.microcycle_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.training_sessions.microcycle_id IS 'FK para microciclo (planejamento semanal)';


--
-- Name: COLUMN training_sessions.status; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.training_sessions.status IS 'Status da sessão: draft (rascunho), scheduled (agendado), closed (fechado), readonly (somente leitura). in_progress é LEGADO e não deve ser usado - estado "Em andamento" é derivado via is_happening.';


--
-- Name: COLUMN training_sessions.closed_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.training_sessions.closed_at IS 'Timestamp de fechamento';


--
-- Name: COLUMN training_sessions.closed_by_user_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.training_sessions.closed_by_user_id IS 'Usuário que fechou a sessão';


--
-- Name: COLUMN training_sessions.deviation_justification; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.training_sessions.deviation_justification IS 'Justificativa de desvio em relação ao planejamento';


--
-- Name: COLUMN training_sessions.planning_deviation_flag; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.training_sessions.planning_deviation_flag IS 'Flag de desvio significativo (≥20pts ou ≥30% agregado)';


--
-- Name: training_suggestions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.training_suggestions (
    id uuid DEFAULT public.gen_random_uuid() NOT NULL,
    team_id uuid NOT NULL,
    type character varying(50) NOT NULL,
    origin_session_id uuid,
    target_session_ids uuid[],
    recommended_adjustment_pct numeric(5,2),
    reason text,
    status character varying(20) DEFAULT 'pending'::character varying NOT NULL,
    applied_at timestamp with time zone,
    dismissed_at timestamp with time zone,
    dismissal_reason text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_training_suggestions_status CHECK (((status)::text = ANY ((ARRAY['pending'::character varying, 'applied'::character varying, 'dismissed'::character varying])::text[]))),
    CONSTRAINT ck_training_suggestions_type CHECK (((type)::text = ANY ((ARRAY['compensation'::character varying, 'reduce_next_week'::character varying])::text[])))
);


--
-- Name: TABLE training_suggestions; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.training_suggestions IS 'Step 3: Sugestões automáticas de compensação de carga e redução de intensidade';


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    id uuid DEFAULT public.gen_random_uuid() NOT NULL,
    person_id uuid NOT NULL,
    email character varying(255) NOT NULL,
    password_hash text,
    is_superadmin boolean DEFAULT false NOT NULL,
    is_locked boolean DEFAULT false NOT NULL,
    status character varying(20) DEFAULT 'ativo'::character varying NOT NULL,
    expired_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    deleted_reason text,
    CONSTRAINT ck_users_deleted_reason CHECK ((((deleted_at IS NULL) AND (deleted_reason IS NULL)) OR ((deleted_at IS NOT NULL) AND (deleted_reason IS NOT NULL)))),
    CONSTRAINT ck_users_status CHECK (((status)::text = ANY ((ARRAY['ativo'::character varying, 'inativo'::character varying, 'arquivado'::character varying])::text[])))
);


--
-- Name: TABLE users; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.users IS 'Usuários com acesso ao sistema. R2, R3: Super Admin único e vitalício (RDB6).';


--
-- Name: wellness_post; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.wellness_post (
    id uuid DEFAULT public.gen_random_uuid() NOT NULL,
    organization_id uuid NOT NULL,
    training_session_id uuid NOT NULL,
    athlete_id uuid NOT NULL,
    session_rpe smallint NOT NULL,
    fatigue_after smallint NOT NULL,
    mood_after smallint NOT NULL,
    muscle_soreness_after smallint,
    notes text,
    perceived_intensity smallint,
    flag_medical_followup boolean DEFAULT false,
    filled_at timestamp with time zone DEFAULT now() NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by_user_id uuid NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    deleted_reason text,
    internal_load numeric(10,2) DEFAULT 0,
    minutes_effective smallint,
    locked_at timestamp with time zone,
    CONSTRAINT ck_wellness_post_deleted_reason CHECK ((((deleted_at IS NULL) AND (deleted_reason IS NULL)) OR ((deleted_at IS NOT NULL) AND (deleted_reason IS NOT NULL)))),
    CONSTRAINT ck_wellness_post_fatigue CHECK (((fatigue_after >= 0) AND (fatigue_after <= 10))),
    CONSTRAINT ck_wellness_post_intensity CHECK (((perceived_intensity IS NULL) OR ((perceived_intensity >= 1) AND (perceived_intensity <= 5)))),
    CONSTRAINT ck_wellness_post_mood CHECK (((mood_after >= 0) AND (mood_after <= 10))),
    CONSTRAINT ck_wellness_post_rpe CHECK (((session_rpe >= 0) AND (session_rpe <= 10))),
    CONSTRAINT ck_wellness_post_soreness CHECK (((muscle_soreness_after IS NULL) OR ((muscle_soreness_after >= 0) AND (muscle_soreness_after <= 10))))
);


--
-- Name: TABLE wellness_post; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.wellness_post IS 'Bem-estar pós-treino. V1.2: atleta preenche depois do treino, 1 por atleta × sessão.';


--
-- Name: COLUMN wellness_post.internal_load; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.wellness_post.internal_load IS 'Carga interna calculada automaticamente: minutes_effective × session_rpe';


--
-- Name: COLUMN wellness_post.minutes_effective; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.wellness_post.minutes_effective IS 'Minutos efetivos de participação do atleta (usado para cálculo de internal_load)';


--
-- Name: COLUMN wellness_post.locked_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.wellness_post.locked_at IS 'Step 3: Timestamp de lock - post editável até 24h após submission';


--
-- Name: wellness_pre; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.wellness_pre (
    id uuid DEFAULT public.gen_random_uuid() NOT NULL,
    organization_id uuid NOT NULL,
    training_session_id uuid NOT NULL,
    athlete_id uuid NOT NULL,
    sleep_hours numeric(4,1) NOT NULL,
    sleep_quality smallint NOT NULL,
    fatigue_pre smallint NOT NULL,
    stress_level smallint NOT NULL,
    muscle_soreness smallint NOT NULL,
    notes text,
    menstrual_cycle_phase character varying(32),
    readiness_score smallint,
    filled_at timestamp with time zone DEFAULT now() NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by_user_id uuid NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    deleted_reason text,
    locked_at timestamp with time zone,
    CONSTRAINT ck_wellness_pre_deleted_reason CHECK ((((deleted_at IS NULL) AND (deleted_reason IS NULL)) OR ((deleted_at IS NOT NULL) AND (deleted_reason IS NOT NULL)))),
    CONSTRAINT ck_wellness_pre_fatigue CHECK (((fatigue_pre >= 0) AND (fatigue_pre <= 10))),
    CONSTRAINT ck_wellness_pre_menstrual CHECK (((menstrual_cycle_phase IS NULL) OR ((menstrual_cycle_phase)::text = ANY ((ARRAY['folicular'::character varying, 'lutea'::character varying, 'menstruacao'::character varying, 'nao_informa'::character varying])::text[])))),
    CONSTRAINT ck_wellness_pre_readiness CHECK (((readiness_score IS NULL) OR ((readiness_score >= 0) AND (readiness_score <= 10)))),
    CONSTRAINT ck_wellness_pre_sleep_hours CHECK (((sleep_hours >= (0)::numeric) AND (sleep_hours <= (24)::numeric))),
    CONSTRAINT ck_wellness_pre_sleep_quality CHECK (((sleep_quality >= 1) AND (sleep_quality <= 5))),
    CONSTRAINT ck_wellness_pre_soreness CHECK (((muscle_soreness >= 0) AND (muscle_soreness <= 10))),
    CONSTRAINT ck_wellness_pre_stress CHECK (((stress_level >= 0) AND (stress_level <= 10)))
);


--
-- Name: TABLE wellness_pre; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.wellness_pre IS 'Bem-estar pré-treino. V1.2: atleta preenche antes do treino, 1 por atleta × sessão.';


--
-- Name: COLUMN wellness_pre.locked_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.wellness_pre.locked_at IS 'Step 3: Timestamp de lock - pré editável até 2h antes da sessão';


--
-- Name: v_anonymization_status; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.v_anonymization_status AS
 WITH cutoff AS (
         SELECT (now() - '3 years'::interval) AS cutoff_date
        ), wellness_pre_eligible AS (
         SELECT 'wellness_pre'::text AS table_name,
            count(*) AS eligible_count,
            min(wellness_pre.filled_at) AS oldest_record_date,
            max(wellness_pre.filled_at) AS newest_eligible_date
           FROM public.wellness_pre,
            cutoff
          WHERE ((wellness_pre.filled_at < cutoff.cutoff_date) AND (wellness_pre.athlete_id IS NOT NULL) AND (wellness_pre.deleted_at IS NULL))
        ), wellness_post_eligible AS (
         SELECT 'wellness_post'::text AS table_name,
            count(*) AS eligible_count,
            min(wellness_post.filled_at) AS oldest_record_date,
            max(wellness_post.filled_at) AS newest_eligible_date
           FROM public.wellness_post,
            cutoff
          WHERE ((wellness_post.filled_at < cutoff.cutoff_date) AND (wellness_post.athlete_id IS NOT NULL) AND (wellness_post.deleted_at IS NULL))
        ), attendance_eligible AS (
         SELECT 'attendance'::text AS table_name,
            count(*) AS eligible_count,
            min(attendance.created_at) AS oldest_record_date,
            max(attendance.created_at) AS newest_eligible_date
           FROM public.attendance,
            cutoff
          WHERE ((attendance.created_at < cutoff.cutoff_date) AND (attendance.athlete_id IS NOT NULL) AND (attendance.deleted_at IS NULL))
        ), badges_eligible AS (
         SELECT 'athlete_badges'::text AS table_name,
            count(*) AS eligible_count,
            min(athlete_badges.earned_at) AS oldest_record_date,
            max(athlete_badges.earned_at) AS newest_eligible_date
           FROM public.athlete_badges,
            cutoff
          WHERE ((athlete_badges.earned_at < cutoff.cutoff_date) AND (athlete_badges.athlete_id IS NOT NULL))
        ), last_run AS (
         SELECT data_retention_logs.table_name AS last_run_table,
            data_retention_logs.records_anonymized AS last_run_count,
            data_retention_logs.anonymized_at AS last_run_date
           FROM public.data_retention_logs
          ORDER BY data_retention_logs.anonymized_at DESC
         LIMIT 1
        ), all_eligible AS (
         SELECT wellness_pre_eligible.table_name,
            wellness_pre_eligible.eligible_count,
            wellness_pre_eligible.oldest_record_date,
            wellness_pre_eligible.newest_eligible_date
           FROM wellness_pre_eligible
        UNION ALL
         SELECT wellness_post_eligible.table_name,
            wellness_post_eligible.eligible_count,
            wellness_post_eligible.oldest_record_date,
            wellness_post_eligible.newest_eligible_date
           FROM wellness_post_eligible
        UNION ALL
         SELECT attendance_eligible.table_name,
            attendance_eligible.eligible_count,
            attendance_eligible.oldest_record_date,
            attendance_eligible.newest_eligible_date
           FROM attendance_eligible
        UNION ALL
         SELECT badges_eligible.table_name,
            badges_eligible.eligible_count,
            badges_eligible.oldest_record_date,
            badges_eligible.newest_eligible_date
           FROM badges_eligible
        )
 SELECT e.table_name,
    e.eligible_count,
    e.oldest_record_date,
    e.newest_eligible_date,
    ( SELECT cutoff.cutoff_date
           FROM cutoff) AS cutoff_date,
    ( SELECT last_run.last_run_date
           FROM last_run) AS last_anonymization_run,
    ( SELECT last_run.last_run_count
           FROM last_run) AS last_run_records,
        CASE
            WHEN (e.eligible_count = 0) THEN 'compliant'::text
            WHEN (e.eligible_count < 100) THEN 'attention'::text
            WHEN (e.eligible_count < 1000) THEN 'warning'::text
            ELSE 'critical'::text
        END AS status_severity
   FROM all_eligible e
  WHERE (e.eligible_count > 0)
UNION ALL
 SELECT 'TOTAL'::text AS table_name,
    sum(all_eligible.eligible_count) AS eligible_count,
    min(all_eligible.oldest_record_date) AS oldest_record_date,
    max(all_eligible.newest_eligible_date) AS newest_eligible_date,
    ( SELECT cutoff.cutoff_date
           FROM cutoff) AS cutoff_date,
    ( SELECT last_run.last_run_date
           FROM last_run) AS last_anonymization_run,
    ( SELECT last_run.last_run_count
           FROM last_run) AS last_run_records,
        CASE
            WHEN (sum(all_eligible.eligible_count) = (0)::numeric) THEN 'compliant'::text
            WHEN (sum(all_eligible.eligible_count) < (500)::numeric) THEN 'attention'::text
            WHEN (sum(all_eligible.eligible_count) < (5000)::numeric) THEN 'warning'::text
            ELSE 'critical'::text
        END AS status_severity
   FROM all_eligible;


--
-- Name: VIEW v_anonymization_status; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON VIEW public.v_anonymization_status IS 'Real-time status of records eligible for anonymization (LGPD Art. 16).
        Shows counts per table and severity levels for compliance dashboard.';


--
-- Name: wellness_reminders; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.wellness_reminders (
    id uuid DEFAULT public.gen_random_uuid() NOT NULL,
    training_session_id uuid NOT NULL,
    athlete_id uuid NOT NULL,
    sent_at timestamp with time zone NOT NULL,
    responded_at timestamp with time zone,
    reminder_count integer DEFAULT 0 NOT NULL,
    locked_at timestamp with time zone
);


--
-- Name: TABLE wellness_reminders; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.wellness_reminders IS 'Step 3: Tracking de lembretes wellness enviados aos atletas';


--
-- Name: categories id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.categories ALTER COLUMN id SET DEFAULT nextval('public.categories_id_seq'::regclass);


--
-- Name: defensive_positions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.defensive_positions ALTER COLUMN id SET DEFAULT nextval('public.defensive_positions_id_seq'::regclass);


--
-- Name: offensive_positions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.offensive_positions ALTER COLUMN id SET DEFAULT nextval('public.offensive_positions_id_seq'::regclass);


--
-- Name: permissions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.permissions ALTER COLUMN id SET DEFAULT nextval('public.permissions_id_seq'::regclass);


--
-- Name: roles id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.roles ALTER COLUMN id SET DEFAULT nextval('public.roles_id_seq'::regclass);


--
-- Name: schooling_levels id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.schooling_levels ALTER COLUMN id SET DEFAULT nextval('public.schooling_levels_id_seq'::regclass);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: athlete_badges athlete_badges_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.athlete_badges
    ADD CONSTRAINT athlete_badges_pkey PRIMARY KEY (id);


--
-- Name: data_access_logs data_access_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.data_access_logs
    ADD CONSTRAINT data_access_logs_pkey PRIMARY KEY (id);


--
-- Name: data_retention_logs data_retention_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.data_retention_logs
    ADD CONSTRAINT data_retention_logs_pkey PRIMARY KEY (id);


--
-- Name: email_queue email_queue_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.email_queue
    ADD CONSTRAINT email_queue_pkey PRIMARY KEY (id);


--
-- Name: exercise_favorites exercise_favorites_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.exercise_favorites
    ADD CONSTRAINT exercise_favorites_pkey PRIMARY KEY (user_id, exercise_id);


--
-- Name: exercise_tags exercise_tags_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.exercise_tags
    ADD CONSTRAINT exercise_tags_name_key UNIQUE (name);


--
-- Name: exercise_tags exercise_tags_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.exercise_tags
    ADD CONSTRAINT exercise_tags_pkey PRIMARY KEY (id);


--
-- Name: exercises exercises_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.exercises
    ADD CONSTRAINT exercises_pkey PRIMARY KEY (id);


--
-- Name: export_jobs export_jobs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.export_jobs
    ADD CONSTRAINT export_jobs_pkey PRIMARY KEY (id);


--
-- Name: export_rate_limits export_rate_limits_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.export_rate_limits
    ADD CONSTRAINT export_rate_limits_pkey PRIMARY KEY (user_id, date);


--
-- Name: idempotency_keys idempotency_keys_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.idempotency_keys
    ADD CONSTRAINT idempotency_keys_pkey PRIMARY KEY (id);


--
-- Name: notifications notifications_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_pkey PRIMARY KEY (id);


--
-- Name: password_resets password_resets_token_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.password_resets
    ADD CONSTRAINT password_resets_token_key UNIQUE (token);


--
-- Name: person_addresses person_addresses_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.person_addresses
    ADD CONSTRAINT person_addresses_pkey PRIMARY KEY (id);


--
-- Name: person_contacts person_contacts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.person_contacts
    ADD CONSTRAINT person_contacts_pkey PRIMARY KEY (id);


--
-- Name: person_documents person_documents_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.person_documents
    ADD CONSTRAINT person_documents_pkey PRIMARY KEY (id);


--
-- Name: person_media person_media_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.person_media
    ADD CONSTRAINT person_media_pkey PRIMARY KEY (id);


--
-- Name: advantage_states pk_advantage_states; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.advantage_states
    ADD CONSTRAINT pk_advantage_states PRIMARY KEY (code);


--
-- Name: athletes pk_athletes; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.athletes
    ADD CONSTRAINT pk_athletes PRIMARY KEY (id);


--
-- Name: attendance pk_attendance; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.attendance
    ADD CONSTRAINT pk_attendance PRIMARY KEY (id);


--
-- Name: audit_logs pk_audit_logs; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT pk_audit_logs PRIMARY KEY (id);


--
-- Name: categories pk_categories; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.categories
    ADD CONSTRAINT pk_categories PRIMARY KEY (id);


--
-- Name: competition_matches pk_competition_matches; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.competition_matches
    ADD CONSTRAINT pk_competition_matches PRIMARY KEY (id);


--
-- Name: competition_opponent_teams pk_competition_opponent_teams; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.competition_opponent_teams
    ADD CONSTRAINT pk_competition_opponent_teams PRIMARY KEY (id);


--
-- Name: competition_phases pk_competition_phases; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.competition_phases
    ADD CONSTRAINT pk_competition_phases PRIMARY KEY (id);


--
-- Name: competition_seasons pk_competition_seasons; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.competition_seasons
    ADD CONSTRAINT pk_competition_seasons PRIMARY KEY (id);


--
-- Name: competition_standings pk_competition_standings; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.competition_standings
    ADD CONSTRAINT pk_competition_standings PRIMARY KEY (id);


--
-- Name: competitions pk_competitions; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.competitions
    ADD CONSTRAINT pk_competitions PRIMARY KEY (id);


--
-- Name: defensive_positions pk_defensive_positions; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.defensive_positions
    ADD CONSTRAINT pk_defensive_positions PRIMARY KEY (id);


--
-- Name: event_subtypes pk_event_subtypes; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_subtypes
    ADD CONSTRAINT pk_event_subtypes PRIMARY KEY (code);


--
-- Name: event_types pk_event_types; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_types
    ADD CONSTRAINT pk_event_types PRIMARY KEY (code);


--
-- Name: match_events pk_match_events; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.match_events
    ADD CONSTRAINT pk_match_events PRIMARY KEY (id);


--
-- Name: match_periods pk_match_periods; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.match_periods
    ADD CONSTRAINT pk_match_periods PRIMARY KEY (id);


--
-- Name: match_possessions pk_match_possessions; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.match_possessions
    ADD CONSTRAINT pk_match_possessions PRIMARY KEY (id);


--
-- Name: match_roster pk_match_roster; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.match_roster
    ADD CONSTRAINT pk_match_roster PRIMARY KEY (id);


--
-- Name: match_teams pk_match_teams; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.match_teams
    ADD CONSTRAINT pk_match_teams PRIMARY KEY (id);


--
-- Name: matches pk_matches; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.matches
    ADD CONSTRAINT pk_matches PRIMARY KEY (id);


--
-- Name: medical_cases pk_medical_cases; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.medical_cases
    ADD CONSTRAINT pk_medical_cases PRIMARY KEY (id);


--
-- Name: offensive_positions pk_offensive_positions; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.offensive_positions
    ADD CONSTRAINT pk_offensive_positions PRIMARY KEY (id);


--
-- Name: org_memberships pk_org_memberships; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.org_memberships
    ADD CONSTRAINT pk_org_memberships PRIMARY KEY (id);


--
-- Name: organizations pk_organizations; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organizations
    ADD CONSTRAINT pk_organizations PRIMARY KEY (id);


--
-- Name: password_resets pk_password_resets; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.password_resets
    ADD CONSTRAINT pk_password_resets PRIMARY KEY (id);


--
-- Name: permissions pk_permissions; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.permissions
    ADD CONSTRAINT pk_permissions PRIMARY KEY (id);


--
-- Name: persons pk_persons; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.persons
    ADD CONSTRAINT pk_persons PRIMARY KEY (id);


--
-- Name: phases_of_play pk_phases_of_play; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.phases_of_play
    ADD CONSTRAINT pk_phases_of_play PRIMARY KEY (code);


--
-- Name: role_permissions pk_role_permissions; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.role_permissions
    ADD CONSTRAINT pk_role_permissions PRIMARY KEY (role_id, permission_id);


--
-- Name: roles pk_roles; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT pk_roles PRIMARY KEY (id);


--
-- Name: schooling_levels pk_schooling_levels; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.schooling_levels
    ADD CONSTRAINT pk_schooling_levels PRIMARY KEY (id);


--
-- Name: seasons pk_seasons; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.seasons
    ADD CONSTRAINT pk_seasons PRIMARY KEY (id);


--
-- Name: team_registrations pk_team_registrations; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.team_registrations
    ADD CONSTRAINT pk_team_registrations PRIMARY KEY (id);


--
-- Name: teams pk_teams; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teams
    ADD CONSTRAINT pk_teams PRIMARY KEY (id);


--
-- Name: training_sessions pk_training_sessions; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.training_sessions
    ADD CONSTRAINT pk_training_sessions PRIMARY KEY (id);


--
-- Name: users pk_users; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT pk_users PRIMARY KEY (id);


--
-- Name: wellness_post pk_wellness_post; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.wellness_post
    ADD CONSTRAINT pk_wellness_post PRIMARY KEY (id);


--
-- Name: wellness_pre pk_wellness_pre; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.wellness_pre
    ADD CONSTRAINT pk_wellness_pre PRIMARY KEY (id);


--
-- Name: refresh_tokens refresh_tokens_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.refresh_tokens
    ADD CONSTRAINT refresh_tokens_pkey PRIMARY KEY (id);


--
-- Name: session_templates session_templates_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.session_templates
    ADD CONSTRAINT session_templates_pkey PRIMARY KEY (id);


--
-- Name: team_memberships team_memberships_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.team_memberships
    ADD CONSTRAINT team_memberships_pkey PRIMARY KEY (id);


--
-- Name: team_wellness_rankings team_wellness_rankings_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.team_wellness_rankings
    ADD CONSTRAINT team_wellness_rankings_pkey PRIMARY KEY (id);


--
-- Name: training_alerts training_alerts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.training_alerts
    ADD CONSTRAINT training_alerts_pkey PRIMARY KEY (id);


--
-- Name: training_analytics_cache training_analytics_cache_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.training_analytics_cache
    ADD CONSTRAINT training_analytics_cache_pkey PRIMARY KEY (id);


--
-- Name: training_cycles training_cycles_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.training_cycles
    ADD CONSTRAINT training_cycles_pkey PRIMARY KEY (id);


--
-- Name: training_microcycles training_microcycles_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.training_microcycles
    ADD CONSTRAINT training_microcycles_pkey PRIMARY KEY (id);


--
-- Name: training_session_exercises training_session_exercises_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.training_session_exercises
    ADD CONSTRAINT training_session_exercises_pkey PRIMARY KEY (id);


--
-- Name: training_suggestions training_suggestions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.training_suggestions
    ADD CONSTRAINT training_suggestions_pkey PRIMARY KEY (id);


--
-- Name: competition_seasons uk_competition_seasons_competition_season; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.competition_seasons
    ADD CONSTRAINT uk_competition_seasons_competition_season UNIQUE (competition_id, season_id);


--
-- Name: competition_standings uk_competition_standings_team_phase; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.competition_standings
    ADD CONSTRAINT uk_competition_standings_team_phase UNIQUE (competition_id, phase_id, opponent_team_id);


--
-- Name: idempotency_keys uq_idempotency_key_endpoint; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.idempotency_keys
    ADD CONSTRAINT uq_idempotency_key_endpoint UNIQUE (key, endpoint);


--
-- Name: session_templates uq_session_templates_org_name; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.session_templates
    ADD CONSTRAINT uq_session_templates_org_name UNIQUE (org_id, name);


--
-- Name: team_wellness_rankings uq_team_wellness_rankings_team_month; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.team_wellness_rankings
    ADD CONSTRAINT uq_team_wellness_rankings_team_month UNIQUE (team_id, month_reference);


--
-- Name: training_analytics_cache uq_training_analytics_cache_lookup; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.training_analytics_cache
    ADD CONSTRAINT uq_training_analytics_cache_lookup UNIQUE (team_id, microcycle_id, month, granularity);


--
-- Name: wellness_reminders uq_wellness_reminders_session_athlete; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.wellness_reminders
    ADD CONSTRAINT uq_wellness_reminders_session_athlete UNIQUE (training_session_id, athlete_id);


--
-- Name: categories ux_categories_name; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.categories
    ADD CONSTRAINT ux_categories_name UNIQUE (name);


--
-- Name: defensive_positions ux_defensive_positions_code; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.defensive_positions
    ADD CONSTRAINT ux_defensive_positions_code UNIQUE (code);


--
-- Name: offensive_positions ux_offensive_positions_code; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.offensive_positions
    ADD CONSTRAINT ux_offensive_positions_code UNIQUE (code);


--
-- Name: permissions ux_permissions_code; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.permissions
    ADD CONSTRAINT ux_permissions_code UNIQUE (code);


--
-- Name: roles ux_roles_code; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT ux_roles_code UNIQUE (code);


--
-- Name: roles ux_roles_name; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT ux_roles_name UNIQUE (name);


--
-- Name: schooling_levels ux_schooling_levels_code; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.schooling_levels
    ADD CONSTRAINT ux_schooling_levels_code UNIQUE (code);


--
-- Name: wellness_reminders wellness_reminders_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.wellness_reminders
    ADD CONSTRAINT wellness_reminders_pkey PRIMARY KEY (id);


--
-- Name: idx_access_logs_accessed_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_access_logs_accessed_at ON public.data_access_logs USING btree (accessed_at);


--
-- Name: idx_access_logs_athlete; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_access_logs_athlete ON public.data_access_logs USING btree (athlete_id, accessed_at);


--
-- Name: idx_access_logs_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_access_logs_user ON public.data_access_logs USING btree (user_id, accessed_at);


--
-- Name: idx_alerts_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_alerts_active ON public.training_alerts USING btree (team_id, triggered_at) WHERE (dismissed_at IS NULL);


--
-- Name: idx_analytics_lookup; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_analytics_lookup ON public.training_analytics_cache USING btree (team_id, granularity, cache_dirty) WHERE (cache_dirty = false);


--
-- Name: INDEX idx_analytics_lookup; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON INDEX public.idx_analytics_lookup IS 'Optimizes analytics cache queries. Partial index: only valid (non-dirty) cache entries.
        Used by TrainingAnalyticsService for summary and load queries.';


--
-- Name: idx_athletes_person_deleted; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_athletes_person_deleted ON public.athletes USING btree (person_id, deleted_at) WHERE (deleted_at IS NULL);


--
-- Name: idx_attendance_corrections; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_attendance_corrections ON public.attendance USING btree (correction_by_user_id, correction_at) WHERE ((source)::text = 'correction'::text);


--
-- Name: idx_attendance_session; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_attendance_session ON public.attendance USING btree (training_session_id);


--
-- Name: idx_badges_athlete_month; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_badges_athlete_month ON public.athlete_badges USING btree (athlete_id, month_reference);


--
-- Name: INDEX idx_badges_athlete_month; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON INDEX public.idx_badges_athlete_month IS 'Optimizes badge queries by athlete and month. Used in athlete profile badges section.';


--
-- Name: idx_exercises_tags; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_exercises_tags ON public.exercises USING gin (tag_ids);


--
-- Name: idx_export_cache; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_export_cache ON public.export_jobs USING btree (params_hash, status) WHERE ((status)::text = 'completed'::text);


--
-- Name: idx_medical_cases_athlete; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_medical_cases_athlete ON public.medical_cases USING btree (athlete_id);


--
-- Name: idx_medical_cases_organization_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_medical_cases_organization_id ON public.medical_cases USING btree (organization_id);


--
-- Name: idx_notifications_cleanup; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_notifications_cleanup ON public.notifications USING btree (read_at, created_at);


--
-- Name: idx_notifications_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_notifications_created ON public.notifications USING btree (created_at DESC);


--
-- Name: idx_notifications_unread; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_notifications_unread ON public.notifications USING btree (user_id, created_at DESC) WHERE (read_at IS NULL);


--
-- Name: INDEX idx_notifications_unread; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON INDEX public.idx_notifications_unread IS 'Optimizes unread notification count and listing. Partial index: only unread notifications.
        Used in navbar badge and notifications dropdown.';


--
-- Name: idx_notifications_user_read; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_notifications_user_read ON public.notifications USING btree (user_id, read_at);


--
-- Name: idx_rankings_month_rank; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_rankings_month_rank ON public.team_wellness_rankings USING btree (month_reference, rank);


--
-- Name: idx_rankings_team_month; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_rankings_team_month ON public.team_wellness_rankings USING btree (team_id, month_reference);


--
-- Name: INDEX idx_rankings_team_month; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON INDEX public.idx_rankings_team_month IS 'Optimizes team ranking queries. Used in analytics dashboard and team comparison.';


--
-- Name: idx_session_exercises_exercise; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_session_exercises_exercise ON public.training_session_exercises USING btree (exercise_id) WHERE (deleted_at IS NULL);


--
-- Name: idx_session_exercises_session_order; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_session_exercises_session_order ON public.training_session_exercises USING btree (session_id, order_index, deleted_at) WHERE (deleted_at IS NULL);


--
-- Name: idx_session_exercises_session_order_unique; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX idx_session_exercises_session_order_unique ON public.training_session_exercises USING btree (session_id, order_index) WHERE (deleted_at IS NULL);


--
-- Name: idx_session_templates_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_session_templates_active ON public.session_templates USING btree (is_active);


--
-- Name: idx_session_templates_org_favorite; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_session_templates_org_favorite ON public.session_templates USING btree (org_id, is_favorite, name);


--
-- Name: idx_sessions_team_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sessions_team_date ON public.training_sessions USING btree (team_id, session_at DESC) INCLUDE (status);


--
-- Name: INDEX idx_sessions_team_date; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON INDEX public.idx_sessions_team_date IS 'Covering index for session listing. Includes frequently accessed columns (status).
        Used in agenda view and session calendar.';


--
-- Name: idx_tags_parent; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tags_parent ON public.exercise_tags USING btree (parent_tag_id) WHERE (parent_tag_id IS NOT NULL);


--
-- Name: idx_team_memberships_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_team_memberships_active ON public.team_memberships USING btree (team_id, status, end_at);


--
-- Name: idx_team_memberships_org_membership_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_team_memberships_org_membership_id ON public.team_memberships USING btree (org_membership_id);


--
-- Name: idx_team_memberships_person_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_team_memberships_person_id ON public.team_memberships USING btree (person_id);


--
-- Name: idx_team_memberships_person_team_active; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX idx_team_memberships_person_team_active ON public.team_memberships USING btree (person_id, team_id) WHERE ((deleted_at IS NULL) AND (end_at IS NULL) AND (status = ANY (ARRAY['pendente'::text, 'ativo'::text])));


--
-- Name: idx_team_memberships_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_team_memberships_status ON public.team_memberships USING btree (status);


--
-- Name: idx_team_memberships_team_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_team_memberships_team_active ON public.team_memberships USING btree (team_id, status) WHERE ((deleted_at IS NULL) AND (end_at IS NULL));


--
-- Name: idx_team_memberships_team_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_team_memberships_team_id ON public.team_memberships USING btree (team_id);


--
-- Name: idx_team_registrations_athlete_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_team_registrations_athlete_active ON public.team_registrations USING btree (athlete_id, deleted_at) WHERE (deleted_at IS NULL);


--
-- Name: idx_team_registrations_team_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_team_registrations_team_active ON public.team_registrations USING btree (team_id, deleted_at) WHERE (deleted_at IS NULL);


--
-- Name: idx_training_cycles_dates; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_training_cycles_dates ON public.training_cycles USING btree (start_date, end_date);


--
-- Name: idx_training_cycles_org; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_training_cycles_org ON public.training_cycles USING btree (organization_id);


--
-- Name: idx_training_cycles_parent; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_training_cycles_parent ON public.training_cycles USING btree (parent_cycle_id);


--
-- Name: idx_training_cycles_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_training_cycles_status ON public.training_cycles USING btree (status);


--
-- Name: idx_training_cycles_team; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_training_cycles_team ON public.training_cycles USING btree (team_id);


--
-- Name: idx_training_cycles_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_training_cycles_type ON public.training_cycles USING btree (type);


--
-- Name: idx_training_microcycles_cycle; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_training_microcycles_cycle ON public.training_microcycles USING btree (cycle_id);


--
-- Name: idx_training_microcycles_dates; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_training_microcycles_dates ON public.training_microcycles USING btree (week_start, week_end);


--
-- Name: idx_training_microcycles_org; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_training_microcycles_org ON public.training_microcycles USING btree (organization_id);


--
-- Name: idx_training_microcycles_team; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_training_microcycles_team ON public.training_microcycles USING btree (team_id);


--
-- Name: idx_training_sessions_deviation_flag; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_training_sessions_deviation_flag ON public.training_sessions USING btree (planning_deviation_flag);


--
-- Name: idx_training_sessions_in_progress_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_training_sessions_in_progress_at ON public.training_sessions USING btree (session_at) WHERE (((status)::text = 'in_progress'::text) AND (deleted_at IS NULL));


--
-- Name: idx_training_sessions_microcycle; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_training_sessions_microcycle ON public.training_sessions USING btree (microcycle_id);


--
-- Name: idx_training_sessions_org; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_training_sessions_org ON public.training_sessions USING btree (organization_id, deleted_at) WHERE (deleted_at IS NULL);


--
-- Name: idx_training_sessions_pending_review_deadline; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_training_sessions_pending_review_deadline ON public.training_sessions USING btree (post_review_deadline_at) WHERE (((status)::text = 'pending_review'::text) AND (deleted_at IS NULL));


--
-- Name: idx_training_sessions_scheduled_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_training_sessions_scheduled_at ON public.training_sessions USING btree (session_at) WHERE (((status)::text = 'scheduled'::text) AND (deleted_at IS NULL));


--
-- Name: idx_training_sessions_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_training_sessions_status ON public.training_sessions USING btree (status);


--
-- Name: idx_training_sessions_team_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_training_sessions_team_date ON public.training_sessions USING btree (team_id, session_at DESC, deleted_at) WHERE (deleted_at IS NULL);


--
-- Name: idx_wellness_athlete_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_wellness_athlete_date ON public.wellness_post USING btree (athlete_id, filled_at DESC) WHERE (athlete_id IS NOT NULL);


--
-- Name: INDEX idx_wellness_athlete_date; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON INDEX public.idx_wellness_athlete_date IS 'Optimizes wellness history queries by athlete. Used in athlete profile and history pages.
        WHERE clause excludes anonymized records (athlete_id IS NULL).';


--
-- Name: idx_wellness_reminders_pending; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_wellness_reminders_pending ON public.wellness_reminders USING btree (training_session_id, athlete_id) WHERE (responded_at IS NULL);


--
-- Name: INDEX idx_wellness_reminders_pending; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON INDEX public.idx_wellness_reminders_pending IS 'Optimizes pending reminder lookups. Used by scheduled jobs (send_pre_wellness_reminders_daily).
        Partial index: only indexes unresponded reminders.';


--
-- Name: idx_wellness_session_athlete; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_wellness_session_athlete ON public.wellness_pre USING btree (training_session_id, athlete_id);


--
-- Name: INDEX idx_wellness_session_athlete; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON INDEX public.idx_wellness_session_athlete IS 'Optimizes wellness status queries per session. Used in wellness dashboard and session modal.';


--
-- Name: ix_athletes_birth_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_athletes_birth_date ON public.athletes USING btree (birth_date);


--
-- Name: ix_athletes_medical_flags; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_athletes_medical_flags ON public.athletes USING btree (state) WHERE ((deleted_at IS NULL) AND ((injured = true) OR (medical_restriction = true) OR (load_restricted = true)));


--
-- Name: ix_athletes_organization_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_athletes_organization_id ON public.athletes USING btree (organization_id) WHERE (deleted_at IS NULL);


--
-- Name: ix_athletes_person_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_athletes_person_id ON public.athletes USING btree (person_id);


--
-- Name: ix_athletes_person_id_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_athletes_person_id_active ON public.athletes USING btree (person_id) WHERE (deleted_at IS NULL);


--
-- Name: ix_athletes_state; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_athletes_state ON public.athletes USING btree (state);


--
-- Name: ix_athletes_state_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_athletes_state_active ON public.athletes USING btree (state) WHERE (deleted_at IS NULL);


--
-- Name: ix_attendance_athlete_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_attendance_athlete_id ON public.attendance USING btree (athlete_id);


--
-- Name: ix_attendance_athlete_session_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_attendance_athlete_session_active ON public.attendance USING btree (athlete_id, training_session_id) WHERE (deleted_at IS NULL);


--
-- Name: ix_attendance_training_session_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_attendance_training_session_id ON public.attendance USING btree (training_session_id);


--
-- Name: ix_audit_logs_actor_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_audit_logs_actor_id ON public.audit_logs USING btree (actor_id);


--
-- Name: ix_audit_logs_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_audit_logs_created_at ON public.audit_logs USING btree (created_at);


--
-- Name: ix_audit_logs_entity; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_audit_logs_entity ON public.audit_logs USING btree (entity);


--
-- Name: ix_audit_logs_entity_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_audit_logs_entity_id ON public.audit_logs USING btree (entity_id);


--
-- Name: ix_competition_matches_competition_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_competition_matches_competition_id ON public.competition_matches USING btree (competition_id);


--
-- Name: ix_competition_matches_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_competition_matches_date ON public.competition_matches USING btree (match_date);


--
-- Name: ix_competition_matches_linked_match_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_competition_matches_linked_match_id ON public.competition_matches USING btree (linked_match_id);


--
-- Name: ix_competition_matches_our_match; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_competition_matches_our_match ON public.competition_matches USING btree (is_our_match);


--
-- Name: ix_competition_matches_phase_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_competition_matches_phase_id ON public.competition_matches USING btree (phase_id);


--
-- Name: ix_competition_opponent_teams_competition_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_competition_opponent_teams_competition_id ON public.competition_opponent_teams USING btree (competition_id);


--
-- Name: ix_competition_opponent_teams_group; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_competition_opponent_teams_group ON public.competition_opponent_teams USING btree (competition_id, group_name);


--
-- Name: ix_competition_opponent_teams_linked_team_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_competition_opponent_teams_linked_team_id ON public.competition_opponent_teams USING btree (linked_team_id);


--
-- Name: ix_competition_phases_competition_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_competition_phases_competition_id ON public.competition_phases USING btree (competition_id);


--
-- Name: ix_competition_phases_order; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_competition_phases_order ON public.competition_phases USING btree (competition_id, order_index);


--
-- Name: ix_competition_seasons_competition_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_competition_seasons_competition_id ON public.competition_seasons USING btree (competition_id);


--
-- Name: ix_competition_seasons_season_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_competition_seasons_season_id ON public.competition_seasons USING btree (season_id);


--
-- Name: ix_competition_standings_competition_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_competition_standings_competition_id ON public.competition_standings USING btree (competition_id);


--
-- Name: ix_competition_standings_position; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_competition_standings_position ON public.competition_standings USING btree (competition_id, phase_id, "position");


--
-- Name: ix_competitions_created_by; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_competitions_created_by ON public.competitions USING btree (created_by);


--
-- Name: ix_competitions_organization_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_competitions_organization_id ON public.competitions USING btree (organization_id);


--
-- Name: ix_competitions_season; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_competitions_season ON public.competitions USING btree (season);


--
-- Name: ix_competitions_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_competitions_status ON public.competitions USING btree (status);


--
-- Name: ix_competitions_team_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_competitions_team_id ON public.competitions USING btree (team_id);


--
-- Name: ix_email_queue_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_email_queue_created_at ON public.email_queue USING btree (created_at);


--
-- Name: ix_email_queue_next_retry; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_email_queue_next_retry ON public.email_queue USING btree (next_retry_at) WHERE ((status)::text = 'pending'::text);


--
-- Name: ix_email_queue_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_email_queue_status ON public.email_queue USING btree (status);


--
-- Name: ix_email_queue_to_email; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_email_queue_to_email ON public.email_queue USING btree (to_email);


--
-- Name: ix_event_subtypes_event_type_code; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_event_subtypes_event_type_code ON public.event_subtypes USING btree (event_type_code);


--
-- Name: ix_idempotency_keys_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_idempotency_keys_created_at ON public.idempotency_keys USING btree (created_at);


--
-- Name: INDEX ix_idempotency_keys_created_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON INDEX public.ix_idempotency_keys_created_at IS 'Índice para otimizar limpeza de registros antigos via cron job';


--
-- Name: ix_idempotency_keys_key; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_idempotency_keys_key ON public.idempotency_keys USING btree (key);


--
-- Name: ix_idempotency_keys_key_endpoint; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_idempotency_keys_key_endpoint ON public.idempotency_keys USING btree (key, endpoint);


--
-- Name: ix_match_events_athlete_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_match_events_athlete_id ON public.match_events USING btree (athlete_id);


--
-- Name: ix_match_events_event_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_match_events_event_type ON public.match_events USING btree (event_type);


--
-- Name: ix_match_events_match_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_match_events_match_id ON public.match_events USING btree (match_id);


--
-- Name: ix_match_events_phase_of_play; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_match_events_phase_of_play ON public.match_events USING btree (phase_of_play);


--
-- Name: ix_match_events_team_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_match_events_team_id ON public.match_events USING btree (team_id);


--
-- Name: ix_match_periods_match_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_match_periods_match_id ON public.match_periods USING btree (match_id);


--
-- Name: ix_match_possessions_match_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_match_possessions_match_id ON public.match_possessions USING btree (match_id);


--
-- Name: ix_match_possessions_team_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_match_possessions_team_id ON public.match_possessions USING btree (team_id);


--
-- Name: ix_match_roster_athlete_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_match_roster_athlete_id ON public.match_roster USING btree (athlete_id);


--
-- Name: ix_match_roster_athlete_match; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_match_roster_athlete_match ON public.match_roster USING btree (athlete_id, match_id);


--
-- Name: ix_match_roster_match_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_match_roster_match_id ON public.match_roster USING btree (match_id);


--
-- Name: ix_match_teams_match_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_match_teams_match_id ON public.match_teams USING btree (match_id);


--
-- Name: ix_match_teams_team_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_match_teams_team_id ON public.match_teams USING btree (team_id);


--
-- Name: ix_matches_away_team_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_matches_away_team_id ON public.matches USING btree (away_team_id);


--
-- Name: ix_matches_home_team_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_matches_home_team_id ON public.matches USING btree (home_team_id);


--
-- Name: ix_matches_match_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_matches_match_date ON public.matches USING btree (match_date);


--
-- Name: ix_matches_season_date_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_matches_season_date_active ON public.matches USING btree (season_id, match_date) WHERE (deleted_at IS NULL);


--
-- Name: ix_matches_season_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_matches_season_id ON public.matches USING btree (season_id);


--
-- Name: ix_matches_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_matches_status ON public.matches USING btree (status);


--
-- Name: ix_medical_cases_athlete_status_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_medical_cases_athlete_status_active ON public.medical_cases USING btree (athlete_id, status) WHERE ((deleted_at IS NULL) AND ((status)::text = ANY ((ARRAY['ativo'::character varying, 'em_acompanhamento'::character varying])::text[])));


--
-- Name: ix_org_memberships_org_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_org_memberships_org_active ON public.org_memberships USING btree (organization_id) WHERE (deleted_at IS NULL);


--
-- Name: ix_org_memberships_organization_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_org_memberships_organization_id ON public.org_memberships USING btree (organization_id);


--
-- Name: ix_org_memberships_person_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_org_memberships_person_active ON public.org_memberships USING btree (person_id) WHERE (deleted_at IS NULL);


--
-- Name: ix_org_memberships_person_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_org_memberships_person_id ON public.org_memberships USING btree (person_id);


--
-- Name: ix_org_memberships_person_org_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_org_memberships_person_org_active ON public.org_memberships USING btree (person_id, organization_id) WHERE ((deleted_at IS NULL) AND (end_at IS NULL));


--
-- Name: ix_org_memberships_role_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_org_memberships_role_id ON public.org_memberships USING btree (role_id);


--
-- Name: ix_organizations_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_organizations_name ON public.organizations USING btree (name);


--
-- Name: ix_organizations_name_trgm; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_organizations_name_trgm ON public.organizations USING gin (name public.gin_trgm_ops) WHERE (deleted_at IS NULL);


--
-- Name: ix_password_resets_expires_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_password_resets_expires_at ON public.password_resets USING btree (expires_at);


--
-- Name: ix_password_resets_token; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_password_resets_token ON public.password_resets USING btree (token);


--
-- Name: ix_password_resets_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_password_resets_user_id ON public.password_resets USING btree (user_id);


--
-- Name: ix_person_addresses_city_state; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_person_addresses_city_state ON public.person_addresses USING btree (city, state);


--
-- Name: ix_person_addresses_created_by_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_person_addresses_created_by_user_id ON public.person_addresses USING btree (created_by_user_id);


--
-- Name: ix_person_addresses_deleted_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_person_addresses_deleted_at ON public.person_addresses USING btree (deleted_at);


--
-- Name: ix_person_addresses_person_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_person_addresses_person_id ON public.person_addresses USING btree (person_id);


--
-- Name: ix_person_contacts_created_by_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_person_contacts_created_by_user_id ON public.person_contacts USING btree (created_by_user_id);


--
-- Name: ix_person_contacts_deleted_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_person_contacts_deleted_at ON public.person_contacts USING btree (deleted_at);


--
-- Name: ix_person_contacts_email_lower; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_person_contacts_email_lower ON public.person_contacts USING btree (lower((contact_value)::text)) WHERE (((contact_type)::text = 'email'::text) AND (deleted_at IS NULL));


--
-- Name: ix_person_contacts_person_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_person_contacts_person_id ON public.person_contacts USING btree (person_id);


--
-- Name: ix_person_contacts_type_value; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_person_contacts_type_value ON public.person_contacts USING btree (contact_type, contact_value);


--
-- Name: ix_person_contacts_type_value_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_person_contacts_type_value_active ON public.person_contacts USING btree (contact_type, contact_value) WHERE (deleted_at IS NULL);


--
-- Name: ix_person_contacts_value; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_person_contacts_value ON public.person_contacts USING btree (contact_value) WHERE (deleted_at IS NULL);


--
-- Name: ix_person_contacts_value_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_person_contacts_value_active ON public.person_contacts USING btree (contact_value) WHERE (deleted_at IS NULL);


--
-- Name: ix_person_documents_cpf_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_person_documents_cpf_active ON public.person_documents USING btree (document_number) WHERE (((document_type)::text = 'cpf'::text) AND (deleted_at IS NULL));


--
-- Name: ix_person_documents_created_by_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_person_documents_created_by_user_id ON public.person_documents USING btree (created_by_user_id);


--
-- Name: ix_person_documents_deleted_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_person_documents_deleted_at ON public.person_documents USING btree (deleted_at);


--
-- Name: ix_person_documents_number; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_person_documents_number ON public.person_documents USING btree (document_number);


--
-- Name: ix_person_documents_person_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_person_documents_person_id ON public.person_documents USING btree (person_id);


--
-- Name: ix_person_documents_rg_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_person_documents_rg_active ON public.person_documents USING btree (document_number) WHERE (((document_type)::text = 'rg'::text) AND (deleted_at IS NULL));


--
-- Name: ix_person_documents_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_person_documents_type ON public.person_documents USING btree (document_type);


--
-- Name: ix_person_documents_type_number; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_person_documents_type_number ON public.person_documents USING btree (document_type, document_number) WHERE (deleted_at IS NULL);


--
-- Name: ix_person_media_created_by_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_person_media_created_by_user_id ON public.person_media USING btree (created_by_user_id);


--
-- Name: ix_person_media_deleted_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_person_media_deleted_at ON public.person_media USING btree (deleted_at);


--
-- Name: ix_person_media_person_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_person_media_person_id ON public.person_media USING btree (person_id);


--
-- Name: ix_person_media_person_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_person_media_person_type ON public.person_media USING btree (person_id, media_type) WHERE (deleted_at IS NULL);


--
-- Name: ix_person_media_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_person_media_type ON public.person_media USING btree (media_type);


--
-- Name: ix_persons_birth_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_persons_birth_date ON public.persons USING btree (birth_date);


--
-- Name: ix_persons_deleted_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_persons_deleted_at ON public.persons USING btree (deleted_at);


--
-- Name: ix_persons_first_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_persons_first_name ON public.persons USING btree (first_name);


--
-- Name: ix_persons_first_name_trgm; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_persons_first_name_trgm ON public.persons USING gin (first_name public.gin_trgm_ops) WHERE (deleted_at IS NULL);


--
-- Name: ix_persons_full_name_trgm; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_persons_full_name_trgm ON public.persons USING gin (full_name public.gin_trgm_ops) WHERE (deleted_at IS NULL);


--
-- Name: INDEX ix_persons_full_name_trgm; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON INDEX public.ix_persons_full_name_trgm IS 'Índice trigram para busca fuzzy de pessoas (autocomplete). FICHA.MD 1.6';


--
-- Name: ix_persons_last_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_persons_last_name ON public.persons USING btree (last_name);


--
-- Name: ix_persons_last_name_trgm; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_persons_last_name_trgm ON public.persons USING gin (last_name public.gin_trgm_ops) WHERE (deleted_at IS NULL);


--
-- Name: ix_refresh_tokens_token_hash; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_refresh_tokens_token_hash ON public.refresh_tokens USING btree (token_hash);


--
-- Name: ix_seasons_team_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_seasons_team_id ON public.seasons USING btree (team_id);


--
-- Name: ix_seasons_year; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_seasons_year ON public.seasons USING btree (year);


--
-- Name: ix_team_registrations_athlete_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_team_registrations_athlete_active ON public.team_registrations USING btree (athlete_id) WHERE ((end_at IS NULL) AND (deleted_at IS NULL));


--
-- Name: ix_team_registrations_athlete_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_team_registrations_athlete_id ON public.team_registrations USING btree (athlete_id);


--
-- Name: ix_team_registrations_period; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_team_registrations_period ON public.team_registrations USING btree (start_at, end_at) WHERE (deleted_at IS NULL);


--
-- Name: ix_team_registrations_team_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_team_registrations_team_active ON public.team_registrations USING btree (team_id) WHERE ((end_at IS NULL) AND (deleted_at IS NULL));


--
-- Name: ix_team_registrations_team_athlete_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_team_registrations_team_athlete_active ON public.team_registrations USING btree (team_id, athlete_id) WHERE ((end_at IS NULL) AND (deleted_at IS NULL));


--
-- Name: ix_team_registrations_team_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_team_registrations_team_id ON public.team_registrations USING btree (team_id);


--
-- Name: ix_teams_category_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_teams_category_id ON public.teams USING btree (category_id);


--
-- Name: ix_teams_coach_membership_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_teams_coach_membership_id ON public.teams USING btree (coach_membership_id);


--
-- Name: ix_teams_created_by_membership_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_teams_created_by_membership_id ON public.teams USING btree (created_by_membership_id);


--
-- Name: ix_teams_name_trgm; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_teams_name_trgm ON public.teams USING gin (name public.gin_trgm_ops) WHERE (deleted_at IS NULL);


--
-- Name: ix_teams_organization_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_teams_organization_active ON public.teams USING btree (organization_id) WHERE (deleted_at IS NULL);


--
-- Name: ix_teams_organization_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_teams_organization_id ON public.teams USING btree (organization_id);


--
-- Name: ix_teams_season_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_teams_season_id ON public.teams USING btree (season_id);


--
-- Name: ix_training_sessions_organization_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_training_sessions_organization_id ON public.training_sessions USING btree (organization_id);


--
-- Name: ix_training_sessions_season_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_training_sessions_season_id ON public.training_sessions USING btree (season_id);


--
-- Name: ix_training_sessions_session_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_training_sessions_session_at ON public.training_sessions USING btree (session_at);


--
-- Name: ix_training_sessions_team_date_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_training_sessions_team_date_active ON public.training_sessions USING btree (team_id, session_at) WHERE (deleted_at IS NULL);


--
-- Name: ix_training_sessions_team_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_training_sessions_team_id ON public.training_sessions USING btree (team_id);


--
-- Name: ix_training_sessions_team_season_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_training_sessions_team_season_date ON public.training_sessions USING btree (team_id, season_id, session_at) WHERE (deleted_at IS NULL);


--
-- Name: ix_users_person_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_users_person_id ON public.users USING btree (person_id);


--
-- Name: ix_wellness_post_athlete_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_wellness_post_athlete_id ON public.wellness_post USING btree (athlete_id);


--
-- Name: ix_wellness_post_athlete_session_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_wellness_post_athlete_session_active ON public.wellness_post USING btree (athlete_id, training_session_id, created_at) WHERE (deleted_at IS NULL);


--
-- Name: ix_wellness_post_training_session_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_wellness_post_training_session_id ON public.wellness_post USING btree (training_session_id);


--
-- Name: ix_wellness_pre_athlete_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_wellness_pre_athlete_id ON public.wellness_pre USING btree (athlete_id);


--
-- Name: ix_wellness_pre_training_session_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_wellness_pre_training_session_id ON public.wellness_pre USING btree (training_session_id);


--
-- Name: uq_person_addresses_primary; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_person_addresses_primary ON public.person_addresses USING btree (person_id) WHERE ((is_primary = true) AND (deleted_at IS NULL));


--
-- Name: uq_person_contacts_primary_per_type; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_person_contacts_primary_per_type ON public.person_contacts USING btree (person_id, contact_type) WHERE ((is_primary = true) AND (deleted_at IS NULL));


--
-- Name: uq_person_documents_per_type; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_person_documents_per_type ON public.person_documents USING btree (person_id, document_type, document_number) WHERE (deleted_at IS NULL);


--
-- Name: uq_person_media_primary_per_type; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_person_media_primary_per_type ON public.person_media USING btree (person_id, media_type) WHERE ((is_primary = true) AND (deleted_at IS NULL));


--
-- Name: ux_org_memberships_active; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ux_org_memberships_active ON public.org_memberships USING btree (person_id, organization_id, role_id) WHERE ((end_at IS NULL) AND (deleted_at IS NULL));


--
-- Name: ux_team_registrations_active; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ux_team_registrations_active ON public.team_registrations USING btree (athlete_id, team_id) WHERE ((end_at IS NULL) AND (deleted_at IS NULL));


--
-- Name: ux_users_email; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ux_users_email ON public.users USING btree (lower((email)::text));


--
-- Name: ux_users_superadmin; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ux_users_superadmin ON public.users USING btree (is_superadmin) WHERE ((is_superadmin = true) AND (deleted_at IS NULL));


--
-- Name: ux_wellness_post_session_athlete; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ux_wellness_post_session_athlete ON public.wellness_post USING btree (training_session_id, athlete_id) WHERE (deleted_at IS NULL);


--
-- Name: ux_wellness_pre_session_athlete; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ux_wellness_pre_session_athlete ON public.wellness_pre USING btree (training_session_id, athlete_id) WHERE (deleted_at IS NULL);


--
-- Name: wellness_post tr_calculate_internal_load; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER tr_calculate_internal_load BEFORE INSERT OR UPDATE ON public.wellness_post FOR EACH ROW EXECUTE FUNCTION public.fn_calculate_internal_load();


--
-- Name: training_sessions tr_derive_phase_focus; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER tr_derive_phase_focus BEFORE INSERT OR UPDATE OF focus_attack_positional_pct, focus_attack_technical_pct, focus_defense_positional_pct, focus_defense_technical_pct, focus_transition_offense_pct, focus_transition_defense_pct, focus_physical_pct ON public.training_sessions FOR EACH ROW EXECUTE FUNCTION public.fn_derive_phase_focus();


--
-- Name: training_sessions tr_invalidate_analytics_cache; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER tr_invalidate_analytics_cache AFTER INSERT OR DELETE OR UPDATE ON public.training_sessions FOR EACH ROW EXECUTE FUNCTION public.fn_invalidate_analytics_cache();


--
-- Name: training_session_exercises tr_session_exercises_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER tr_session_exercises_updated_at BEFORE UPDATE ON public.training_session_exercises FOR EACH ROW EXECUTE FUNCTION public.tr_update_session_exercises_updated_at();


--
-- Name: wellness_post tr_update_wellness_post_response; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER tr_update_wellness_post_response AFTER INSERT ON public.wellness_post FOR EACH ROW EXECUTE FUNCTION public.fn_update_wellness_response_timestamp();


--
-- Name: wellness_pre tr_update_wellness_pre_response; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER tr_update_wellness_pre_response AFTER INSERT ON public.wellness_pre FOR EACH ROW EXECUTE FUNCTION public.fn_update_wellness_response_timestamp();


--
-- Name: organizations trg_after_insert_organization; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_after_insert_organization AFTER INSERT ON public.organizations FOR EACH ROW EXECUTE FUNCTION public.trg_insert_default_session_templates();


--
-- Name: athletes trg_athletes_age_at_registration; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_athletes_age_at_registration BEFORE INSERT OR UPDATE OF birth_date, registered_at ON public.athletes FOR EACH ROW EXECUTE FUNCTION public.trg_set_athlete_age_at_registration();


--
-- Name: athletes trg_athletes_auto_end_registrations; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_athletes_auto_end_registrations AFTER UPDATE OF state ON public.athletes FOR EACH ROW EXECUTE FUNCTION public.trg_auto_end_team_registrations_on_dispensada();


--
-- Name: athletes trg_athletes_block_delete; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_athletes_block_delete BEFORE DELETE ON public.athletes FOR EACH ROW EXECUTE FUNCTION public.trg_block_physical_delete();


--
-- Name: athletes trg_athletes_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_athletes_updated_at BEFORE UPDATE ON public.athletes FOR EACH ROW EXECUTE FUNCTION public.trg_set_updated_at();


--
-- Name: attendance trg_attendance_block_delete; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_attendance_block_delete BEFORE DELETE ON public.attendance FOR EACH ROW EXECUTE FUNCTION public.trg_block_physical_delete();


--
-- Name: attendance trg_attendance_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_attendance_updated_at BEFORE UPDATE ON public.attendance FOR EACH ROW EXECUTE FUNCTION public.trg_set_updated_at();


--
-- Name: audit_logs trg_audit_logs_block_delete; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_audit_logs_block_delete BEFORE DELETE ON public.audit_logs FOR EACH ROW EXECUTE FUNCTION public.trg_block_audit_logs_modification();


--
-- Name: audit_logs trg_audit_logs_block_update; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_audit_logs_block_update BEFORE UPDATE ON public.audit_logs FOR EACH ROW EXECUTE FUNCTION public.trg_block_audit_logs_modification();


--
-- Name: email_queue trg_email_queue_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_email_queue_updated_at BEFORE UPDATE ON public.email_queue FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: matches trg_matches_block_delete; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_matches_block_delete BEFORE DELETE ON public.matches FOR EACH ROW EXECUTE FUNCTION public.trg_block_physical_delete();


--
-- Name: matches trg_matches_block_finished_update; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_matches_block_finished_update BEFORE UPDATE ON public.matches FOR EACH ROW EXECUTE FUNCTION public.trg_block_finished_match_update();


--
-- Name: matches trg_matches_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_matches_updated_at BEFORE UPDATE ON public.matches FOR EACH ROW EXECUTE FUNCTION public.trg_set_updated_at();


--
-- Name: medical_cases trg_medical_cases_block_delete; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_medical_cases_block_delete BEFORE DELETE ON public.medical_cases FOR EACH ROW EXECUTE FUNCTION public.trg_block_physical_delete();


--
-- Name: medical_cases trg_medical_cases_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_medical_cases_updated_at BEFORE UPDATE ON public.medical_cases FOR EACH ROW EXECUTE FUNCTION public.trg_set_updated_at();


--
-- Name: org_memberships trg_org_memberships_block_delete; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_org_memberships_block_delete BEFORE DELETE ON public.org_memberships FOR EACH ROW EXECUTE FUNCTION public.trg_block_physical_delete();


--
-- Name: org_memberships trg_org_memberships_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_org_memberships_updated_at BEFORE UPDATE ON public.org_memberships FOR EACH ROW EXECUTE FUNCTION public.trg_set_updated_at();


--
-- Name: organizations trg_organizations_block_delete; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_organizations_block_delete BEFORE DELETE ON public.organizations FOR EACH ROW EXECUTE FUNCTION public.trg_block_physical_delete();


--
-- Name: organizations trg_organizations_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_organizations_updated_at BEFORE UPDATE ON public.organizations FOR EACH ROW EXECUTE FUNCTION public.trg_set_updated_at();


--
-- Name: person_addresses trg_person_addresses_block_delete; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_person_addresses_block_delete BEFORE DELETE ON public.person_addresses FOR EACH ROW EXECUTE FUNCTION public.trg_block_physical_delete();


--
-- Name: person_addresses trg_person_addresses_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_person_addresses_updated_at BEFORE UPDATE ON public.person_addresses FOR EACH ROW EXECUTE FUNCTION public.trg_set_updated_at();


--
-- Name: person_contacts trg_person_contacts_block_delete; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_person_contacts_block_delete BEFORE DELETE ON public.person_contacts FOR EACH ROW EXECUTE FUNCTION public.trg_block_physical_delete();


--
-- Name: person_contacts trg_person_contacts_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_person_contacts_updated_at BEFORE UPDATE ON public.person_contacts FOR EACH ROW EXECUTE FUNCTION public.trg_set_updated_at();


--
-- Name: person_documents trg_person_documents_block_delete; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_person_documents_block_delete BEFORE DELETE ON public.person_documents FOR EACH ROW EXECUTE FUNCTION public.trg_block_physical_delete();


--
-- Name: person_documents trg_person_documents_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_person_documents_updated_at BEFORE UPDATE ON public.person_documents FOR EACH ROW EXECUTE FUNCTION public.trg_set_updated_at();


--
-- Name: person_media trg_person_media_block_delete; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_person_media_block_delete BEFORE DELETE ON public.person_media FOR EACH ROW EXECUTE FUNCTION public.trg_block_physical_delete();


--
-- Name: person_media trg_person_media_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_person_media_updated_at BEFORE UPDATE ON public.person_media FOR EACH ROW EXECUTE FUNCTION public.trg_set_updated_at();


--
-- Name: persons trg_persons_block_delete; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_persons_block_delete BEFORE DELETE ON public.persons FOR EACH ROW EXECUTE FUNCTION public.trg_block_physical_delete();


--
-- Name: persons trg_persons_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_persons_updated_at BEFORE UPDATE ON public.persons FOR EACH ROW EXECUTE FUNCTION public.trg_set_updated_at();


--
-- Name: seasons trg_seasons_block_delete; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_seasons_block_delete BEFORE DELETE ON public.seasons FOR EACH ROW EXECUTE FUNCTION public.trg_block_physical_delete();


--
-- Name: seasons trg_seasons_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_seasons_updated_at BEFORE UPDATE ON public.seasons FOR EACH ROW EXECUTE FUNCTION public.trg_set_updated_at();


--
-- Name: team_registrations trg_team_registrations_block_delete; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_team_registrations_block_delete BEFORE DELETE ON public.team_registrations FOR EACH ROW EXECUTE FUNCTION public.trg_block_physical_delete();


--
-- Name: team_registrations trg_team_registrations_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_team_registrations_updated_at BEFORE UPDATE ON public.team_registrations FOR EACH ROW EXECUTE FUNCTION public.trg_set_updated_at();


--
-- Name: teams trg_teams_block_delete; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_teams_block_delete BEFORE DELETE ON public.teams FOR EACH ROW EXECUTE FUNCTION public.trg_block_physical_delete();


--
-- Name: teams trg_teams_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_teams_updated_at BEFORE UPDATE ON public.teams FOR EACH ROW EXECUTE FUNCTION public.trg_set_updated_at();


--
-- Name: training_sessions trg_training_sessions_block_delete; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_training_sessions_block_delete BEFORE DELETE ON public.training_sessions FOR EACH ROW EXECUTE FUNCTION public.trg_block_physical_delete();


--
-- Name: training_sessions trg_training_sessions_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_training_sessions_updated_at BEFORE UPDATE ON public.training_sessions FOR EACH ROW EXECUTE FUNCTION public.trg_set_updated_at();


--
-- Name: users trg_users_block_delete; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_users_block_delete BEFORE DELETE ON public.users FOR EACH ROW EXECUTE FUNCTION public.trg_block_physical_delete();


--
-- Name: users trg_users_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_users_updated_at BEFORE UPDATE ON public.users FOR EACH ROW EXECUTE FUNCTION public.trg_set_updated_at();


--
-- Name: wellness_post trg_wellness_post_block_delete; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_wellness_post_block_delete BEFORE DELETE ON public.wellness_post FOR EACH ROW EXECUTE FUNCTION public.trg_block_physical_delete();


--
-- Name: wellness_post trg_wellness_post_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_wellness_post_updated_at BEFORE UPDATE ON public.wellness_post FOR EACH ROW EXECUTE FUNCTION public.trg_set_updated_at();


--
-- Name: wellness_pre trg_wellness_pre_block_delete; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_wellness_pre_block_delete BEFORE DELETE ON public.wellness_pre FOR EACH ROW EXECUTE FUNCTION public.trg_block_physical_delete();


--
-- Name: wellness_pre trg_wellness_pre_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_wellness_pre_updated_at BEFORE UPDATE ON public.wellness_pre FOR EACH ROW EXECUTE FUNCTION public.trg_set_updated_at();


--
-- Name: competition_matches trigger_competition_matches_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trigger_competition_matches_updated_at BEFORE UPDATE ON public.competition_matches FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: competition_opponent_teams trigger_competition_opponent_teams_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trigger_competition_opponent_teams_updated_at BEFORE UPDATE ON public.competition_opponent_teams FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: competition_phases trigger_competition_phases_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trigger_competition_phases_updated_at BEFORE UPDATE ON public.competition_phases FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: competition_seasons trigger_competition_seasons_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trigger_competition_seasons_updated_at BEFORE UPDATE ON public.competition_seasons FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: competition_standings trigger_competition_standings_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trigger_competition_standings_updated_at BEFORE UPDATE ON public.competition_standings FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: competitions trigger_competitions_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trigger_competitions_updated_at BEFORE UPDATE ON public.competitions FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: athlete_badges athlete_badges_athlete_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.athlete_badges
    ADD CONSTRAINT athlete_badges_athlete_id_fkey FOREIGN KEY (athlete_id) REFERENCES public.athletes(id) ON DELETE CASCADE;


--
-- Name: attendance attendance_correction_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.attendance
    ADD CONSTRAINT attendance_correction_by_user_id_fkey FOREIGN KEY (correction_by_user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: data_access_logs data_access_logs_athlete_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.data_access_logs
    ADD CONSTRAINT data_access_logs_athlete_id_fkey FOREIGN KEY (athlete_id) REFERENCES public.athletes(id) ON DELETE SET NULL;


--
-- Name: data_access_logs data_access_logs_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.data_access_logs
    ADD CONSTRAINT data_access_logs_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: exercise_favorites exercise_favorites_exercise_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.exercise_favorites
    ADD CONSTRAINT exercise_favorites_exercise_id_fkey FOREIGN KEY (exercise_id) REFERENCES public.exercises(id) ON DELETE CASCADE;


--
-- Name: exercise_favorites exercise_favorites_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.exercise_favorites
    ADD CONSTRAINT exercise_favorites_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: exercise_tags exercise_tags_approved_by_admin_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.exercise_tags
    ADD CONSTRAINT exercise_tags_approved_by_admin_id_fkey FOREIGN KEY (approved_by_admin_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: exercise_tags exercise_tags_parent_tag_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.exercise_tags
    ADD CONSTRAINT exercise_tags_parent_tag_id_fkey FOREIGN KEY (parent_tag_id) REFERENCES public.exercise_tags(id) ON DELETE CASCADE;


--
-- Name: exercise_tags exercise_tags_suggested_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.exercise_tags
    ADD CONSTRAINT exercise_tags_suggested_by_user_id_fkey FOREIGN KEY (suggested_by_user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: exercises exercises_created_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.exercises
    ADD CONSTRAINT exercises_created_by_user_id_fkey FOREIGN KEY (created_by_user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: exercises exercises_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.exercises
    ADD CONSTRAINT exercises_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id) ON DELETE CASCADE;


--
-- Name: export_jobs export_jobs_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.export_jobs
    ADD CONSTRAINT export_jobs_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: export_rate_limits export_rate_limits_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.export_rate_limits
    ADD CONSTRAINT export_rate_limits_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: athletes fk_athletes_main_defensive_position_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.athletes
    ADD CONSTRAINT fk_athletes_main_defensive_position_id FOREIGN KEY (main_defensive_position_id) REFERENCES public.defensive_positions(id) ON DELETE SET NULL;


--
-- Name: athletes fk_athletes_main_offensive_position_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.athletes
    ADD CONSTRAINT fk_athletes_main_offensive_position_id FOREIGN KEY (main_offensive_position_id) REFERENCES public.offensive_positions(id) ON DELETE SET NULL;


--
-- Name: athletes fk_athletes_organization_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.athletes
    ADD CONSTRAINT fk_athletes_organization_id FOREIGN KEY (organization_id) REFERENCES public.organizations(id) ON DELETE RESTRICT;


--
-- Name: athletes fk_athletes_person_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.athletes
    ADD CONSTRAINT fk_athletes_person_id FOREIGN KEY (person_id) REFERENCES public.persons(id) ON DELETE RESTRICT;


--
-- Name: athletes fk_athletes_schooling_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.athletes
    ADD CONSTRAINT fk_athletes_schooling_id FOREIGN KEY (schooling_id) REFERENCES public.schooling_levels(id) ON DELETE SET NULL;


--
-- Name: athletes fk_athletes_secondary_defensive_position_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.athletes
    ADD CONSTRAINT fk_athletes_secondary_defensive_position_id FOREIGN KEY (secondary_defensive_position_id) REFERENCES public.defensive_positions(id) ON DELETE SET NULL;


--
-- Name: athletes fk_athletes_secondary_offensive_position_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.athletes
    ADD CONSTRAINT fk_athletes_secondary_offensive_position_id FOREIGN KEY (secondary_offensive_position_id) REFERENCES public.offensive_positions(id) ON DELETE SET NULL;


--
-- Name: attendance fk_attendance_athlete_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.attendance
    ADD CONSTRAINT fk_attendance_athlete_id FOREIGN KEY (athlete_id) REFERENCES public.athletes(id) ON DELETE RESTRICT;


--
-- Name: attendance fk_attendance_created_by_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.attendance
    ADD CONSTRAINT fk_attendance_created_by_user_id FOREIGN KEY (created_by_user_id) REFERENCES public.users(id) ON DELETE RESTRICT;


--
-- Name: attendance fk_attendance_team_registration_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.attendance
    ADD CONSTRAINT fk_attendance_team_registration_id FOREIGN KEY (team_registration_id) REFERENCES public.team_registrations(id) ON DELETE RESTRICT;


--
-- Name: attendance fk_attendance_training_session_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.attendance
    ADD CONSTRAINT fk_attendance_training_session_id FOREIGN KEY (training_session_id) REFERENCES public.training_sessions(id) ON DELETE RESTRICT;


--
-- Name: audit_logs fk_audit_logs_actor_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT fk_audit_logs_actor_id FOREIGN KEY (actor_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: competition_matches fk_competition_matches_away_team_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.competition_matches
    ADD CONSTRAINT fk_competition_matches_away_team_id FOREIGN KEY (away_team_id) REFERENCES public.competition_opponent_teams(id) ON DELETE SET NULL;


--
-- Name: competition_matches fk_competition_matches_competition_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.competition_matches
    ADD CONSTRAINT fk_competition_matches_competition_id FOREIGN KEY (competition_id) REFERENCES public.competitions(id) ON DELETE CASCADE;


--
-- Name: competition_matches fk_competition_matches_home_team_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.competition_matches
    ADD CONSTRAINT fk_competition_matches_home_team_id FOREIGN KEY (home_team_id) REFERENCES public.competition_opponent_teams(id) ON DELETE SET NULL;


--
-- Name: competition_matches fk_competition_matches_linked_match_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.competition_matches
    ADD CONSTRAINT fk_competition_matches_linked_match_id FOREIGN KEY (linked_match_id) REFERENCES public.matches(id) ON DELETE SET NULL;


--
-- Name: competition_matches fk_competition_matches_phase_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.competition_matches
    ADD CONSTRAINT fk_competition_matches_phase_id FOREIGN KEY (phase_id) REFERENCES public.competition_phases(id) ON DELETE SET NULL;


--
-- Name: competition_opponent_teams fk_competition_opponent_teams_competition_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.competition_opponent_teams
    ADD CONSTRAINT fk_competition_opponent_teams_competition_id FOREIGN KEY (competition_id) REFERENCES public.competitions(id) ON DELETE CASCADE;


--
-- Name: competition_opponent_teams fk_competition_opponent_teams_linked_team_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.competition_opponent_teams
    ADD CONSTRAINT fk_competition_opponent_teams_linked_team_id FOREIGN KEY (linked_team_id) REFERENCES public.teams(id) ON DELETE SET NULL;


--
-- Name: competition_phases fk_competition_phases_competition_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.competition_phases
    ADD CONSTRAINT fk_competition_phases_competition_id FOREIGN KEY (competition_id) REFERENCES public.competitions(id) ON DELETE CASCADE;


--
-- Name: competition_seasons fk_competition_seasons_competition_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.competition_seasons
    ADD CONSTRAINT fk_competition_seasons_competition_id FOREIGN KEY (competition_id) REFERENCES public.competitions(id) ON DELETE CASCADE;


--
-- Name: competition_seasons fk_competition_seasons_season_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.competition_seasons
    ADD CONSTRAINT fk_competition_seasons_season_id FOREIGN KEY (season_id) REFERENCES public.seasons(id) ON DELETE CASCADE;


--
-- Name: competition_standings fk_competition_standings_competition_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.competition_standings
    ADD CONSTRAINT fk_competition_standings_competition_id FOREIGN KEY (competition_id) REFERENCES public.competitions(id) ON DELETE CASCADE;


--
-- Name: competition_standings fk_competition_standings_opponent_team_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.competition_standings
    ADD CONSTRAINT fk_competition_standings_opponent_team_id FOREIGN KEY (opponent_team_id) REFERENCES public.competition_opponent_teams(id) ON DELETE CASCADE;


--
-- Name: competition_standings fk_competition_standings_phase_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.competition_standings
    ADD CONSTRAINT fk_competition_standings_phase_id FOREIGN KEY (phase_id) REFERENCES public.competition_phases(id) ON DELETE CASCADE;


--
-- Name: competitions fk_competitions_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.competitions
    ADD CONSTRAINT fk_competitions_created_by FOREIGN KEY (created_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: competitions fk_competitions_current_phase_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.competitions
    ADD CONSTRAINT fk_competitions_current_phase_id FOREIGN KEY (current_phase_id) REFERENCES public.competition_phases(id) ON DELETE SET NULL;


--
-- Name: competitions fk_competitions_organization_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.competitions
    ADD CONSTRAINT fk_competitions_organization_id FOREIGN KEY (organization_id) REFERENCES public.organizations(id) ON DELETE RESTRICT;


--
-- Name: competitions fk_competitions_team_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.competitions
    ADD CONSTRAINT fk_competitions_team_id FOREIGN KEY (team_id) REFERENCES public.teams(id) ON DELETE SET NULL;


--
-- Name: email_queue fk_email_queue_created_by_user; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.email_queue
    ADD CONSTRAINT fk_email_queue_created_by_user FOREIGN KEY (created_by_user_id) REFERENCES public.users(id);


--
-- Name: event_subtypes fk_event_subtypes_event_type_code; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_subtypes
    ADD CONSTRAINT fk_event_subtypes_event_type_code FOREIGN KEY (event_type_code) REFERENCES public.event_types(code) ON DELETE RESTRICT;


--
-- Name: match_events fk_match_events_advantage_state; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.match_events
    ADD CONSTRAINT fk_match_events_advantage_state FOREIGN KEY (advantage_state) REFERENCES public.advantage_states(code) ON DELETE RESTRICT;


--
-- Name: match_events fk_match_events_assisting_athlete_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.match_events
    ADD CONSTRAINT fk_match_events_assisting_athlete_id FOREIGN KEY (assisting_athlete_id) REFERENCES public.athletes(id) ON DELETE RESTRICT;


--
-- Name: match_events fk_match_events_athlete_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.match_events
    ADD CONSTRAINT fk_match_events_athlete_id FOREIGN KEY (athlete_id) REFERENCES public.athletes(id) ON DELETE RESTRICT;


--
-- Name: match_events fk_match_events_created_by_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.match_events
    ADD CONSTRAINT fk_match_events_created_by_user_id FOREIGN KEY (created_by_user_id) REFERENCES public.users(id) ON DELETE RESTRICT;


--
-- Name: match_events fk_match_events_event_subtype; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.match_events
    ADD CONSTRAINT fk_match_events_event_subtype FOREIGN KEY (event_subtype) REFERENCES public.event_subtypes(code) ON DELETE RESTRICT;


--
-- Name: match_events fk_match_events_event_type; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.match_events
    ADD CONSTRAINT fk_match_events_event_type FOREIGN KEY (event_type) REFERENCES public.event_types(code) ON DELETE RESTRICT;


--
-- Name: match_events fk_match_events_match_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.match_events
    ADD CONSTRAINT fk_match_events_match_id FOREIGN KEY (match_id) REFERENCES public.matches(id) ON DELETE CASCADE;


--
-- Name: match_events fk_match_events_opponent_team_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.match_events
    ADD CONSTRAINT fk_match_events_opponent_team_id FOREIGN KEY (opponent_team_id) REFERENCES public.teams(id) ON DELETE RESTRICT;


--
-- Name: match_events fk_match_events_phase_of_play; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.match_events
    ADD CONSTRAINT fk_match_events_phase_of_play FOREIGN KEY (phase_of_play) REFERENCES public.phases_of_play(code) ON DELETE RESTRICT;


--
-- Name: match_events fk_match_events_possession_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.match_events
    ADD CONSTRAINT fk_match_events_possession_id FOREIGN KEY (possession_id) REFERENCES public.match_possessions(id) ON DELETE SET NULL;


--
-- Name: match_events fk_match_events_related_event_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.match_events
    ADD CONSTRAINT fk_match_events_related_event_id FOREIGN KEY (related_event_id) REFERENCES public.match_events(id) ON DELETE SET NULL;


--
-- Name: match_events fk_match_events_secondary_athlete_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.match_events
    ADD CONSTRAINT fk_match_events_secondary_athlete_id FOREIGN KEY (secondary_athlete_id) REFERENCES public.athletes(id) ON DELETE RESTRICT;


--
-- Name: match_events fk_match_events_team_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.match_events
    ADD CONSTRAINT fk_match_events_team_id FOREIGN KEY (team_id) REFERENCES public.teams(id) ON DELETE RESTRICT;


--
-- Name: match_periods fk_match_periods_match_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.match_periods
    ADD CONSTRAINT fk_match_periods_match_id FOREIGN KEY (match_id) REFERENCES public.matches(id) ON DELETE CASCADE;


--
-- Name: match_possessions fk_match_possessions_match_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.match_possessions
    ADD CONSTRAINT fk_match_possessions_match_id FOREIGN KEY (match_id) REFERENCES public.matches(id) ON DELETE CASCADE;


--
-- Name: match_possessions fk_match_possessions_team_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.match_possessions
    ADD CONSTRAINT fk_match_possessions_team_id FOREIGN KEY (team_id) REFERENCES public.teams(id) ON DELETE RESTRICT;


--
-- Name: match_roster fk_match_roster_athlete_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.match_roster
    ADD CONSTRAINT fk_match_roster_athlete_id FOREIGN KEY (athlete_id) REFERENCES public.athletes(id) ON DELETE RESTRICT;


--
-- Name: match_roster fk_match_roster_match_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.match_roster
    ADD CONSTRAINT fk_match_roster_match_id FOREIGN KEY (match_id) REFERENCES public.matches(id) ON DELETE CASCADE;


--
-- Name: match_roster fk_match_roster_team_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.match_roster
    ADD CONSTRAINT fk_match_roster_team_id FOREIGN KEY (team_id) REFERENCES public.teams(id) ON DELETE RESTRICT;


--
-- Name: match_teams fk_match_teams_match_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.match_teams
    ADD CONSTRAINT fk_match_teams_match_id FOREIGN KEY (match_id) REFERENCES public.matches(id) ON DELETE CASCADE;


--
-- Name: match_teams fk_match_teams_team_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.match_teams
    ADD CONSTRAINT fk_match_teams_team_id FOREIGN KEY (team_id) REFERENCES public.teams(id) ON DELETE RESTRICT;


--
-- Name: matches fk_matches_away_team_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.matches
    ADD CONSTRAINT fk_matches_away_team_id FOREIGN KEY (away_team_id) REFERENCES public.teams(id) ON DELETE RESTRICT;


--
-- Name: matches fk_matches_created_by_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.matches
    ADD CONSTRAINT fk_matches_created_by_user_id FOREIGN KEY (created_by_user_id) REFERENCES public.users(id) ON DELETE RESTRICT;


--
-- Name: matches fk_matches_home_team_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.matches
    ADD CONSTRAINT fk_matches_home_team_id FOREIGN KEY (home_team_id) REFERENCES public.teams(id) ON DELETE RESTRICT;


--
-- Name: matches fk_matches_our_team_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.matches
    ADD CONSTRAINT fk_matches_our_team_id FOREIGN KEY (our_team_id) REFERENCES public.teams(id) ON DELETE RESTRICT;


--
-- Name: matches fk_matches_season_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.matches
    ADD CONSTRAINT fk_matches_season_id FOREIGN KEY (season_id) REFERENCES public.seasons(id) ON DELETE RESTRICT;


--
-- Name: medical_cases fk_medical_cases_athlete_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.medical_cases
    ADD CONSTRAINT fk_medical_cases_athlete_id FOREIGN KEY (athlete_id) REFERENCES public.athletes(id) ON DELETE RESTRICT;


--
-- Name: medical_cases fk_medical_cases_created_by_user; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.medical_cases
    ADD CONSTRAINT fk_medical_cases_created_by_user FOREIGN KEY (created_by_user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: medical_cases fk_medical_cases_organization; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.medical_cases
    ADD CONSTRAINT fk_medical_cases_organization FOREIGN KEY (organization_id) REFERENCES public.organizations(id) ON DELETE RESTRICT;


--
-- Name: org_memberships fk_org_memberships_created_by_user; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.org_memberships
    ADD CONSTRAINT fk_org_memberships_created_by_user FOREIGN KEY (created_by_user_id) REFERENCES public.users(id);


--
-- Name: org_memberships fk_org_memberships_organization_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.org_memberships
    ADD CONSTRAINT fk_org_memberships_organization_id FOREIGN KEY (organization_id) REFERENCES public.organizations(id) ON DELETE RESTRICT;


--
-- Name: org_memberships fk_org_memberships_person_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.org_memberships
    ADD CONSTRAINT fk_org_memberships_person_id FOREIGN KEY (person_id) REFERENCES public.persons(id) ON DELETE RESTRICT;


--
-- Name: org_memberships fk_org_memberships_role_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.org_memberships
    ADD CONSTRAINT fk_org_memberships_role_id FOREIGN KEY (role_id) REFERENCES public.roles(id) ON DELETE RESTRICT;


--
-- Name: password_resets fk_password_resets_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.password_resets
    ADD CONSTRAINT fk_password_resets_user_id FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: person_addresses fk_person_addresses_created_by_user; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.person_addresses
    ADD CONSTRAINT fk_person_addresses_created_by_user FOREIGN KEY (created_by_user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: person_contacts fk_person_contacts_created_by_user; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.person_contacts
    ADD CONSTRAINT fk_person_contacts_created_by_user FOREIGN KEY (created_by_user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: person_documents fk_person_documents_created_by_user; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.person_documents
    ADD CONSTRAINT fk_person_documents_created_by_user FOREIGN KEY (created_by_user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: person_media fk_person_media_created_by_user; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.person_media
    ADD CONSTRAINT fk_person_media_created_by_user FOREIGN KEY (created_by_user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: role_permissions fk_role_permissions_permission_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.role_permissions
    ADD CONSTRAINT fk_role_permissions_permission_id FOREIGN KEY (permission_id) REFERENCES public.permissions(id) ON DELETE CASCADE;


--
-- Name: role_permissions fk_role_permissions_role_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.role_permissions
    ADD CONSTRAINT fk_role_permissions_role_id FOREIGN KEY (role_id) REFERENCES public.roles(id) ON DELETE CASCADE;


--
-- Name: seasons fk_seasons_created_by_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.seasons
    ADD CONSTRAINT fk_seasons_created_by_user_id FOREIGN KEY (created_by_user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: seasons fk_seasons_team_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.seasons
    ADD CONSTRAINT fk_seasons_team_id FOREIGN KEY (team_id) REFERENCES public.teams(id) ON DELETE RESTRICT;


--
-- Name: team_registrations fk_team_registrations_athlete_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.team_registrations
    ADD CONSTRAINT fk_team_registrations_athlete_id FOREIGN KEY (athlete_id) REFERENCES public.athletes(id) ON DELETE RESTRICT;


--
-- Name: team_registrations fk_team_registrations_created_by_user; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.team_registrations
    ADD CONSTRAINT fk_team_registrations_created_by_user FOREIGN KEY (created_by_user_id) REFERENCES public.users(id);


--
-- Name: team_registrations fk_team_registrations_team_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.team_registrations
    ADD CONSTRAINT fk_team_registrations_team_id FOREIGN KEY (team_id) REFERENCES public.teams(id) ON DELETE RESTRICT;


--
-- Name: teams fk_teams_category_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teams
    ADD CONSTRAINT fk_teams_category_id FOREIGN KEY (category_id) REFERENCES public.categories(id) ON DELETE RESTRICT;


--
-- Name: teams fk_teams_coach_membership_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teams
    ADD CONSTRAINT fk_teams_coach_membership_id FOREIGN KEY (coach_membership_id) REFERENCES public.org_memberships(id) ON DELETE SET NULL;


--
-- Name: teams fk_teams_created_by_membership_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teams
    ADD CONSTRAINT fk_teams_created_by_membership_id FOREIGN KEY (created_by_membership_id) REFERENCES public.org_memberships(id) ON DELETE SET NULL;


--
-- Name: teams fk_teams_created_by_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teams
    ADD CONSTRAINT fk_teams_created_by_user_id FOREIGN KEY (created_by_user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: teams fk_teams_organization_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teams
    ADD CONSTRAINT fk_teams_organization_id FOREIGN KEY (organization_id) REFERENCES public.organizations(id) ON DELETE RESTRICT;


--
-- Name: teams fk_teams_season_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teams
    ADD CONSTRAINT fk_teams_season_id FOREIGN KEY (season_id) REFERENCES public.seasons(id) ON DELETE RESTRICT;


--
-- Name: training_sessions fk_training_sessions_closed_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.training_sessions
    ADD CONSTRAINT fk_training_sessions_closed_by FOREIGN KEY (closed_by_user_id) REFERENCES public.users(id);


--
-- Name: training_sessions fk_training_sessions_created_by_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.training_sessions
    ADD CONSTRAINT fk_training_sessions_created_by_user_id FOREIGN KEY (created_by_user_id) REFERENCES public.users(id) ON DELETE RESTRICT;


--
-- Name: training_sessions fk_training_sessions_microcycle; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.training_sessions
    ADD CONSTRAINT fk_training_sessions_microcycle FOREIGN KEY (microcycle_id) REFERENCES public.training_microcycles(id);


--
-- Name: training_sessions fk_training_sessions_organization_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.training_sessions
    ADD CONSTRAINT fk_training_sessions_organization_id FOREIGN KEY (organization_id) REFERENCES public.organizations(id) ON DELETE RESTRICT;


--
-- Name: training_sessions fk_training_sessions_season_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.training_sessions
    ADD CONSTRAINT fk_training_sessions_season_id FOREIGN KEY (season_id) REFERENCES public.seasons(id) ON DELETE RESTRICT;


--
-- Name: training_sessions fk_training_sessions_team_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.training_sessions
    ADD CONSTRAINT fk_training_sessions_team_id FOREIGN KEY (team_id) REFERENCES public.teams(id) ON DELETE RESTRICT;


--
-- Name: users fk_users_person_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT fk_users_person_id FOREIGN KEY (person_id) REFERENCES public.persons(id) ON DELETE RESTRICT;


--
-- Name: wellness_post fk_wellness_post_athlete_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.wellness_post
    ADD CONSTRAINT fk_wellness_post_athlete_id FOREIGN KEY (athlete_id) REFERENCES public.athletes(id) ON DELETE RESTRICT;


--
-- Name: wellness_post fk_wellness_post_created_by_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.wellness_post
    ADD CONSTRAINT fk_wellness_post_created_by_user_id FOREIGN KEY (created_by_user_id) REFERENCES public.users(id) ON DELETE RESTRICT;


--
-- Name: wellness_post fk_wellness_post_organization_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.wellness_post
    ADD CONSTRAINT fk_wellness_post_organization_id FOREIGN KEY (organization_id) REFERENCES public.organizations(id) ON DELETE RESTRICT;


--
-- Name: wellness_post fk_wellness_post_training_session_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.wellness_post
    ADD CONSTRAINT fk_wellness_post_training_session_id FOREIGN KEY (training_session_id) REFERENCES public.training_sessions(id) ON DELETE RESTRICT;


--
-- Name: wellness_pre fk_wellness_pre_athlete_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.wellness_pre
    ADD CONSTRAINT fk_wellness_pre_athlete_id FOREIGN KEY (athlete_id) REFERENCES public.athletes(id) ON DELETE RESTRICT;


--
-- Name: wellness_pre fk_wellness_pre_created_by_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.wellness_pre
    ADD CONSTRAINT fk_wellness_pre_created_by_user_id FOREIGN KEY (created_by_user_id) REFERENCES public.users(id) ON DELETE RESTRICT;


--
-- Name: wellness_pre fk_wellness_pre_organization_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.wellness_pre
    ADD CONSTRAINT fk_wellness_pre_organization_id FOREIGN KEY (organization_id) REFERENCES public.organizations(id) ON DELETE RESTRICT;


--
-- Name: wellness_pre fk_wellness_pre_training_session_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.wellness_pre
    ADD CONSTRAINT fk_wellness_pre_training_session_id FOREIGN KEY (training_session_id) REFERENCES public.training_sessions(id) ON DELETE RESTRICT;


--
-- Name: notifications notifications_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: person_addresses person_addresses_person_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.person_addresses
    ADD CONSTRAINT person_addresses_person_id_fkey FOREIGN KEY (person_id) REFERENCES public.persons(id) ON DELETE CASCADE;


--
-- Name: person_contacts person_contacts_person_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.person_contacts
    ADD CONSTRAINT person_contacts_person_id_fkey FOREIGN KEY (person_id) REFERENCES public.persons(id) ON DELETE CASCADE;


--
-- Name: person_documents person_documents_person_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.person_documents
    ADD CONSTRAINT person_documents_person_id_fkey FOREIGN KEY (person_id) REFERENCES public.persons(id) ON DELETE CASCADE;


--
-- Name: person_media person_media_person_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.person_media
    ADD CONSTRAINT person_media_person_id_fkey FOREIGN KEY (person_id) REFERENCES public.persons(id) ON DELETE CASCADE;


--
-- Name: refresh_tokens refresh_tokens_parent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.refresh_tokens
    ADD CONSTRAINT refresh_tokens_parent_id_fkey FOREIGN KEY (parent_id) REFERENCES public.refresh_tokens(id) ON DELETE SET NULL;


--
-- Name: refresh_tokens refresh_tokens_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.refresh_tokens
    ADD CONSTRAINT refresh_tokens_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: session_templates session_templates_created_by_membership_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.session_templates
    ADD CONSTRAINT session_templates_created_by_membership_id_fkey FOREIGN KEY (created_by_membership_id) REFERENCES public.org_memberships(id) ON DELETE SET NULL;


--
-- Name: session_templates session_templates_org_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.session_templates
    ADD CONSTRAINT session_templates_org_id_fkey FOREIGN KEY (org_id) REFERENCES public.organizations(id) ON DELETE CASCADE;


--
-- Name: team_memberships team_memberships_org_membership_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.team_memberships
    ADD CONSTRAINT team_memberships_org_membership_id_fkey FOREIGN KEY (org_membership_id) REFERENCES public.org_memberships(id) ON DELETE SET NULL;


--
-- Name: team_memberships team_memberships_person_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.team_memberships
    ADD CONSTRAINT team_memberships_person_id_fkey FOREIGN KEY (person_id) REFERENCES public.persons(id) ON DELETE CASCADE;


--
-- Name: team_memberships team_memberships_team_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.team_memberships
    ADD CONSTRAINT team_memberships_team_id_fkey FOREIGN KEY (team_id) REFERENCES public.teams(id) ON DELETE CASCADE;


--
-- Name: team_wellness_rankings team_wellness_rankings_team_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.team_wellness_rankings
    ADD CONSTRAINT team_wellness_rankings_team_id_fkey FOREIGN KEY (team_id) REFERENCES public.teams(id) ON DELETE CASCADE;


--
-- Name: training_alerts training_alerts_dismissed_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.training_alerts
    ADD CONSTRAINT training_alerts_dismissed_by_user_id_fkey FOREIGN KEY (dismissed_by_user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: training_alerts training_alerts_team_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.training_alerts
    ADD CONSTRAINT training_alerts_team_id_fkey FOREIGN KEY (team_id) REFERENCES public.teams(id) ON DELETE CASCADE;


--
-- Name: training_analytics_cache training_analytics_cache_microcycle_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.training_analytics_cache
    ADD CONSTRAINT training_analytics_cache_microcycle_id_fkey FOREIGN KEY (microcycle_id) REFERENCES public.training_microcycles(id) ON DELETE CASCADE;


--
-- Name: training_analytics_cache training_analytics_cache_team_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.training_analytics_cache
    ADD CONSTRAINT training_analytics_cache_team_id_fkey FOREIGN KEY (team_id) REFERENCES public.teams(id) ON DELETE CASCADE;


--
-- Name: training_cycles training_cycles_created_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.training_cycles
    ADD CONSTRAINT training_cycles_created_by_user_id_fkey FOREIGN KEY (created_by_user_id) REFERENCES public.users(id);


--
-- Name: training_cycles training_cycles_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.training_cycles
    ADD CONSTRAINT training_cycles_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id);


--
-- Name: training_cycles training_cycles_parent_cycle_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.training_cycles
    ADD CONSTRAINT training_cycles_parent_cycle_id_fkey FOREIGN KEY (parent_cycle_id) REFERENCES public.training_cycles(id);


--
-- Name: training_cycles training_cycles_team_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.training_cycles
    ADD CONSTRAINT training_cycles_team_id_fkey FOREIGN KEY (team_id) REFERENCES public.teams(id);


--
-- Name: training_microcycles training_microcycles_created_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.training_microcycles
    ADD CONSTRAINT training_microcycles_created_by_user_id_fkey FOREIGN KEY (created_by_user_id) REFERENCES public.users(id);


--
-- Name: training_microcycles training_microcycles_cycle_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.training_microcycles
    ADD CONSTRAINT training_microcycles_cycle_id_fkey FOREIGN KEY (cycle_id) REFERENCES public.training_cycles(id);


--
-- Name: training_microcycles training_microcycles_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.training_microcycles
    ADD CONSTRAINT training_microcycles_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id);


--
-- Name: training_microcycles training_microcycles_team_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.training_microcycles
    ADD CONSTRAINT training_microcycles_team_id_fkey FOREIGN KEY (team_id) REFERENCES public.teams(id);


--
-- Name: training_session_exercises training_session_exercises_exercise_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.training_session_exercises
    ADD CONSTRAINT training_session_exercises_exercise_id_fkey FOREIGN KEY (exercise_id) REFERENCES public.exercises(id) ON DELETE RESTRICT;


--
-- Name: training_session_exercises training_session_exercises_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.training_session_exercises
    ADD CONSTRAINT training_session_exercises_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.training_sessions(id) ON DELETE CASCADE;


--
-- Name: training_sessions training_sessions_post_review_completed_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.training_sessions
    ADD CONSTRAINT training_sessions_post_review_completed_by_user_id_fkey FOREIGN KEY (post_review_completed_by_user_id) REFERENCES public.users(id);


--
-- Name: training_suggestions training_suggestions_origin_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.training_suggestions
    ADD CONSTRAINT training_suggestions_origin_session_id_fkey FOREIGN KEY (origin_session_id) REFERENCES public.training_sessions(id) ON DELETE CASCADE;


--
-- Name: training_suggestions training_suggestions_team_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.training_suggestions
    ADD CONSTRAINT training_suggestions_team_id_fkey FOREIGN KEY (team_id) REFERENCES public.teams(id) ON DELETE CASCADE;


--
-- Name: wellness_reminders wellness_reminders_athlete_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.wellness_reminders
    ADD CONSTRAINT wellness_reminders_athlete_id_fkey FOREIGN KEY (athlete_id) REFERENCES public.athletes(id) ON DELETE CASCADE;


--
-- Name: wellness_reminders wellness_reminders_training_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.wellness_reminders
    ADD CONSTRAINT wellness_reminders_training_session_id_fkey FOREIGN KEY (training_session_id) REFERENCES public.training_sessions(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict ho7fk19KMuJx0CDdjBtcmOh8HdW1wJfBLfZNAXKQ01TP4bKeGiJbzIYGrhTqyt9

