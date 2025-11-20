
\restrict LvRpyC4XKNPiNuNhcOOBmSUbhfFL8hnOV4fOdZaHhipT7PzohvwkgLX6phIMR9i


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


COMMENT ON SCHEMA "public" IS 'standard public schema';



CREATE EXTENSION IF NOT EXISTS "btree_gin" WITH SCHEMA "public";






CREATE EXTENSION IF NOT EXISTS "pg_graphql" WITH SCHEMA "graphql";






CREATE EXTENSION IF NOT EXISTS "pg_stat_statements" WITH SCHEMA "extensions";






CREATE EXTENSION IF NOT EXISTS "pg_trgm" WITH SCHEMA "public";






CREATE EXTENSION IF NOT EXISTS "pgcrypto" WITH SCHEMA "extensions";






CREATE EXTENSION IF NOT EXISTS "supabase_vault" WITH SCHEMA "vault";






CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA "extensions";






CREATE EXTENSION IF NOT EXISTS "vector" WITH SCHEMA "public";






CREATE TYPE "public"."equipment_criticality" AS ENUM (
    'low',
    'medium',
    'high',
    'critical'
);


ALTER TYPE "public"."equipment_criticality" OWNER TO "postgres";


CREATE TYPE "public"."fault_severity" AS ENUM (
    'low',
    'medium',
    'high',
    'critical'
);


ALTER TYPE "public"."fault_severity" OWNER TO "postgres";


CREATE TYPE "public"."graph_edge_type" AS ENUM (
    'USES_PART',
    'HAS_FAULT',
    'MENTIONED_IN',
    'REFERS_TO',
    'PARENT_OF',
    'CHILD_OF',
    'COMPATIBLE_WITH',
    'RELATED_TO',
    'USED_IN_WO',
    'DOCUMENTED_BY'
);


ALTER TYPE "public"."graph_edge_type" OWNER TO "postgres";


CREATE TYPE "public"."graph_node_type" AS ENUM (
    'equipment',
    'part',
    'fault',
    'document_chunk',
    'work_order',
    'handover_item',
    'supplier'
);


ALTER TYPE "public"."graph_node_type" OWNER TO "postgres";


CREATE TYPE "public"."handover_source_type" AS ENUM (
    'fault',
    'work_order',
    'history',
    'document',
    'predictive',
    'note'
);


ALTER TYPE "public"."handover_source_type" OWNER TO "postgres";


CREATE TYPE "public"."work_order_priority" AS ENUM (
    'routine',
    'important',
    'critical',
    'emergency'
);


ALTER TYPE "public"."work_order_priority" OWNER TO "postgres";


CREATE TYPE "public"."work_order_status" AS ENUM (
    'planned',
    'in_progress',
    'completed',
    'deferred',
    'cancelled'
);


ALTER TYPE "public"."work_order_status" OWNER TO "postgres";


CREATE TYPE "public"."work_order_type" AS ENUM (
    'scheduled',
    'corrective',
    'unplanned',
    'preventive'
);


ALTER TYPE "public"."work_order_type" OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."get_directory_depth_stats"("p_yacht_id" "text") RETURNS TABLE("depth" integer, "document_count" bigint)
    LANGUAGE "plpgsql"
    AS $$
BEGIN
  RETURN QUERY
  SELECT
    jsonb_array_length(metadata->'directories') as depth,
    COUNT(*) as document_count
  FROM documents
  WHERE yacht_id = p_yacht_id
    AND metadata->'directories' IS NOT NULL
  GROUP BY jsonb_array_length(metadata->'directories')
  ORDER BY depth;
END;
$$;


ALTER FUNCTION "public"."get_directory_depth_stats"("p_yacht_id" "text") OWNER TO "postgres";


COMMENT ON FUNCTION "public"."get_directory_depth_stats"("p_yacht_id" "text") IS 'Get document count by directory depth level';


SET default_tablespace = '';

SET default_table_access_method = "heap";


CREATE TABLE IF NOT EXISTS "public"."documents" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "yacht_id" "uuid" NOT NULL,
    "source" "text" NOT NULL,
    "original_path" "text",
    "filename" "text" NOT NULL,
    "content_type" "text",
    "size_bytes" bigint,
    "sha256" "text",
    "storage_path" "text" NOT NULL,
    "equipment_ids" "uuid"[] DEFAULT '{}'::"uuid"[],
    "tags" "text"[] DEFAULT '{}'::"text"[],
    "indexed" boolean DEFAULT false,
    "indexed_at" timestamp with time zone,
    "metadata" "jsonb" DEFAULT '{}'::"jsonb",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "system_path" "text"
);


ALTER TABLE "public"."documents" OWNER TO "postgres";


COMMENT ON TABLE "public"."documents" IS 'Raw document metadata - files from NAS, email, uploads';



COMMENT ON COLUMN "public"."documents"."sha256" IS 'SHA256 hash for file integrity and deduplication (NOT for auth)';



COMMENT ON COLUMN "public"."documents"."indexed" IS 'Whether document has been processed by indexing pipeline';



COMMENT ON COLUMN "public"."documents"."metadata" IS 'Flexible JSONB field for additional metadata (directories, timestamps, etc.)';



COMMENT ON COLUMN "public"."documents"."system_path" IS 'NAS directory hierarchy (e.g., "02_Engineering/Electrical")';



CREATE OR REPLACE FUNCTION "public"."get_document_department"("doc" "public"."documents") RETURNS "text"
    LANGUAGE "plpgsql" IMMUTABLE
    AS $$
BEGIN
  RETURN doc.metadata->'directories'->>0;
END;
$$;


ALTER FUNCTION "public"."get_document_department"("doc" "public"."documents") OWNER TO "postgres";


COMMENT ON FUNCTION "public"."get_document_department"("doc" "public"."documents") IS 'Extract department (first directory) from document metadata';



CREATE OR REPLACE FUNCTION "public"."get_user_role"() RETURNS "text"
    LANGUAGE "sql" STABLE SECURITY DEFINER
    AS $$
  SELECT role
  FROM public.users
  WHERE auth_user_id = auth.uid()
  LIMIT 1;
$$;


ALTER FUNCTION "public"."get_user_role"() OWNER TO "postgres";


COMMENT ON FUNCTION "public"."get_user_role"() IS 'Returns role for currently authenticated user';



CREATE OR REPLACE FUNCTION "public"."get_user_yacht_id"() RETURNS "uuid"
    LANGUAGE "sql" STABLE SECURITY DEFINER
    AS $$
  SELECT yacht_id
  FROM public.users
  WHERE auth_user_id = auth.uid()
  LIMIT 1;
$$;


ALTER FUNCTION "public"."get_user_yacht_id"() OWNER TO "postgres";


COMMENT ON FUNCTION "public"."get_user_yacht_id"() IS 'Returns yacht_id for currently authenticated user';



CREATE OR REPLACE FUNCTION "public"."handle_new_user"() RETURNS "trigger"
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $$
BEGIN
  -- This function should be called by a webhook or database trigger
  -- to create a business user record when auth.users is created
  -- Implementation depends on your onboarding flow
  RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."handle_new_user"() OWNER TO "postgres";


COMMENT ON FUNCTION "public"."handle_new_user"() IS 'Placeholder for auto-creating users records from auth.users';



CREATE OR REPLACE FUNCTION "public"."is_manager"() RETURNS boolean
    LANGUAGE "sql" STABLE SECURITY DEFINER
    AS $$
  SELECT role IN ('manager', 'captain', 'chief_engineer')
  FROM public.users
  WHERE auth_user_id = auth.uid()
  LIMIT 1;
$$;


ALTER FUNCTION "public"."is_manager"() OWNER TO "postgres";


COMMENT ON FUNCTION "public"."is_manager"() IS 'Returns true if user has manager-level permissions';



CREATE OR REPLACE FUNCTION "public"."search_documents_by_directory"("p_yacht_id" "text", "p_directory_prefix" "text") RETURNS TABLE("id" "uuid", "filename" "text", "system_path" "text", "directories" "jsonb", "size_bytes" bigint, "created_at" timestamp with time zone)
    LANGUAGE "plpgsql"
    AS $$
BEGIN
  RETURN QUERY
  SELECT
    d.id,
    d.filename,
    d.system_path,
    d.metadata->'directories' as directories,
    d.size_bytes,
    d.created_at
  FROM documents d
  WHERE d.yacht_id = p_yacht_id
    AND d.metadata->'directories' @> to_jsonb(ARRAY[p_directory_prefix]);
END;
$$;


ALTER FUNCTION "public"."search_documents_by_directory"("p_yacht_id" "text", "p_directory_prefix" "text") OWNER TO "postgres";


COMMENT ON FUNCTION "public"."search_documents_by_directory"("p_yacht_id" "text", "p_directory_prefix" "text") IS 'Search documents by yacht and directory prefix';



CREATE TABLE IF NOT EXISTS "public"."agents" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "yacht_id" "uuid" NOT NULL,
    "name" "text" NOT NULL,
    "agent_secret_hash" "text" NOT NULL,
    "device_info" "jsonb" DEFAULT '{}'::"jsonb",
    "last_seen_at" timestamp with time zone,
    "is_active" boolean DEFAULT true,
    "metadata" "jsonb" DEFAULT '{}'::"jsonb",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "agents_agent_secret_hash_check" CHECK (("agent_secret_hash" ~ '^\$2[aby]\$'::"text"))
);


ALTER TABLE "public"."agents" OWNER TO "postgres";


COMMENT ON TABLE "public"."agents" IS 'Local agent devices (Mac Studio/Mini) for NAS ingestion';



COMMENT ON COLUMN "public"."agents"."agent_secret_hash" IS 'bcrypt hash of agent secret - used for HMAC verification';



COMMENT ON COLUMN "public"."agents"."device_info" IS 'Device metadata: OS, version, IP, hardware specs';



CREATE TABLE IF NOT EXISTS "public"."api_keys" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "yacht_id" "uuid" NOT NULL,
    "key_prefix" "text" NOT NULL,
    "hashed_key" "text" NOT NULL,
    "name" "text" NOT NULL,
    "scopes" "text"[] DEFAULT '{}'::"text"[],
    "created_by" "uuid",
    "expires_at" timestamp with time zone,
    "last_used_at" timestamp with time zone,
    "is_active" boolean DEFAULT true,
    "metadata" "jsonb" DEFAULT '{}'::"jsonb",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "api_keys_hashed_key_check" CHECK (("hashed_key" ~ '^\$2[aby]\$'::"text")),
    CONSTRAINT "api_keys_key_prefix_check" CHECK (("key_prefix" ~ '^sk_(live|test)_[a-z0-9]{4,8}$'::"text"))
);


ALTER TABLE "public"."api_keys" OWNER TO "postgres";


COMMENT ON TABLE "public"."api_keys" IS 'API keys for automation (n8n) and external integrations';



COMMENT ON COLUMN "public"."api_keys"."key_prefix" IS 'First 8-12 chars for identification (e.g., sk_live_a1b2c3d4)';



COMMENT ON COLUMN "public"."api_keys"."hashed_key" IS 'bcrypt hash of full API key';



COMMENT ON COLUMN "public"."api_keys"."scopes" IS 'Granted permissions (e.g., read:equipment, write:work_orders)';



CREATE TABLE IF NOT EXISTS "public"."document_chunks" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "yacht_id" "uuid" NOT NULL,
    "document_id" "uuid" NOT NULL,
    "chunk_index" integer NOT NULL,
    "text" "text" NOT NULL,
    "page_number" integer,
    "embedding" "public"."vector"(1024),
    "equipment_ids" "uuid"[] DEFAULT '{}'::"uuid"[],
    "fault_codes" "text"[] DEFAULT '{}'::"text"[],
    "tags" "text"[] DEFAULT '{}'::"text"[],
    "metadata" "jsonb" DEFAULT '{}'::"jsonb",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."document_chunks" OWNER TO "postgres";


COMMENT ON TABLE "public"."document_chunks" IS 'Chunked document text with vector embeddings for RAG';



COMMENT ON COLUMN "public"."document_chunks"."text" IS 'Chunk text content (250-800 tokens typically)';



COMMENT ON COLUMN "public"."document_chunks"."embedding" IS 'Vector embedding for semantic search';



CREATE OR REPLACE VIEW "public"."document_counts_by_department" AS
 SELECT "yacht_id",
    (("metadata" -> 'directories'::"text") ->> 0) AS "department",
    "count"(*) AS "document_count",
    "sum"("size_bytes") AS "total_size_bytes",
    "count"(*) FILTER (WHERE ("indexed" = true)) AS "indexed_count",
    "count"(*) FILTER (WHERE ("indexed" = false)) AS "pending_count"
   FROM "public"."documents"
  WHERE (("metadata" -> 'directories'::"text") IS NOT NULL)
  GROUP BY "yacht_id", (("metadata" -> 'directories'::"text") ->> 0);


ALTER VIEW "public"."document_counts_by_department" OWNER TO "postgres";


COMMENT ON VIEW "public"."document_counts_by_department" IS 'Document statistics grouped by yacht and department';



CREATE OR REPLACE VIEW "public"."document_directory_tree" AS
 SELECT "yacht_id",
    (("metadata" -> 'directories'::"text") ->> 0) AS "level_1",
    (("metadata" -> 'directories'::"text") ->> 1) AS "level_2",
    (("metadata" -> 'directories'::"text") ->> 2) AS "level_3",
    "count"(*) AS "document_count"
   FROM "public"."documents"
  WHERE (("metadata" -> 'directories'::"text") IS NOT NULL)
  GROUP BY "yacht_id", (("metadata" -> 'directories'::"text") ->> 0), (("metadata" -> 'directories'::"text") ->> 1), (("metadata" -> 'directories'::"text") ->> 2);


ALTER VIEW "public"."document_directory_tree" OWNER TO "postgres";


COMMENT ON VIEW "public"."document_directory_tree" IS 'Hierarchical view of document organization';



CREATE TABLE IF NOT EXISTS "public"."embedding_jobs" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "yacht_id" "uuid" NOT NULL,
    "document_id" "uuid",
    "status" "text" DEFAULT 'pending'::"text" NOT NULL,
    "error_message" "text",
    "started_at" timestamp with time zone,
    "completed_at" timestamp with time zone,
    "metadata" "jsonb" DEFAULT '{}'::"jsonb",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."embedding_jobs" OWNER TO "postgres";


COMMENT ON TABLE "public"."embedding_jobs" IS 'Indexing pipeline job tracking';



CREATE TABLE IF NOT EXISTS "public"."equipment" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "yacht_id" "uuid" NOT NULL,
    "parent_id" "uuid",
    "name" "text" NOT NULL,
    "code" "text",
    "description" "text",
    "location" "text",
    "manufacturer" "text",
    "model" "text",
    "serial_number" "text",
    "installed_date" "date",
    "criticality" "public"."equipment_criticality" DEFAULT 'medium'::"public"."equipment_criticality",
    "system_type" "text",
    "metadata" "jsonb" DEFAULT '{}'::"jsonb",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."equipment" OWNER TO "postgres";


COMMENT ON TABLE "public"."equipment" IS 'Master list of all vessel equipment, systems, and components';



COMMENT ON COLUMN "public"."equipment"."parent_id" IS 'Parent equipment for hierarchical structure';



COMMENT ON COLUMN "public"."equipment"."criticality" IS 'Operational criticality level';



CREATE TABLE IF NOT EXISTS "public"."equipment_parts" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "yacht_id" "uuid" NOT NULL,
    "equipment_id" "uuid" NOT NULL,
    "part_id" "uuid" NOT NULL,
    "quantity_required" integer DEFAULT 1,
    "notes" "text",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."equipment_parts" OWNER TO "postgres";


COMMENT ON TABLE "public"."equipment_parts" IS 'Many-to-many: which parts are used in which equipment';



CREATE TABLE IF NOT EXISTS "public"."event_logs" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "yacht_id" "uuid" NOT NULL,
    "user_id" "uuid",
    "event_type" "text" NOT NULL,
    "entity_type" "text",
    "entity_id" "uuid",
    "metadata" "jsonb" DEFAULT '{}'::"jsonb",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."event_logs" OWNER TO "postgres";


COMMENT ON TABLE "public"."event_logs" IS 'System-wide audit log for all actions';



CREATE TABLE IF NOT EXISTS "public"."faults" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "yacht_id" "uuid" NOT NULL,
    "equipment_id" "uuid" NOT NULL,
    "fault_code" "text",
    "title" "text" NOT NULL,
    "description" "text",
    "severity" "public"."fault_severity" DEFAULT 'medium'::"public"."fault_severity" NOT NULL,
    "detected_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "resolved_at" timestamp with time zone,
    "resolved_by" "uuid",
    "work_order_id" "uuid",
    "metadata" "jsonb" DEFAULT '{}'::"jsonb",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."faults" OWNER TO "postgres";


COMMENT ON TABLE "public"."faults" IS 'Equipment fault events and diagnostic codes';



COMMENT ON COLUMN "public"."faults"."fault_code" IS 'OEM fault code (e.g., E047, SPN 123)';



CREATE TABLE IF NOT EXISTS "public"."graph_edges" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "yacht_id" "uuid" NOT NULL,
    "from_node_id" "uuid" NOT NULL,
    "to_node_id" "uuid" NOT NULL,
    "edge_type" "public"."graph_edge_type" NOT NULL,
    "weight" numeric(10,4),
    "properties" "jsonb" DEFAULT '{}'::"jsonb",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."graph_edges" OWNER TO "postgres";


COMMENT ON TABLE "public"."graph_edges" IS 'Knowledge graph edges - relationships between entities';



COMMENT ON COLUMN "public"."graph_edges"."weight" IS 'Relationship strength/importance';



CREATE TABLE IF NOT EXISTS "public"."graph_nodes" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "yacht_id" "uuid" NOT NULL,
    "node_type" "public"."graph_node_type" NOT NULL,
    "ref_table" "text" NOT NULL,
    "ref_id" "uuid" NOT NULL,
    "label" "text" NOT NULL,
    "properties" "jsonb" DEFAULT '{}'::"jsonb",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."graph_nodes" OWNER TO "postgres";


COMMENT ON TABLE "public"."graph_nodes" IS 'Knowledge graph nodes - entities from various tables';



COMMENT ON COLUMN "public"."graph_nodes"."ref_table" IS 'Source table name';



COMMENT ON COLUMN "public"."graph_nodes"."ref_id" IS 'Source entity ID';



CREATE TABLE IF NOT EXISTS "public"."handover_items" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "yacht_id" "uuid" NOT NULL,
    "handover_id" "uuid" NOT NULL,
    "source_type" "public"."handover_source_type" NOT NULL,
    "source_id" "uuid" NOT NULL,
    "summary" "text",
    "detail" "text",
    "importance" "text" DEFAULT 'normal'::"text",
    "metadata" "jsonb" DEFAULT '{}'::"jsonb",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."handover_items" OWNER TO "postgres";


COMMENT ON TABLE "public"."handover_items" IS 'Items included in handover - polymorphic references';



COMMENT ON COLUMN "public"."handover_items"."source_type" IS 'Type of source: fault, work_order, history, document, predictive';



COMMENT ON COLUMN "public"."handover_items"."source_id" IS 'UUID of the source entity';



CREATE TABLE IF NOT EXISTS "public"."handovers" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "yacht_id" "uuid" NOT NULL,
    "period_start" "date",
    "period_end" "date",
    "title" "text" NOT NULL,
    "description" "text",
    "created_by" "uuid" NOT NULL,
    "status" "text" DEFAULT 'draft'::"text",
    "metadata" "jsonb" DEFAULT '{}'::"jsonb",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."handovers" OWNER TO "postgres";


COMMENT ON TABLE "public"."handovers" IS 'Crew handover documents';



COMMENT ON COLUMN "public"."handovers"."description" IS 'Auto-generated summary from included items';



CREATE TABLE IF NOT EXISTS "public"."hours_of_rest" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "yacht_id" "uuid" NOT NULL,
    "user_id" "uuid" NOT NULL,
    "date" "date" NOT NULL,
    "hours_worked" numeric(5,2) NOT NULL,
    "hours_of_rest" numeric(5,2) NOT NULL,
    "violations" boolean DEFAULT false,
    "notes" "text",
    "metadata" "jsonb" DEFAULT '{}'::"jsonb",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."hours_of_rest" OWNER TO "postgres";


COMMENT ON TABLE "public"."hours_of_rest" IS 'MLC hours of rest compliance records';



CREATE TABLE IF NOT EXISTS "public"."inventory_stock" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "yacht_id" "uuid" NOT NULL,
    "part_id" "uuid" NOT NULL,
    "location" "text",
    "quantity" integer DEFAULT 0 NOT NULL,
    "min_quantity" integer,
    "max_quantity" integer,
    "reorder_quantity" integer,
    "last_counted_at" timestamp with time zone,
    "metadata" "jsonb" DEFAULT '{}'::"jsonb",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."inventory_stock" OWNER TO "postgres";


COMMENT ON TABLE "public"."inventory_stock" IS 'Current inventory levels by location';



COMMENT ON COLUMN "public"."inventory_stock"."location" IS 'Physical storage location on vessel';



CREATE TABLE IF NOT EXISTS "public"."ocred_pages" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "yacht_id" "uuid" NOT NULL,
    "document_id" "uuid" NOT NULL,
    "page_number" integer NOT NULL,
    "raw_text" "text",
    "confidence" numeric(5,2),
    "metadata" "jsonb" DEFAULT '{}'::"jsonb",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."ocred_pages" OWNER TO "postgres";


COMMENT ON TABLE "public"."ocred_pages" IS 'Intermediate OCR results before chunking';



CREATE TABLE IF NOT EXISTS "public"."parts" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "yacht_id" "uuid" NOT NULL,
    "name" "text" NOT NULL,
    "part_number" "text",
    "manufacturer" "text",
    "description" "text",
    "category" "text",
    "model_compatibility" "jsonb" DEFAULT '[]'::"jsonb",
    "metadata" "jsonb" DEFAULT '{}'::"jsonb",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."parts" OWNER TO "postgres";


COMMENT ON TABLE "public"."parts" IS 'Master parts catalog - spares and consumables';



COMMENT ON COLUMN "public"."parts"."model_compatibility" IS 'Compatible equipment models';



CREATE TABLE IF NOT EXISTS "public"."predictive_insights" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "yacht_id" "uuid" NOT NULL,
    "equipment_id" "uuid" NOT NULL,
    "insight_type" "text" NOT NULL,
    "title" "text" NOT NULL,
    "description" "text",
    "recommendation" "text",
    "severity" "text",
    "acknowledged" boolean DEFAULT false,
    "acknowledged_by" "uuid",
    "acknowledged_at" timestamp with time zone,
    "metadata" "jsonb" DEFAULT '{}'::"jsonb",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."predictive_insights" OWNER TO "postgres";


COMMENT ON TABLE "public"."predictive_insights" IS 'AI-generated predictive maintenance insights and recommendations';



COMMENT ON COLUMN "public"."predictive_insights"."description" IS 'Explanation of the insight';



CREATE TABLE IF NOT EXISTS "public"."predictive_state" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "yacht_id" "uuid" NOT NULL,
    "equipment_id" "uuid" NOT NULL,
    "risk_score" numeric(5,4) NOT NULL,
    "confidence" numeric(5,4),
    "contributing_factors" "jsonb" DEFAULT '{}'::"jsonb",
    "last_calculated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "metadata" "jsonb" DEFAULT '{}'::"jsonb",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "predictive_state_confidence_check" CHECK ((("confidence" >= (0)::numeric) AND ("confidence" <= (1)::numeric))),
    CONSTRAINT "predictive_state_risk_score_check" CHECK ((("risk_score" >= (0)::numeric) AND ("risk_score" <= (1)::numeric)))
);


ALTER TABLE "public"."predictive_state" OWNER TO "postgres";


COMMENT ON TABLE "public"."predictive_state" IS 'Current predictive maintenance risk scores';



COMMENT ON COLUMN "public"."predictive_state"."risk_score" IS 'Failure risk score 0.00-1.00';



COMMENT ON COLUMN "public"."predictive_state"."contributing_factors" IS 'Signals contributing to risk score';



CREATE TABLE IF NOT EXISTS "public"."purchase_order_items" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "yacht_id" "uuid" NOT NULL,
    "purchase_order_id" "uuid" NOT NULL,
    "part_id" "uuid",
    "description" "text" NOT NULL,
    "quantity_ordered" integer NOT NULL,
    "quantity_received" integer DEFAULT 0,
    "unit_price" numeric(12,2),
    "metadata" "jsonb" DEFAULT '{}'::"jsonb",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."purchase_order_items" OWNER TO "postgres";


COMMENT ON TABLE "public"."purchase_order_items" IS 'Purchase order line items';



CREATE TABLE IF NOT EXISTS "public"."purchase_orders" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "yacht_id" "uuid" NOT NULL,
    "supplier_id" "uuid",
    "po_number" "text",
    "status" "text" DEFAULT 'draft'::"text",
    "ordered_at" timestamp with time zone,
    "received_at" timestamp with time zone,
    "currency" "text" DEFAULT 'USD'::"text",
    "metadata" "jsonb" DEFAULT '{}'::"jsonb",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."purchase_orders" OWNER TO "postgres";


COMMENT ON TABLE "public"."purchase_orders" IS 'Purchase order tracking';



CREATE TABLE IF NOT EXISTS "public"."search_queries" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "yacht_id" "uuid" NOT NULL,
    "user_id" "uuid",
    "query_text" "text" NOT NULL,
    "interpreted_intent" "text",
    "entities" "jsonb" DEFAULT '{}'::"jsonb",
    "latency_ms" integer,
    "success" boolean,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."search_queries" OWNER TO "postgres";


COMMENT ON TABLE "public"."search_queries" IS 'User search history for analytics and crew pain index';



COMMENT ON COLUMN "public"."search_queries"."entities" IS 'Extracted entities from query (equipment, fault codes, etc)';



CREATE TABLE IF NOT EXISTS "public"."suppliers" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "yacht_id" "uuid" NOT NULL,
    "name" "text" NOT NULL,
    "contact_name" "text",
    "email" "text",
    "phone" "text",
    "address" "jsonb" DEFAULT '{}'::"jsonb",
    "preferred" boolean DEFAULT false,
    "metadata" "jsonb" DEFAULT '{}'::"jsonb",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."suppliers" OWNER TO "postgres";


COMMENT ON TABLE "public"."suppliers" IS 'Vendors, OEMs, and service providers';



CREATE TABLE IF NOT EXISTS "public"."user_roles" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "name" "text" NOT NULL,
    "description" "text",
    "permissions" "jsonb" DEFAULT '{}'::"jsonb",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."user_roles" OWNER TO "postgres";


COMMENT ON TABLE "public"."user_roles" IS 'Role definitions for RBAC';



CREATE TABLE IF NOT EXISTS "public"."users" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "auth_user_id" "uuid" NOT NULL,
    "yacht_id" "uuid" NOT NULL,
    "email" "text" NOT NULL,
    "name" "text" NOT NULL,
    "role" "text" NOT NULL,
    "is_active" boolean DEFAULT true,
    "metadata" "jsonb" DEFAULT '{}'::"jsonb",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "users_role_check" CHECK (("role" = ANY (ARRAY['chief_engineer'::"text", 'eto'::"text", 'captain'::"text", 'deck'::"text", 'interior'::"text", 'manager'::"text", 'vendor'::"text"])))
);


ALTER TABLE "public"."users" OWNER TO "postgres";


COMMENT ON TABLE "public"."users" IS 'Business user records linked to Supabase Auth';



COMMENT ON COLUMN "public"."users"."auth_user_id" IS 'Links to auth.users(id) - enables JWT validation via JWT.sub';



COMMENT ON COLUMN "public"."users"."role" IS 'User role - determines permissions and access levels';



CREATE TABLE IF NOT EXISTS "public"."work_order_history" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "yacht_id" "uuid" NOT NULL,
    "work_order_id" "uuid" NOT NULL,
    "equipment_id" "uuid",
    "completed_by" "uuid",
    "completed_at" timestamp with time zone,
    "notes" "text",
    "hours_logged" integer,
    "status_on_completion" "text",
    "parts_used" "jsonb" DEFAULT '[]'::"jsonb",
    "documents_used" "jsonb" DEFAULT '[]'::"jsonb",
    "faults_related" "jsonb" DEFAULT '[]'::"jsonb",
    "metadata" "jsonb" DEFAULT '{}'::"jsonb",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."work_order_history" OWNER TO "postgres";


COMMENT ON TABLE "public"."work_order_history" IS 'Work order execution history - includes notes, parts used, timeline';



COMMENT ON COLUMN "public"."work_order_history"."notes" IS 'Free-form technician notes - indexed for RAG search';



COMMENT ON COLUMN "public"."work_order_history"."parts_used" IS 'Array of parts consumed during work order';



CREATE TABLE IF NOT EXISTS "public"."work_orders" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "yacht_id" "uuid" NOT NULL,
    "equipment_id" "uuid",
    "title" "text" NOT NULL,
    "description" "text",
    "type" "public"."work_order_type" DEFAULT 'scheduled'::"public"."work_order_type" NOT NULL,
    "priority" "public"."work_order_priority" DEFAULT 'routine'::"public"."work_order_priority" NOT NULL,
    "status" "public"."work_order_status" DEFAULT 'planned'::"public"."work_order_status" NOT NULL,
    "due_date" "date",
    "due_hours" integer,
    "last_completed_date" "date",
    "last_completed_hours" integer,
    "frequency" "jsonb",
    "created_by" "uuid" NOT NULL,
    "updated_by" "uuid",
    "metadata" "jsonb" DEFAULT '{}'::"jsonb",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."work_orders" OWNER TO "postgres";


COMMENT ON TABLE "public"."work_orders" IS 'Planned and corrective maintenance work orders';



COMMENT ON COLUMN "public"."work_orders"."due_hours" IS 'Equipment running hours when maintenance is due';



COMMENT ON COLUMN "public"."work_orders"."frequency" IS 'Recurring schedule definition';



CREATE TABLE IF NOT EXISTS "public"."yachts" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "name" "text" NOT NULL,
    "imo" "text",
    "mmsi" "text",
    "flag_state" "text",
    "length_m" numeric(10,2),
    "owner_ref" "text",
    "yacht_secret_hash" "text" NOT NULL,
    "nas_root_path" "text",
    "status" "text" DEFAULT 'active'::"text",
    "metadata" "jsonb" DEFAULT '{}'::"jsonb",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "yachts_status_check" CHECK (("status" = ANY (ARRAY['active'::"text", 'inactive'::"text", 'demo'::"text"]))),
    CONSTRAINT "yachts_yacht_secret_hash_check" CHECK (("yacht_secret_hash" ~ '^\$2[aby]\$'::"text"))
);


ALTER TABLE "public"."yachts" OWNER TO "postgres";


COMMENT ON TABLE "public"."yachts" IS 'Each yacht (vessel) using CelesteOS - tenant isolation root';



COMMENT ON COLUMN "public"."yachts"."yacht_secret_hash" IS 'bcrypt hash of master yacht secret - for deriving agent keys';



ALTER TABLE ONLY "public"."agents"
    ADD CONSTRAINT "agents_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."api_keys"
    ADD CONSTRAINT "api_keys_hashed_key_key" UNIQUE ("hashed_key");



ALTER TABLE ONLY "public"."api_keys"
    ADD CONSTRAINT "api_keys_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."document_chunks"
    ADD CONSTRAINT "document_chunks_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."documents"
    ADD CONSTRAINT "documents_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."embedding_jobs"
    ADD CONSTRAINT "embedding_jobs_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."equipment_parts"
    ADD CONSTRAINT "equipment_parts_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."equipment"
    ADD CONSTRAINT "equipment_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."event_logs"
    ADD CONSTRAINT "event_logs_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."faults"
    ADD CONSTRAINT "faults_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."graph_edges"
    ADD CONSTRAINT "graph_edges_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."graph_nodes"
    ADD CONSTRAINT "graph_nodes_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."handover_items"
    ADD CONSTRAINT "handover_items_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."handovers"
    ADD CONSTRAINT "handovers_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."hours_of_rest"
    ADD CONSTRAINT "hours_of_rest_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."inventory_stock"
    ADD CONSTRAINT "inventory_stock_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."ocred_pages"
    ADD CONSTRAINT "ocred_pages_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."parts"
    ADD CONSTRAINT "parts_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."predictive_insights"
    ADD CONSTRAINT "predictive_insights_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."predictive_state"
    ADD CONSTRAINT "predictive_state_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."purchase_order_items"
    ADD CONSTRAINT "purchase_order_items_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."purchase_orders"
    ADD CONSTRAINT "purchase_orders_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."search_queries"
    ADD CONSTRAINT "search_queries_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."suppliers"
    ADD CONSTRAINT "suppliers_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."user_roles"
    ADD CONSTRAINT "user_roles_name_key" UNIQUE ("name");



ALTER TABLE ONLY "public"."user_roles"
    ADD CONSTRAINT "user_roles_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."users"
    ADD CONSTRAINT "users_auth_user_id_key" UNIQUE ("auth_user_id");



ALTER TABLE ONLY "public"."users"
    ADD CONSTRAINT "users_email_key" UNIQUE ("email");



ALTER TABLE ONLY "public"."users"
    ADD CONSTRAINT "users_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."work_order_history"
    ADD CONSTRAINT "work_order_history_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."work_orders"
    ADD CONSTRAINT "work_orders_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."yachts"
    ADD CONSTRAINT "yachts_pkey" PRIMARY KEY ("id");



CREATE INDEX "idx_agents_is_active" ON "public"."agents" USING "btree" ("is_active");



CREATE INDEX "idx_agents_yacht_id" ON "public"."agents" USING "btree" ("yacht_id");



CREATE INDEX "idx_api_keys_hashed_key" ON "public"."api_keys" USING "btree" ("hashed_key");



CREATE INDEX "idx_api_keys_is_active" ON "public"."api_keys" USING "btree" ("is_active");



CREATE INDEX "idx_api_keys_yacht_id" ON "public"."api_keys" USING "btree" ("yacht_id");



CREATE INDEX "idx_document_chunks_document_id" ON "public"."document_chunks" USING "btree" ("document_id");



CREATE INDEX "idx_document_chunks_embedding" ON "public"."document_chunks" USING "ivfflat" ("embedding" "public"."vector_cosine_ops") WITH ("lists"='100');



CREATE INDEX "idx_document_chunks_equipment_ids" ON "public"."document_chunks" USING "gin" ("equipment_ids");



CREATE INDEX "idx_document_chunks_fault_codes" ON "public"."document_chunks" USING "gin" ("fault_codes");



CREATE INDEX "idx_document_chunks_yacht_id" ON "public"."document_chunks" USING "btree" ("yacht_id");



CREATE INDEX "idx_documents_department" ON "public"."documents" USING "btree" (((("metadata" -> 'directories'::"text") -> 0)));



CREATE INDEX "idx_documents_directories" ON "public"."documents" USING "gin" ((("metadata" -> 'directories'::"text")));



CREATE INDEX "idx_documents_equipment_ids" ON "public"."documents" USING "gin" ("equipment_ids");



CREATE INDEX "idx_documents_indexed" ON "public"."documents" USING "btree" ("indexed");



CREATE INDEX "idx_documents_metadata" ON "public"."documents" USING "gin" ("metadata");



CREATE INDEX "idx_documents_sha256" ON "public"."documents" USING "btree" ("sha256");



CREATE INDEX "idx_documents_source" ON "public"."documents" USING "btree" ("source");



CREATE INDEX "idx_documents_system_path" ON "public"."documents" USING "btree" ("system_path");



CREATE INDEX "idx_documents_system_path_gin" ON "public"."documents" USING "gin" ("system_path" "public"."gin_trgm_ops");



CREATE INDEX "idx_documents_tags" ON "public"."documents" USING "gin" ("tags");



CREATE INDEX "idx_documents_yacht_id" ON "public"."documents" USING "btree" ("yacht_id");



CREATE INDEX "idx_documents_yacht_system" ON "public"."documents" USING "btree" ("yacht_id", "system_path");



CREATE INDEX "idx_documents_yacht_system_path" ON "public"."documents" USING "btree" ("yacht_id", "system_path");



CREATE INDEX "idx_embedding_jobs_document_id" ON "public"."embedding_jobs" USING "btree" ("document_id");



CREATE INDEX "idx_embedding_jobs_status" ON "public"."embedding_jobs" USING "btree" ("status");



CREATE INDEX "idx_embedding_jobs_yacht_id" ON "public"."embedding_jobs" USING "btree" ("yacht_id");



CREATE INDEX "idx_equipment_code" ON "public"."equipment" USING "btree" ("code");



CREATE INDEX "idx_equipment_criticality" ON "public"."equipment" USING "btree" ("criticality");



CREATE INDEX "idx_equipment_parent_id" ON "public"."equipment" USING "btree" ("parent_id");



CREATE INDEX "idx_equipment_parts_equipment_id" ON "public"."equipment_parts" USING "btree" ("equipment_id");



CREATE INDEX "idx_equipment_parts_part_id" ON "public"."equipment_parts" USING "btree" ("part_id");



CREATE UNIQUE INDEX "idx_equipment_parts_unique" ON "public"."equipment_parts" USING "btree" ("equipment_id", "part_id");



CREATE INDEX "idx_equipment_parts_yacht_id" ON "public"."equipment_parts" USING "btree" ("yacht_id");



CREATE INDEX "idx_equipment_system_type" ON "public"."equipment" USING "btree" ("system_type");



CREATE INDEX "idx_equipment_yacht_id" ON "public"."equipment" USING "btree" ("yacht_id");



CREATE INDEX "idx_event_logs_created_at" ON "public"."event_logs" USING "btree" ("created_at");



CREATE INDEX "idx_event_logs_event_type" ON "public"."event_logs" USING "btree" ("event_type");



CREATE INDEX "idx_event_logs_user_id" ON "public"."event_logs" USING "btree" ("user_id");



CREATE INDEX "idx_event_logs_yacht_id" ON "public"."event_logs" USING "btree" ("yacht_id");



CREATE INDEX "idx_faults_detected_at" ON "public"."faults" USING "btree" ("detected_at");



CREATE INDEX "idx_faults_equipment_id" ON "public"."faults" USING "btree" ("equipment_id");



CREATE INDEX "idx_faults_fault_code" ON "public"."faults" USING "btree" ("fault_code");



CREATE INDEX "idx_faults_severity" ON "public"."faults" USING "btree" ("severity");



CREATE INDEX "idx_faults_work_order_id" ON "public"."faults" USING "btree" ("work_order_id");



CREATE INDEX "idx_faults_yacht_id" ON "public"."faults" USING "btree" ("yacht_id");



CREATE INDEX "idx_graph_edges_from" ON "public"."graph_edges" USING "btree" ("from_node_id");



CREATE INDEX "idx_graph_edges_properties" ON "public"."graph_edges" USING "gin" ("properties");



CREATE INDEX "idx_graph_edges_to" ON "public"."graph_edges" USING "btree" ("to_node_id");



CREATE INDEX "idx_graph_edges_type" ON "public"."graph_edges" USING "btree" ("edge_type");



CREATE INDEX "idx_graph_edges_yacht_id" ON "public"."graph_edges" USING "btree" ("yacht_id");



CREATE INDEX "idx_graph_nodes_properties" ON "public"."graph_nodes" USING "gin" ("properties");



CREATE INDEX "idx_graph_nodes_ref" ON "public"."graph_nodes" USING "btree" ("ref_table", "ref_id");



CREATE INDEX "idx_graph_nodes_type" ON "public"."graph_nodes" USING "btree" ("node_type");



CREATE INDEX "idx_graph_nodes_yacht_id" ON "public"."graph_nodes" USING "btree" ("yacht_id");



CREATE INDEX "idx_handover_items_handover_id" ON "public"."handover_items" USING "btree" ("handover_id");



CREATE INDEX "idx_handover_items_source" ON "public"."handover_items" USING "btree" ("source_type", "source_id");



CREATE INDEX "idx_handover_items_yacht_id" ON "public"."handover_items" USING "btree" ("yacht_id");



CREATE INDEX "idx_handovers_period" ON "public"."handovers" USING "btree" ("period_start", "period_end");



CREATE INDEX "idx_handovers_status" ON "public"."handovers" USING "btree" ("status");



CREATE INDEX "idx_handovers_yacht_id" ON "public"."handovers" USING "btree" ("yacht_id");



CREATE INDEX "idx_hours_of_rest_date" ON "public"."hours_of_rest" USING "btree" ("date");



CREATE UNIQUE INDEX "idx_hours_of_rest_unique" ON "public"."hours_of_rest" USING "btree" ("yacht_id", "user_id", "date");



CREATE INDEX "idx_hours_of_rest_user_id" ON "public"."hours_of_rest" USING "btree" ("user_id");



CREATE INDEX "idx_hours_of_rest_yacht_id" ON "public"."hours_of_rest" USING "btree" ("yacht_id");



CREATE INDEX "idx_inventory_stock_location" ON "public"."inventory_stock" USING "btree" ("location");



CREATE INDEX "idx_inventory_stock_part_id" ON "public"."inventory_stock" USING "btree" ("part_id");



CREATE INDEX "idx_inventory_stock_yacht_id" ON "public"."inventory_stock" USING "btree" ("yacht_id");



CREATE INDEX "idx_ocred_pages_document_id" ON "public"."ocred_pages" USING "btree" ("document_id");



CREATE INDEX "idx_ocred_pages_yacht_id" ON "public"."ocred_pages" USING "btree" ("yacht_id");



CREATE INDEX "idx_parts_category" ON "public"."parts" USING "btree" ("category");



CREATE INDEX "idx_parts_part_number" ON "public"."parts" USING "btree" ("part_number");



CREATE INDEX "idx_parts_yacht_id" ON "public"."parts" USING "btree" ("yacht_id");



CREATE INDEX "idx_predictive_insights_acknowledged" ON "public"."predictive_insights" USING "btree" ("acknowledged");



CREATE INDEX "idx_predictive_insights_equipment_id" ON "public"."predictive_insights" USING "btree" ("equipment_id");



CREATE INDEX "idx_predictive_insights_severity" ON "public"."predictive_insights" USING "btree" ("severity");



CREATE INDEX "idx_predictive_insights_yacht_id" ON "public"."predictive_insights" USING "btree" ("yacht_id");



CREATE INDEX "idx_predictive_state_equipment_id" ON "public"."predictive_state" USING "btree" ("equipment_id");



CREATE INDEX "idx_predictive_state_risk_score" ON "public"."predictive_state" USING "btree" ("risk_score");



CREATE UNIQUE INDEX "idx_predictive_state_unique" ON "public"."predictive_state" USING "btree" ("yacht_id", "equipment_id");



CREATE INDEX "idx_predictive_state_yacht_id" ON "public"."predictive_state" USING "btree" ("yacht_id");



CREATE INDEX "idx_purchase_order_items_part_id" ON "public"."purchase_order_items" USING "btree" ("part_id");



CREATE INDEX "idx_purchase_order_items_po_id" ON "public"."purchase_order_items" USING "btree" ("purchase_order_id");



CREATE INDEX "idx_purchase_order_items_yacht_id" ON "public"."purchase_order_items" USING "btree" ("yacht_id");



CREATE INDEX "idx_purchase_orders_status" ON "public"."purchase_orders" USING "btree" ("status");



CREATE INDEX "idx_purchase_orders_supplier_id" ON "public"."purchase_orders" USING "btree" ("supplier_id");



CREATE INDEX "idx_purchase_orders_yacht_id" ON "public"."purchase_orders" USING "btree" ("yacht_id");



CREATE INDEX "idx_search_queries_created_at" ON "public"."search_queries" USING "btree" ("created_at");



CREATE INDEX "idx_search_queries_intent" ON "public"."search_queries" USING "btree" ("interpreted_intent");



CREATE INDEX "idx_search_queries_user_id" ON "public"."search_queries" USING "btree" ("user_id");



CREATE INDEX "idx_search_queries_yacht_id" ON "public"."search_queries" USING "btree" ("yacht_id");



CREATE INDEX "idx_suppliers_preferred" ON "public"."suppliers" USING "btree" ("preferred");



CREATE INDEX "idx_suppliers_yacht_id" ON "public"."suppliers" USING "btree" ("yacht_id");



CREATE INDEX "idx_users_auth_user_id" ON "public"."users" USING "btree" ("auth_user_id");



CREATE INDEX "idx_users_email" ON "public"."users" USING "btree" ("email");



CREATE INDEX "idx_users_role" ON "public"."users" USING "btree" ("role");



CREATE INDEX "idx_users_yacht_id" ON "public"."users" USING "btree" ("yacht_id");



CREATE INDEX "idx_work_order_history_completed_at" ON "public"."work_order_history" USING "btree" ("completed_at");



CREATE INDEX "idx_work_order_history_equipment_id" ON "public"."work_order_history" USING "btree" ("equipment_id");



CREATE INDEX "idx_work_order_history_work_order_id" ON "public"."work_order_history" USING "btree" ("work_order_id");



CREATE INDEX "idx_work_order_history_yacht_id" ON "public"."work_order_history" USING "btree" ("yacht_id");



CREATE INDEX "idx_work_orders_due_date" ON "public"."work_orders" USING "btree" ("due_date");



CREATE INDEX "idx_work_orders_equipment_id" ON "public"."work_orders" USING "btree" ("equipment_id");



CREATE INDEX "idx_work_orders_priority" ON "public"."work_orders" USING "btree" ("priority");



CREATE INDEX "idx_work_orders_status" ON "public"."work_orders" USING "btree" ("status");



CREATE INDEX "idx_work_orders_yacht_id" ON "public"."work_orders" USING "btree" ("yacht_id");



CREATE INDEX "idx_yachts_status" ON "public"."yachts" USING "btree" ("status");



ALTER TABLE ONLY "public"."agents"
    ADD CONSTRAINT "agents_yacht_id_fkey" FOREIGN KEY ("yacht_id") REFERENCES "public"."yachts"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."api_keys"
    ADD CONSTRAINT "api_keys_created_by_fkey" FOREIGN KEY ("created_by") REFERENCES "public"."users"("id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."api_keys"
    ADD CONSTRAINT "api_keys_yacht_id_fkey" FOREIGN KEY ("yacht_id") REFERENCES "public"."yachts"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."document_chunks"
    ADD CONSTRAINT "document_chunks_document_id_fkey" FOREIGN KEY ("document_id") REFERENCES "public"."documents"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."document_chunks"
    ADD CONSTRAINT "document_chunks_yacht_id_fkey" FOREIGN KEY ("yacht_id") REFERENCES "public"."yachts"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."embedding_jobs"
    ADD CONSTRAINT "embedding_jobs_document_id_fkey" FOREIGN KEY ("document_id") REFERENCES "public"."documents"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."embedding_jobs"
    ADD CONSTRAINT "embedding_jobs_yacht_id_fkey" FOREIGN KEY ("yacht_id") REFERENCES "public"."yachts"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."equipment"
    ADD CONSTRAINT "equipment_parent_id_fkey" FOREIGN KEY ("parent_id") REFERENCES "public"."equipment"("id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."equipment_parts"
    ADD CONSTRAINT "equipment_parts_equipment_id_fkey" FOREIGN KEY ("equipment_id") REFERENCES "public"."equipment"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."equipment_parts"
    ADD CONSTRAINT "equipment_parts_part_id_fkey" FOREIGN KEY ("part_id") REFERENCES "public"."parts"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."equipment_parts"
    ADD CONSTRAINT "equipment_parts_yacht_id_fkey" FOREIGN KEY ("yacht_id") REFERENCES "public"."yachts"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."equipment"
    ADD CONSTRAINT "equipment_yacht_id_fkey" FOREIGN KEY ("yacht_id") REFERENCES "public"."yachts"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."event_logs"
    ADD CONSTRAINT "event_logs_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "public"."users"("id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."event_logs"
    ADD CONSTRAINT "event_logs_yacht_id_fkey" FOREIGN KEY ("yacht_id") REFERENCES "public"."yachts"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."faults"
    ADD CONSTRAINT "faults_equipment_id_fkey" FOREIGN KEY ("equipment_id") REFERENCES "public"."equipment"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."faults"
    ADD CONSTRAINT "faults_resolved_by_fkey" FOREIGN KEY ("resolved_by") REFERENCES "public"."users"("id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."faults"
    ADD CONSTRAINT "faults_work_order_id_fkey" FOREIGN KEY ("work_order_id") REFERENCES "public"."work_orders"("id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."faults"
    ADD CONSTRAINT "faults_yacht_id_fkey" FOREIGN KEY ("yacht_id") REFERENCES "public"."yachts"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."graph_edges"
    ADD CONSTRAINT "graph_edges_from_node_id_fkey" FOREIGN KEY ("from_node_id") REFERENCES "public"."graph_nodes"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."graph_edges"
    ADD CONSTRAINT "graph_edges_to_node_id_fkey" FOREIGN KEY ("to_node_id") REFERENCES "public"."graph_nodes"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."graph_edges"
    ADD CONSTRAINT "graph_edges_yacht_id_fkey" FOREIGN KEY ("yacht_id") REFERENCES "public"."yachts"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."graph_nodes"
    ADD CONSTRAINT "graph_nodes_yacht_id_fkey" FOREIGN KEY ("yacht_id") REFERENCES "public"."yachts"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."handover_items"
    ADD CONSTRAINT "handover_items_handover_id_fkey" FOREIGN KEY ("handover_id") REFERENCES "public"."handovers"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."handover_items"
    ADD CONSTRAINT "handover_items_yacht_id_fkey" FOREIGN KEY ("yacht_id") REFERENCES "public"."yachts"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."handovers"
    ADD CONSTRAINT "handovers_created_by_fkey" FOREIGN KEY ("created_by") REFERENCES "public"."users"("id") ON DELETE RESTRICT;



ALTER TABLE ONLY "public"."handovers"
    ADD CONSTRAINT "handovers_yacht_id_fkey" FOREIGN KEY ("yacht_id") REFERENCES "public"."yachts"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."hours_of_rest"
    ADD CONSTRAINT "hours_of_rest_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "public"."users"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."hours_of_rest"
    ADD CONSTRAINT "hours_of_rest_yacht_id_fkey" FOREIGN KEY ("yacht_id") REFERENCES "public"."yachts"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."inventory_stock"
    ADD CONSTRAINT "inventory_stock_part_id_fkey" FOREIGN KEY ("part_id") REFERENCES "public"."parts"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."inventory_stock"
    ADD CONSTRAINT "inventory_stock_yacht_id_fkey" FOREIGN KEY ("yacht_id") REFERENCES "public"."yachts"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."ocred_pages"
    ADD CONSTRAINT "ocred_pages_document_id_fkey" FOREIGN KEY ("document_id") REFERENCES "public"."documents"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."ocred_pages"
    ADD CONSTRAINT "ocred_pages_yacht_id_fkey" FOREIGN KEY ("yacht_id") REFERENCES "public"."yachts"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."parts"
    ADD CONSTRAINT "parts_yacht_id_fkey" FOREIGN KEY ("yacht_id") REFERENCES "public"."yachts"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."predictive_insights"
    ADD CONSTRAINT "predictive_insights_acknowledged_by_fkey" FOREIGN KEY ("acknowledged_by") REFERENCES "public"."users"("id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."predictive_insights"
    ADD CONSTRAINT "predictive_insights_equipment_id_fkey" FOREIGN KEY ("equipment_id") REFERENCES "public"."equipment"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."predictive_insights"
    ADD CONSTRAINT "predictive_insights_yacht_id_fkey" FOREIGN KEY ("yacht_id") REFERENCES "public"."yachts"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."predictive_state"
    ADD CONSTRAINT "predictive_state_equipment_id_fkey" FOREIGN KEY ("equipment_id") REFERENCES "public"."equipment"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."predictive_state"
    ADD CONSTRAINT "predictive_state_yacht_id_fkey" FOREIGN KEY ("yacht_id") REFERENCES "public"."yachts"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."purchase_order_items"
    ADD CONSTRAINT "purchase_order_items_part_id_fkey" FOREIGN KEY ("part_id") REFERENCES "public"."parts"("id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."purchase_order_items"
    ADD CONSTRAINT "purchase_order_items_purchase_order_id_fkey" FOREIGN KEY ("purchase_order_id") REFERENCES "public"."purchase_orders"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."purchase_order_items"
    ADD CONSTRAINT "purchase_order_items_yacht_id_fkey" FOREIGN KEY ("yacht_id") REFERENCES "public"."yachts"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."purchase_orders"
    ADD CONSTRAINT "purchase_orders_supplier_id_fkey" FOREIGN KEY ("supplier_id") REFERENCES "public"."suppliers"("id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."purchase_orders"
    ADD CONSTRAINT "purchase_orders_yacht_id_fkey" FOREIGN KEY ("yacht_id") REFERENCES "public"."yachts"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."search_queries"
    ADD CONSTRAINT "search_queries_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "public"."users"("id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."search_queries"
    ADD CONSTRAINT "search_queries_yacht_id_fkey" FOREIGN KEY ("yacht_id") REFERENCES "public"."yachts"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."suppliers"
    ADD CONSTRAINT "suppliers_yacht_id_fkey" FOREIGN KEY ("yacht_id") REFERENCES "public"."yachts"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."users"
    ADD CONSTRAINT "users_auth_user_id_fkey" FOREIGN KEY ("auth_user_id") REFERENCES "auth"."users"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."users"
    ADD CONSTRAINT "users_yacht_id_fkey" FOREIGN KEY ("yacht_id") REFERENCES "public"."yachts"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."work_order_history"
    ADD CONSTRAINT "work_order_history_completed_by_fkey" FOREIGN KEY ("completed_by") REFERENCES "public"."users"("id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."work_order_history"
    ADD CONSTRAINT "work_order_history_equipment_id_fkey" FOREIGN KEY ("equipment_id") REFERENCES "public"."equipment"("id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."work_order_history"
    ADD CONSTRAINT "work_order_history_work_order_id_fkey" FOREIGN KEY ("work_order_id") REFERENCES "public"."work_orders"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."work_order_history"
    ADD CONSTRAINT "work_order_history_yacht_id_fkey" FOREIGN KEY ("yacht_id") REFERENCES "public"."yachts"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."work_orders"
    ADD CONSTRAINT "work_orders_created_by_fkey" FOREIGN KEY ("created_by") REFERENCES "public"."users"("id") ON DELETE RESTRICT;



ALTER TABLE ONLY "public"."work_orders"
    ADD CONSTRAINT "work_orders_equipment_id_fkey" FOREIGN KEY ("equipment_id") REFERENCES "public"."equipment"("id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."work_orders"
    ADD CONSTRAINT "work_orders_updated_by_fkey" FOREIGN KEY ("updated_by") REFERENCES "public"."users"("id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."work_orders"
    ADD CONSTRAINT "work_orders_yacht_id_fkey" FOREIGN KEY ("yacht_id") REFERENCES "public"."yachts"("id") ON DELETE CASCADE;



CREATE POLICY "Anyone can view roles" ON "public"."user_roles" FOR SELECT USING (true);



COMMENT ON POLICY "Anyone can view roles" ON "public"."user_roles" IS 'Role definitions are globally readable';



CREATE POLICY "Engineers can acknowledge insights" ON "public"."predictive_insights" FOR UPDATE USING ((("yacht_id" = "public"."get_user_yacht_id"()) AND ("public"."get_user_role"() = ANY (ARRAY['chief_engineer'::"text", 'eto'::"text", 'manager'::"text"])))) WITH CHECK ((("yacht_id" = "public"."get_user_yacht_id"()) AND ("public"."get_user_role"() = ANY (ARRAY['chief_engineer'::"text", 'eto'::"text", 'manager'::"text"]))));



COMMENT ON POLICY "Engineers can acknowledge insights" ON "public"."predictive_insights" IS 'Engineers can acknowledge/dismiss insights';



CREATE POLICY "Engineers can add history" ON "public"."work_order_history" FOR INSERT WITH CHECK ((("yacht_id" = "public"."get_user_yacht_id"()) AND ("public"."get_user_role"() = ANY (ARRAY['chief_engineer'::"text", 'eto'::"text", 'deck'::"text", 'interior'::"text"]))));



COMMENT ON POLICY "Engineers can add history" ON "public"."work_order_history" IS 'Crew can log work completion';



CREATE POLICY "Engineers can create work orders" ON "public"."work_orders" FOR INSERT WITH CHECK ((("yacht_id" = "public"."get_user_yacht_id"()) AND ("public"."get_user_role"() = ANY (ARRAY['chief_engineer'::"text", 'eto'::"text", 'deck'::"text", 'interior'::"text"]))));



COMMENT ON POLICY "Engineers can create work orders" ON "public"."work_orders" IS 'Crew can create work orders';



CREATE POLICY "Engineers can manage equipment" ON "public"."equipment" USING ((("yacht_id" = "public"."get_user_yacht_id"()) AND ("public"."get_user_role"() = ANY (ARRAY['chief_engineer'::"text", 'eto'::"text", 'manager'::"text"]))));



COMMENT ON POLICY "Engineers can manage equipment" ON "public"."equipment" IS 'Only engineers can modify equipment';



CREATE POLICY "Engineers can manage equipment parts" ON "public"."equipment_parts" USING ((("yacht_id" = "public"."get_user_yacht_id"()) AND ("public"."get_user_role"() = ANY (ARRAY['chief_engineer'::"text", 'eto'::"text", 'manager'::"text"]))));



COMMENT ON POLICY "Engineers can manage equipment parts" ON "public"."equipment_parts" IS 'Engineers link parts to equipment';



CREATE POLICY "Engineers can manage faults" ON "public"."faults" USING ((("yacht_id" = "public"."get_user_yacht_id"()) AND ("public"."get_user_role"() = ANY (ARRAY['chief_engineer'::"text", 'eto'::"text", 'deck'::"text", 'interior'::"text"]))));



COMMENT ON POLICY "Engineers can manage faults" ON "public"."faults" IS 'Crew can create/resolve faults';



CREATE POLICY "Engineers can manage handover items" ON "public"."handover_items" USING ((("yacht_id" = "public"."get_user_yacht_id"()) AND ("public"."get_user_role"() = ANY (ARRAY['chief_engineer'::"text", 'eto'::"text", 'captain'::"text", 'manager'::"text"]))));



COMMENT ON POLICY "Engineers can manage handover items" ON "public"."handover_items" IS 'Senior crew manage items';



CREATE POLICY "Engineers can manage handovers" ON "public"."handovers" USING ((("yacht_id" = "public"."get_user_yacht_id"()) AND ("public"."get_user_role"() = ANY (ARRAY['chief_engineer'::"text", 'eto'::"text", 'captain'::"text", 'manager'::"text"]))));



COMMENT ON POLICY "Engineers can manage handovers" ON "public"."handovers" IS 'Senior crew create handovers';



CREATE POLICY "Engineers can manage parts" ON "public"."parts" USING ((("yacht_id" = "public"."get_user_yacht_id"()) AND ("public"."get_user_role"() = ANY (ARRAY['chief_engineer'::"text", 'eto'::"text", 'manager'::"text"]))));



COMMENT ON POLICY "Engineers can manage parts" ON "public"."parts" IS 'Engineers manage parts catalog';



CREATE POLICY "Engineers can manage stock" ON "public"."inventory_stock" USING ((("yacht_id" = "public"."get_user_yacht_id"()) AND ("public"."get_user_role"() = ANY (ARRAY['chief_engineer'::"text", 'eto'::"text", 'deck'::"text", 'interior'::"text"]))));



COMMENT ON POLICY "Engineers can manage stock" ON "public"."inventory_stock" IS 'Crew can update stock counts';



CREATE POLICY "Engineers can update work orders" ON "public"."work_orders" FOR UPDATE USING ((("yacht_id" = "public"."get_user_yacht_id"()) AND ("public"."get_user_role"() = ANY (ARRAY['chief_engineer'::"text", 'eto'::"text", 'manager'::"text"]))));



COMMENT ON POLICY "Engineers can update work orders" ON "public"."work_orders" IS 'Engineers can modify work orders';



CREATE POLICY "Managers can delete work orders" ON "public"."work_orders" FOR DELETE USING ((("yacht_id" = "public"."get_user_yacht_id"()) AND "public"."is_manager"()));



COMMENT ON POLICY "Managers can delete work orders" ON "public"."work_orders" IS 'Only managers can delete';



CREATE POLICY "Managers can manage PO items" ON "public"."purchase_order_items" USING ((("yacht_id" = "public"."get_user_yacht_id"()) AND "public"."is_manager"()));



COMMENT ON POLICY "Managers can manage PO items" ON "public"."purchase_order_items" IS 'Managers manage PO items';



CREATE POLICY "Managers can manage agents" ON "public"."agents" USING ((("yacht_id" = "public"."get_user_yacht_id"()) AND "public"."is_manager"()));



COMMENT ON POLICY "Managers can manage agents" ON "public"."agents" IS 'Only managers can create/edit agents';



CREATE POLICY "Managers can manage api keys" ON "public"."api_keys" USING ((("yacht_id" = "public"."get_user_yacht_id"()) AND "public"."is_manager"()));



COMMENT ON POLICY "Managers can manage api keys" ON "public"."api_keys" IS 'Only managers can create/revoke API keys';



CREATE POLICY "Managers can manage documents" ON "public"."documents" USING ((("yacht_id" = "public"."get_user_yacht_id"()) AND "public"."is_manager"()));



COMMENT ON POLICY "Managers can manage documents" ON "public"."documents" IS 'Managers can delete/organize docs';



CREATE POLICY "Managers can manage purchase orders" ON "public"."purchase_orders" USING ((("yacht_id" = "public"."get_user_yacht_id"()) AND "public"."is_manager"()));



COMMENT ON POLICY "Managers can manage purchase orders" ON "public"."purchase_orders" IS 'Managers create/approve POs';



CREATE POLICY "Managers can manage suppliers" ON "public"."suppliers" USING ((("yacht_id" = "public"."get_user_yacht_id"()) AND "public"."is_manager"()));



COMMENT ON POLICY "Managers can manage suppliers" ON "public"."suppliers" IS 'Managers manage supplier relationships';



CREATE POLICY "Managers can manage yacht users" ON "public"."users" USING ((("yacht_id" = "public"."get_user_yacht_id"()) AND "public"."is_manager"()));



COMMENT ON POLICY "Managers can manage yacht users" ON "public"."users" IS 'Managers can add/edit/remove users';



CREATE POLICY "Managers can update yacht settings" ON "public"."yachts" FOR UPDATE USING ((("id" = "public"."get_user_yacht_id"()) AND "public"."is_manager"()));



COMMENT ON POLICY "Managers can update yacht settings" ON "public"."yachts" IS 'Only managers can modify yacht settings';



CREATE POLICY "Managers can view agents" ON "public"."agents" FOR SELECT USING ((("yacht_id" = "public"."get_user_yacht_id"()) AND "public"."is_manager"()));



COMMENT ON POLICY "Managers can view agents" ON "public"."agents" IS 'Only managers can see local agents';



CREATE POLICY "Managers can view api keys" ON "public"."api_keys" FOR SELECT USING ((("yacht_id" = "public"."get_user_yacht_id"()) AND "public"."is_manager"()));



COMMENT ON POLICY "Managers can view api keys" ON "public"."api_keys" IS 'Only managers can see API keys';



CREATE POLICY "Managers can view embedding jobs" ON "public"."embedding_jobs" FOR SELECT USING ((("yacht_id" = "public"."get_user_yacht_id"()) AND "public"."is_manager"()));



COMMENT ON POLICY "Managers can view embedding jobs" ON "public"."embedding_jobs" IS 'Managers monitor indexing progress';



CREATE POLICY "System can create insights" ON "public"."predictive_insights" FOR INSERT WITH CHECK (("yacht_id" = "public"."get_user_yacht_id"()));



COMMENT ON POLICY "System can create insights" ON "public"."predictive_insights" IS 'Predictive engine generates insights';



CREATE POLICY "System can insert chunks" ON "public"."document_chunks" FOR INSERT WITH CHECK (("yacht_id" = "public"."get_user_yacht_id"()));



COMMENT ON POLICY "System can insert chunks" ON "public"."document_chunks" IS 'Indexing pipeline creates chunks';



CREATE POLICY "System can insert documents" ON "public"."documents" FOR INSERT WITH CHECK (("yacht_id" = "public"."get_user_yacht_id"()));



COMMENT ON POLICY "System can insert documents" ON "public"."documents" IS 'Local agent uploads documents';



CREATE POLICY "System can insert event logs" ON "public"."event_logs" FOR INSERT WITH CHECK (("yacht_id" = "public"."get_user_yacht_id"()));



COMMENT ON POLICY "System can insert event logs" ON "public"."event_logs" IS 'System records all events';



CREATE POLICY "System can manage embedding jobs" ON "public"."embedding_jobs" USING (("yacht_id" = "public"."get_user_yacht_id"()));



COMMENT ON POLICY "System can manage embedding jobs" ON "public"."embedding_jobs" IS 'Indexing pipeline tracks jobs';



CREATE POLICY "System can manage graph edges" ON "public"."graph_edges" USING (("yacht_id" = "public"."get_user_yacht_id"()));



COMMENT ON POLICY "System can manage graph edges" ON "public"."graph_edges" IS 'Indexing pipeline creates relationships';



CREATE POLICY "System can manage graph nodes" ON "public"."graph_nodes" USING (("yacht_id" = "public"."get_user_yacht_id"()));



COMMENT ON POLICY "System can manage graph nodes" ON "public"."graph_nodes" IS 'Indexing pipeline builds graph';



CREATE POLICY "System can manage ocred pages" ON "public"."ocred_pages" USING (("yacht_id" = "public"."get_user_yacht_id"()));



COMMENT ON POLICY "System can manage ocred pages" ON "public"."ocred_pages" IS 'Indexing pipeline manages OCR results';



CREATE POLICY "System can manage predictive state" ON "public"."predictive_state" USING (("yacht_id" = "public"."get_user_yacht_id"()));



COMMENT ON POLICY "System can manage predictive state" ON "public"."predictive_state" IS 'Predictive engine updates scores';



CREATE POLICY "Users can insert own hours of rest" ON "public"."hours_of_rest" FOR INSERT WITH CHECK ((("yacht_id" = "public"."get_user_yacht_id"()) AND ("user_id" = ( SELECT "users"."id"
   FROM "public"."users"
  WHERE ("users"."auth_user_id" = "auth"."uid"())))));



COMMENT ON POLICY "Users can insert own hours of rest" ON "public"."hours_of_rest" IS 'Users log their own hours';



CREATE POLICY "Users can insert search queries" ON "public"."search_queries" FOR INSERT WITH CHECK (("yacht_id" = "public"."get_user_yacht_id"()));



COMMENT ON POLICY "Users can insert search queries" ON "public"."search_queries" IS 'System logs all searches';



CREATE POLICY "Users can update own hours of rest" ON "public"."hours_of_rest" FOR UPDATE USING ((("yacht_id" = "public"."get_user_yacht_id"()) AND ("user_id" = ( SELECT "users"."id"
   FROM "public"."users"
  WHERE ("users"."auth_user_id" = "auth"."uid"())))));



COMMENT ON POLICY "Users can update own hours of rest" ON "public"."hours_of_rest" IS 'Users can edit their hours';



CREATE POLICY "Users can update own profile" ON "public"."users" FOR UPDATE USING (("auth_user_id" = "auth"."uid"())) WITH CHECK (("auth_user_id" = "auth"."uid"()));



COMMENT ON POLICY "Users can update own profile" ON "public"."users" IS 'Users can edit their own profile';



CREATE POLICY "Users can view PO items" ON "public"."purchase_order_items" FOR SELECT USING (("yacht_id" = "public"."get_user_yacht_id"()));



COMMENT ON POLICY "Users can view PO items" ON "public"."purchase_order_items" IS 'All crew see PO line items';



CREATE POLICY "Users can view document chunks" ON "public"."document_chunks" FOR SELECT USING (("yacht_id" = "public"."get_user_yacht_id"()));



COMMENT ON POLICY "Users can view document chunks" ON "public"."document_chunks" IS 'All crew can search documents';



CREATE POLICY "Users can view documents" ON "public"."documents" FOR SELECT USING (("yacht_id" = "public"."get_user_yacht_id"()));



COMMENT ON POLICY "Users can view documents" ON "public"."documents" IS 'All crew see documents';



CREATE POLICY "Users can view equipment parts" ON "public"."equipment_parts" FOR SELECT USING (("yacht_id" = "public"."get_user_yacht_id"()));



COMMENT ON POLICY "Users can view equipment parts" ON "public"."equipment_parts" IS 'All crew see part relationships';



CREATE POLICY "Users can view faults" ON "public"."faults" FOR SELECT USING (("yacht_id" = "public"."get_user_yacht_id"()));



COMMENT ON POLICY "Users can view faults" ON "public"."faults" IS 'All crew see faults';



CREATE POLICY "Users can view graph edges" ON "public"."graph_edges" FOR SELECT USING (("yacht_id" = "public"."get_user_yacht_id"()));



COMMENT ON POLICY "Users can view graph edges" ON "public"."graph_edges" IS 'All crew can use graph relationships';



CREATE POLICY "Users can view graph nodes" ON "public"."graph_nodes" FOR SELECT USING (("yacht_id" = "public"."get_user_yacht_id"()));



COMMENT ON POLICY "Users can view graph nodes" ON "public"."graph_nodes" IS 'All crew can traverse knowledge graph';



CREATE POLICY "Users can view handover items" ON "public"."handover_items" FOR SELECT USING (("yacht_id" = "public"."get_user_yacht_id"()));



COMMENT ON POLICY "Users can view handover items" ON "public"."handover_items" IS 'All crew see handover items';



CREATE POLICY "Users can view handovers" ON "public"."handovers" FOR SELECT USING (("yacht_id" = "public"."get_user_yacht_id"()));



COMMENT ON POLICY "Users can view handovers" ON "public"."handovers" IS 'All crew see handovers';



CREATE POLICY "Users can view insights" ON "public"."predictive_insights" FOR SELECT USING (("yacht_id" = "public"."get_user_yacht_id"()));



COMMENT ON POLICY "Users can view insights" ON "public"."predictive_insights" IS 'All crew see predictive insights';



CREATE POLICY "Users can view own hours of rest" ON "public"."hours_of_rest" FOR SELECT USING ((("yacht_id" = "public"."get_user_yacht_id"()) AND (("user_id" = ( SELECT "users"."id"
   FROM "public"."users"
  WHERE ("users"."auth_user_id" = "auth"."uid"()))) OR "public"."is_manager"())));



COMMENT ON POLICY "Users can view own hours of rest" ON "public"."hours_of_rest" IS 'Users see own hours, managers see all';



CREATE POLICY "Users can view own yacht" ON "public"."yachts" FOR SELECT USING (("id" = "public"."get_user_yacht_id"()));



COMMENT ON POLICY "Users can view own yacht" ON "public"."yachts" IS 'Users can only see their own yacht';



CREATE POLICY "Users can view parts" ON "public"."parts" FOR SELECT USING (("yacht_id" = "public"."get_user_yacht_id"()));



COMMENT ON POLICY "Users can view parts" ON "public"."parts" IS 'All crew can see parts catalog';



CREATE POLICY "Users can view predictive state" ON "public"."predictive_state" FOR SELECT USING (("yacht_id" = "public"."get_user_yacht_id"()));



COMMENT ON POLICY "Users can view predictive state" ON "public"."predictive_state" IS 'All crew see risk scores';



CREATE POLICY "Users can view purchase orders" ON "public"."purchase_orders" FOR SELECT USING (("yacht_id" = "public"."get_user_yacht_id"()));



COMMENT ON POLICY "Users can view purchase orders" ON "public"."purchase_orders" IS 'All crew see purchase orders';



CREATE POLICY "Users can view stock levels" ON "public"."inventory_stock" FOR SELECT USING (("yacht_id" = "public"."get_user_yacht_id"()));



COMMENT ON POLICY "Users can view stock levels" ON "public"."inventory_stock" IS 'All crew see stock levels';



CREATE POLICY "Users can view suppliers" ON "public"."suppliers" FOR SELECT USING (("yacht_id" = "public"."get_user_yacht_id"()));



COMMENT ON POLICY "Users can view suppliers" ON "public"."suppliers" IS 'All crew see supplier list';



CREATE POLICY "Users can view work order history" ON "public"."work_order_history" FOR SELECT USING (("yacht_id" = "public"."get_user_yacht_id"()));



COMMENT ON POLICY "Users can view work order history" ON "public"."work_order_history" IS 'All crew see work history';



CREATE POLICY "Users can view work orders" ON "public"."work_orders" FOR SELECT USING (("yacht_id" = "public"."get_user_yacht_id"()));



COMMENT ON POLICY "Users can view work orders" ON "public"."work_orders" IS 'All crew see work orders';



CREATE POLICY "Users can view yacht crew" ON "public"."users" FOR SELECT USING (("yacht_id" = "public"."get_user_yacht_id"()));



COMMENT ON POLICY "Users can view yacht crew" ON "public"."users" IS 'Users see all crew on their yacht';



CREATE POLICY "Users can view yacht equipment" ON "public"."equipment" FOR SELECT USING (("yacht_id" = "public"."get_user_yacht_id"()));



COMMENT ON POLICY "Users can view yacht equipment" ON "public"."equipment" IS 'All crew can see equipment';



CREATE POLICY "Users can view yacht event logs" ON "public"."event_logs" FOR SELECT USING (("yacht_id" = "public"."get_user_yacht_id"()));



COMMENT ON POLICY "Users can view yacht event logs" ON "public"."event_logs" IS 'Audit logs visible to all crew';



CREATE POLICY "Users can view yacht search queries" ON "public"."search_queries" FOR SELECT USING (("yacht_id" = "public"."get_user_yacht_id"()));



COMMENT ON POLICY "Users can view yacht search queries" ON "public"."search_queries" IS 'Users see search history for their yacht';



ALTER TABLE "public"."agents" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."api_keys" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."document_chunks" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."documents" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."embedding_jobs" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."equipment" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."equipment_parts" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."event_logs" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."faults" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."graph_edges" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."graph_nodes" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."handover_items" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."handovers" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."hours_of_rest" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."inventory_stock" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."ocred_pages" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."parts" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."predictive_insights" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."predictive_state" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."purchase_order_items" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."purchase_orders" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."search_queries" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."suppliers" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."user_roles" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."users" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."work_order_history" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."work_orders" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."yachts" ENABLE ROW LEVEL SECURITY;




ALTER PUBLICATION "supabase_realtime" OWNER TO "postgres";


GRANT USAGE ON SCHEMA "public" TO "postgres";
GRANT USAGE ON SCHEMA "public" TO "anon";
GRANT USAGE ON SCHEMA "public" TO "authenticated";
GRANT USAGE ON SCHEMA "public" TO "service_role";



GRANT ALL ON FUNCTION "public"."gtrgm_in"("cstring") TO "postgres";
GRANT ALL ON FUNCTION "public"."gtrgm_in"("cstring") TO "anon";
GRANT ALL ON FUNCTION "public"."gtrgm_in"("cstring") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gtrgm_in"("cstring") TO "service_role";



GRANT ALL ON FUNCTION "public"."gtrgm_out"("public"."gtrgm") TO "postgres";
GRANT ALL ON FUNCTION "public"."gtrgm_out"("public"."gtrgm") TO "anon";
GRANT ALL ON FUNCTION "public"."gtrgm_out"("public"."gtrgm") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gtrgm_out"("public"."gtrgm") TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_in"("cstring", "oid", integer) TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_in"("cstring", "oid", integer) TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_in"("cstring", "oid", integer) TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_in"("cstring", "oid", integer) TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_out"("public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_out"("public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_out"("public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_out"("public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_recv"("internal", "oid", integer) TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_recv"("internal", "oid", integer) TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_recv"("internal", "oid", integer) TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_recv"("internal", "oid", integer) TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_send"("public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_send"("public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_send"("public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_send"("public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_typmod_in"("cstring"[]) TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_typmod_in"("cstring"[]) TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_typmod_in"("cstring"[]) TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_typmod_in"("cstring"[]) TO "service_role";



GRANT ALL ON FUNCTION "public"."sparsevec_in"("cstring", "oid", integer) TO "postgres";
GRANT ALL ON FUNCTION "public"."sparsevec_in"("cstring", "oid", integer) TO "anon";
GRANT ALL ON FUNCTION "public"."sparsevec_in"("cstring", "oid", integer) TO "authenticated";
GRANT ALL ON FUNCTION "public"."sparsevec_in"("cstring", "oid", integer) TO "service_role";



GRANT ALL ON FUNCTION "public"."sparsevec_out"("public"."sparsevec") TO "postgres";
GRANT ALL ON FUNCTION "public"."sparsevec_out"("public"."sparsevec") TO "anon";
GRANT ALL ON FUNCTION "public"."sparsevec_out"("public"."sparsevec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."sparsevec_out"("public"."sparsevec") TO "service_role";



GRANT ALL ON FUNCTION "public"."sparsevec_recv"("internal", "oid", integer) TO "postgres";
GRANT ALL ON FUNCTION "public"."sparsevec_recv"("internal", "oid", integer) TO "anon";
GRANT ALL ON FUNCTION "public"."sparsevec_recv"("internal", "oid", integer) TO "authenticated";
GRANT ALL ON FUNCTION "public"."sparsevec_recv"("internal", "oid", integer) TO "service_role";



GRANT ALL ON FUNCTION "public"."sparsevec_send"("public"."sparsevec") TO "postgres";
GRANT ALL ON FUNCTION "public"."sparsevec_send"("public"."sparsevec") TO "anon";
GRANT ALL ON FUNCTION "public"."sparsevec_send"("public"."sparsevec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."sparsevec_send"("public"."sparsevec") TO "service_role";



GRANT ALL ON FUNCTION "public"."sparsevec_typmod_in"("cstring"[]) TO "postgres";
GRANT ALL ON FUNCTION "public"."sparsevec_typmod_in"("cstring"[]) TO "anon";
GRANT ALL ON FUNCTION "public"."sparsevec_typmod_in"("cstring"[]) TO "authenticated";
GRANT ALL ON FUNCTION "public"."sparsevec_typmod_in"("cstring"[]) TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_in"("cstring", "oid", integer) TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_in"("cstring", "oid", integer) TO "anon";
GRANT ALL ON FUNCTION "public"."vector_in"("cstring", "oid", integer) TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_in"("cstring", "oid", integer) TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_out"("public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_out"("public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."vector_out"("public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_out"("public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_recv"("internal", "oid", integer) TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_recv"("internal", "oid", integer) TO "anon";
GRANT ALL ON FUNCTION "public"."vector_recv"("internal", "oid", integer) TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_recv"("internal", "oid", integer) TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_send"("public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_send"("public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."vector_send"("public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_send"("public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_typmod_in"("cstring"[]) TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_typmod_in"("cstring"[]) TO "anon";
GRANT ALL ON FUNCTION "public"."vector_typmod_in"("cstring"[]) TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_typmod_in"("cstring"[]) TO "service_role";



GRANT ALL ON FUNCTION "public"."array_to_halfvec"(real[], integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."array_to_halfvec"(real[], integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."array_to_halfvec"(real[], integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."array_to_halfvec"(real[], integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."array_to_sparsevec"(real[], integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."array_to_sparsevec"(real[], integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."array_to_sparsevec"(real[], integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."array_to_sparsevec"(real[], integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."array_to_vector"(real[], integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."array_to_vector"(real[], integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."array_to_vector"(real[], integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."array_to_vector"(real[], integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."array_to_halfvec"(double precision[], integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."array_to_halfvec"(double precision[], integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."array_to_halfvec"(double precision[], integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."array_to_halfvec"(double precision[], integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."array_to_sparsevec"(double precision[], integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."array_to_sparsevec"(double precision[], integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."array_to_sparsevec"(double precision[], integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."array_to_sparsevec"(double precision[], integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."array_to_vector"(double precision[], integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."array_to_vector"(double precision[], integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."array_to_vector"(double precision[], integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."array_to_vector"(double precision[], integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."array_to_halfvec"(integer[], integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."array_to_halfvec"(integer[], integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."array_to_halfvec"(integer[], integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."array_to_halfvec"(integer[], integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."array_to_sparsevec"(integer[], integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."array_to_sparsevec"(integer[], integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."array_to_sparsevec"(integer[], integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."array_to_sparsevec"(integer[], integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."array_to_vector"(integer[], integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."array_to_vector"(integer[], integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."array_to_vector"(integer[], integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."array_to_vector"(integer[], integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."array_to_halfvec"(numeric[], integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."array_to_halfvec"(numeric[], integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."array_to_halfvec"(numeric[], integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."array_to_halfvec"(numeric[], integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."array_to_sparsevec"(numeric[], integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."array_to_sparsevec"(numeric[], integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."array_to_sparsevec"(numeric[], integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."array_to_sparsevec"(numeric[], integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."array_to_vector"(numeric[], integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."array_to_vector"(numeric[], integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."array_to_vector"(numeric[], integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."array_to_vector"(numeric[], integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_to_float4"("public"."halfvec", integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_to_float4"("public"."halfvec", integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_to_float4"("public"."halfvec", integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_to_float4"("public"."halfvec", integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec"("public"."halfvec", integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec"("public"."halfvec", integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec"("public"."halfvec", integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec"("public"."halfvec", integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_to_sparsevec"("public"."halfvec", integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_to_sparsevec"("public"."halfvec", integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_to_sparsevec"("public"."halfvec", integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_to_sparsevec"("public"."halfvec", integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_to_vector"("public"."halfvec", integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_to_vector"("public"."halfvec", integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_to_vector"("public"."halfvec", integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_to_vector"("public"."halfvec", integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."sparsevec_to_halfvec"("public"."sparsevec", integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."sparsevec_to_halfvec"("public"."sparsevec", integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."sparsevec_to_halfvec"("public"."sparsevec", integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."sparsevec_to_halfvec"("public"."sparsevec", integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."sparsevec"("public"."sparsevec", integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."sparsevec"("public"."sparsevec", integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."sparsevec"("public"."sparsevec", integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."sparsevec"("public"."sparsevec", integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."sparsevec_to_vector"("public"."sparsevec", integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."sparsevec_to_vector"("public"."sparsevec", integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."sparsevec_to_vector"("public"."sparsevec", integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."sparsevec_to_vector"("public"."sparsevec", integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_to_float4"("public"."vector", integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_to_float4"("public"."vector", integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."vector_to_float4"("public"."vector", integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_to_float4"("public"."vector", integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_to_halfvec"("public"."vector", integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_to_halfvec"("public"."vector", integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."vector_to_halfvec"("public"."vector", integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_to_halfvec"("public"."vector", integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_to_sparsevec"("public"."vector", integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_to_sparsevec"("public"."vector", integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."vector_to_sparsevec"("public"."vector", integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_to_sparsevec"("public"."vector", integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."vector"("public"."vector", integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."vector"("public"."vector", integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."vector"("public"."vector", integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector"("public"."vector", integer, boolean) TO "service_role";

























































































































































GRANT ALL ON FUNCTION "public"."binary_quantize"("public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."binary_quantize"("public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."binary_quantize"("public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."binary_quantize"("public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."binary_quantize"("public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."binary_quantize"("public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."binary_quantize"("public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."binary_quantize"("public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."cosine_distance"("public"."halfvec", "public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."cosine_distance"("public"."halfvec", "public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."cosine_distance"("public"."halfvec", "public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."cosine_distance"("public"."halfvec", "public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."cosine_distance"("public"."sparsevec", "public"."sparsevec") TO "postgres";
GRANT ALL ON FUNCTION "public"."cosine_distance"("public"."sparsevec", "public"."sparsevec") TO "anon";
GRANT ALL ON FUNCTION "public"."cosine_distance"("public"."sparsevec", "public"."sparsevec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."cosine_distance"("public"."sparsevec", "public"."sparsevec") TO "service_role";



GRANT ALL ON FUNCTION "public"."cosine_distance"("public"."vector", "public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."cosine_distance"("public"."vector", "public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."cosine_distance"("public"."vector", "public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."cosine_distance"("public"."vector", "public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."get_directory_depth_stats"("p_yacht_id" "text") TO "anon";
GRANT ALL ON FUNCTION "public"."get_directory_depth_stats"("p_yacht_id" "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."get_directory_depth_stats"("p_yacht_id" "text") TO "service_role";



GRANT ALL ON TABLE "public"."documents" TO "anon";
GRANT ALL ON TABLE "public"."documents" TO "authenticated";
GRANT ALL ON TABLE "public"."documents" TO "service_role";



GRANT ALL ON FUNCTION "public"."get_document_department"("doc" "public"."documents") TO "anon";
GRANT ALL ON FUNCTION "public"."get_document_department"("doc" "public"."documents") TO "authenticated";
GRANT ALL ON FUNCTION "public"."get_document_department"("doc" "public"."documents") TO "service_role";



GRANT ALL ON FUNCTION "public"."get_user_role"() TO "anon";
GRANT ALL ON FUNCTION "public"."get_user_role"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."get_user_role"() TO "service_role";



GRANT ALL ON FUNCTION "public"."get_user_yacht_id"() TO "anon";
GRANT ALL ON FUNCTION "public"."get_user_yacht_id"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."get_user_yacht_id"() TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_btree_consistent"("internal", smallint, "anyelement", integer, "internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_btree_consistent"("internal", smallint, "anyelement", integer, "internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_btree_consistent"("internal", smallint, "anyelement", integer, "internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_btree_consistent"("internal", smallint, "anyelement", integer, "internal", "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_compare_prefix_anyenum"("anyenum", "anyenum", smallint, "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_anyenum"("anyenum", "anyenum", smallint, "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_anyenum"("anyenum", "anyenum", smallint, "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_anyenum"("anyenum", "anyenum", smallint, "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_compare_prefix_bit"(bit, bit, smallint, "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_bit"(bit, bit, smallint, "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_bit"(bit, bit, smallint, "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_bit"(bit, bit, smallint, "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_compare_prefix_bool"(boolean, boolean, smallint, "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_bool"(boolean, boolean, smallint, "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_bool"(boolean, boolean, smallint, "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_bool"(boolean, boolean, smallint, "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_compare_prefix_bpchar"(character, character, smallint, "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_bpchar"(character, character, smallint, "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_bpchar"(character, character, smallint, "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_bpchar"(character, character, smallint, "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_compare_prefix_bytea"("bytea", "bytea", smallint, "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_bytea"("bytea", "bytea", smallint, "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_bytea"("bytea", "bytea", smallint, "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_bytea"("bytea", "bytea", smallint, "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_compare_prefix_char"("char", "char", smallint, "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_char"("char", "char", smallint, "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_char"("char", "char", smallint, "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_char"("char", "char", smallint, "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_compare_prefix_cidr"("cidr", "cidr", smallint, "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_cidr"("cidr", "cidr", smallint, "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_cidr"("cidr", "cidr", smallint, "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_cidr"("cidr", "cidr", smallint, "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_compare_prefix_date"("date", "date", smallint, "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_date"("date", "date", smallint, "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_date"("date", "date", smallint, "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_date"("date", "date", smallint, "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_compare_prefix_float4"(real, real, smallint, "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_float4"(real, real, smallint, "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_float4"(real, real, smallint, "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_float4"(real, real, smallint, "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_compare_prefix_float8"(double precision, double precision, smallint, "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_float8"(double precision, double precision, smallint, "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_float8"(double precision, double precision, smallint, "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_float8"(double precision, double precision, smallint, "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_compare_prefix_inet"("inet", "inet", smallint, "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_inet"("inet", "inet", smallint, "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_inet"("inet", "inet", smallint, "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_inet"("inet", "inet", smallint, "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_compare_prefix_int2"(smallint, smallint, smallint, "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_int2"(smallint, smallint, smallint, "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_int2"(smallint, smallint, smallint, "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_int2"(smallint, smallint, smallint, "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_compare_prefix_int4"(integer, integer, smallint, "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_int4"(integer, integer, smallint, "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_int4"(integer, integer, smallint, "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_int4"(integer, integer, smallint, "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_compare_prefix_int8"(bigint, bigint, smallint, "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_int8"(bigint, bigint, smallint, "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_int8"(bigint, bigint, smallint, "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_int8"(bigint, bigint, smallint, "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_compare_prefix_interval"(interval, interval, smallint, "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_interval"(interval, interval, smallint, "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_interval"(interval, interval, smallint, "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_interval"(interval, interval, smallint, "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_compare_prefix_macaddr"("macaddr", "macaddr", smallint, "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_macaddr"("macaddr", "macaddr", smallint, "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_macaddr"("macaddr", "macaddr", smallint, "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_macaddr"("macaddr", "macaddr", smallint, "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_compare_prefix_macaddr8"("macaddr8", "macaddr8", smallint, "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_macaddr8"("macaddr8", "macaddr8", smallint, "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_macaddr8"("macaddr8", "macaddr8", smallint, "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_macaddr8"("macaddr8", "macaddr8", smallint, "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_compare_prefix_money"("money", "money", smallint, "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_money"("money", "money", smallint, "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_money"("money", "money", smallint, "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_money"("money", "money", smallint, "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_compare_prefix_name"("name", "name", smallint, "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_name"("name", "name", smallint, "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_name"("name", "name", smallint, "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_name"("name", "name", smallint, "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_compare_prefix_numeric"(numeric, numeric, smallint, "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_numeric"(numeric, numeric, smallint, "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_numeric"(numeric, numeric, smallint, "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_numeric"(numeric, numeric, smallint, "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_compare_prefix_oid"("oid", "oid", smallint, "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_oid"("oid", "oid", smallint, "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_oid"("oid", "oid", smallint, "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_oid"("oid", "oid", smallint, "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_compare_prefix_text"("text", "text", smallint, "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_text"("text", "text", smallint, "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_text"("text", "text", smallint, "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_text"("text", "text", smallint, "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_compare_prefix_time"(time without time zone, time without time zone, smallint, "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_time"(time without time zone, time without time zone, smallint, "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_time"(time without time zone, time without time zone, smallint, "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_time"(time without time zone, time without time zone, smallint, "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_compare_prefix_timestamp"(timestamp without time zone, timestamp without time zone, smallint, "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_timestamp"(timestamp without time zone, timestamp without time zone, smallint, "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_timestamp"(timestamp without time zone, timestamp without time zone, smallint, "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_timestamp"(timestamp without time zone, timestamp without time zone, smallint, "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_compare_prefix_timestamptz"(timestamp with time zone, timestamp with time zone, smallint, "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_timestamptz"(timestamp with time zone, timestamp with time zone, smallint, "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_timestamptz"(timestamp with time zone, timestamp with time zone, smallint, "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_timestamptz"(timestamp with time zone, timestamp with time zone, smallint, "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_compare_prefix_timetz"(time with time zone, time with time zone, smallint, "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_timetz"(time with time zone, time with time zone, smallint, "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_timetz"(time with time zone, time with time zone, smallint, "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_timetz"(time with time zone, time with time zone, smallint, "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_compare_prefix_uuid"("uuid", "uuid", smallint, "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_uuid"("uuid", "uuid", smallint, "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_uuid"("uuid", "uuid", smallint, "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_uuid"("uuid", "uuid", smallint, "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_compare_prefix_varbit"(bit varying, bit varying, smallint, "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_varbit"(bit varying, bit varying, smallint, "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_varbit"(bit varying, bit varying, smallint, "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_compare_prefix_varbit"(bit varying, bit varying, smallint, "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_enum_cmp"("anyenum", "anyenum") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_enum_cmp"("anyenum", "anyenum") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_enum_cmp"("anyenum", "anyenum") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_enum_cmp"("anyenum", "anyenum") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_extract_query_anyenum"("anyenum", "internal", smallint, "internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_extract_query_anyenum"("anyenum", "internal", smallint, "internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_extract_query_anyenum"("anyenum", "internal", smallint, "internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_extract_query_anyenum"("anyenum", "internal", smallint, "internal", "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_extract_query_bit"(bit, "internal", smallint, "internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_extract_query_bit"(bit, "internal", smallint, "internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_extract_query_bit"(bit, "internal", smallint, "internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_extract_query_bit"(bit, "internal", smallint, "internal", "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_extract_query_bool"(boolean, "internal", smallint, "internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_extract_query_bool"(boolean, "internal", smallint, "internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_extract_query_bool"(boolean, "internal", smallint, "internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_extract_query_bool"(boolean, "internal", smallint, "internal", "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_extract_query_bpchar"(character, "internal", smallint, "internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_extract_query_bpchar"(character, "internal", smallint, "internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_extract_query_bpchar"(character, "internal", smallint, "internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_extract_query_bpchar"(character, "internal", smallint, "internal", "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_extract_query_bytea"("bytea", "internal", smallint, "internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_extract_query_bytea"("bytea", "internal", smallint, "internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_extract_query_bytea"("bytea", "internal", smallint, "internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_extract_query_bytea"("bytea", "internal", smallint, "internal", "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_extract_query_char"("char", "internal", smallint, "internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_extract_query_char"("char", "internal", smallint, "internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_extract_query_char"("char", "internal", smallint, "internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_extract_query_char"("char", "internal", smallint, "internal", "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_extract_query_cidr"("cidr", "internal", smallint, "internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_extract_query_cidr"("cidr", "internal", smallint, "internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_extract_query_cidr"("cidr", "internal", smallint, "internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_extract_query_cidr"("cidr", "internal", smallint, "internal", "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_extract_query_date"("date", "internal", smallint, "internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_extract_query_date"("date", "internal", smallint, "internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_extract_query_date"("date", "internal", smallint, "internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_extract_query_date"("date", "internal", smallint, "internal", "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_extract_query_float4"(real, "internal", smallint, "internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_extract_query_float4"(real, "internal", smallint, "internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_extract_query_float4"(real, "internal", smallint, "internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_extract_query_float4"(real, "internal", smallint, "internal", "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_extract_query_float8"(double precision, "internal", smallint, "internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_extract_query_float8"(double precision, "internal", smallint, "internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_extract_query_float8"(double precision, "internal", smallint, "internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_extract_query_float8"(double precision, "internal", smallint, "internal", "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_extract_query_inet"("inet", "internal", smallint, "internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_extract_query_inet"("inet", "internal", smallint, "internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_extract_query_inet"("inet", "internal", smallint, "internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_extract_query_inet"("inet", "internal", smallint, "internal", "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_extract_query_int2"(smallint, "internal", smallint, "internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_extract_query_int2"(smallint, "internal", smallint, "internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_extract_query_int2"(smallint, "internal", smallint, "internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_extract_query_int2"(smallint, "internal", smallint, "internal", "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_extract_query_int4"(integer, "internal", smallint, "internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_extract_query_int4"(integer, "internal", smallint, "internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_extract_query_int4"(integer, "internal", smallint, "internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_extract_query_int4"(integer, "internal", smallint, "internal", "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_extract_query_int8"(bigint, "internal", smallint, "internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_extract_query_int8"(bigint, "internal", smallint, "internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_extract_query_int8"(bigint, "internal", smallint, "internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_extract_query_int8"(bigint, "internal", smallint, "internal", "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_extract_query_interval"(interval, "internal", smallint, "internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_extract_query_interval"(interval, "internal", smallint, "internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_extract_query_interval"(interval, "internal", smallint, "internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_extract_query_interval"(interval, "internal", smallint, "internal", "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_extract_query_macaddr"("macaddr", "internal", smallint, "internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_extract_query_macaddr"("macaddr", "internal", smallint, "internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_extract_query_macaddr"("macaddr", "internal", smallint, "internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_extract_query_macaddr"("macaddr", "internal", smallint, "internal", "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_extract_query_macaddr8"("macaddr8", "internal", smallint, "internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_extract_query_macaddr8"("macaddr8", "internal", smallint, "internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_extract_query_macaddr8"("macaddr8", "internal", smallint, "internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_extract_query_macaddr8"("macaddr8", "internal", smallint, "internal", "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_extract_query_money"("money", "internal", smallint, "internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_extract_query_money"("money", "internal", smallint, "internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_extract_query_money"("money", "internal", smallint, "internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_extract_query_money"("money", "internal", smallint, "internal", "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_extract_query_name"("name", "internal", smallint, "internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_extract_query_name"("name", "internal", smallint, "internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_extract_query_name"("name", "internal", smallint, "internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_extract_query_name"("name", "internal", smallint, "internal", "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_extract_query_numeric"(numeric, "internal", smallint, "internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_extract_query_numeric"(numeric, "internal", smallint, "internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_extract_query_numeric"(numeric, "internal", smallint, "internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_extract_query_numeric"(numeric, "internal", smallint, "internal", "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_extract_query_oid"("oid", "internal", smallint, "internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_extract_query_oid"("oid", "internal", smallint, "internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_extract_query_oid"("oid", "internal", smallint, "internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_extract_query_oid"("oid", "internal", smallint, "internal", "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_extract_query_text"("text", "internal", smallint, "internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_extract_query_text"("text", "internal", smallint, "internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_extract_query_text"("text", "internal", smallint, "internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_extract_query_text"("text", "internal", smallint, "internal", "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_extract_query_time"(time without time zone, "internal", smallint, "internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_extract_query_time"(time without time zone, "internal", smallint, "internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_extract_query_time"(time without time zone, "internal", smallint, "internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_extract_query_time"(time without time zone, "internal", smallint, "internal", "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_extract_query_timestamp"(timestamp without time zone, "internal", smallint, "internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_extract_query_timestamp"(timestamp without time zone, "internal", smallint, "internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_extract_query_timestamp"(timestamp without time zone, "internal", smallint, "internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_extract_query_timestamp"(timestamp without time zone, "internal", smallint, "internal", "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_extract_query_timestamptz"(timestamp with time zone, "internal", smallint, "internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_extract_query_timestamptz"(timestamp with time zone, "internal", smallint, "internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_extract_query_timestamptz"(timestamp with time zone, "internal", smallint, "internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_extract_query_timestamptz"(timestamp with time zone, "internal", smallint, "internal", "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_extract_query_timetz"(time with time zone, "internal", smallint, "internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_extract_query_timetz"(time with time zone, "internal", smallint, "internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_extract_query_timetz"(time with time zone, "internal", smallint, "internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_extract_query_timetz"(time with time zone, "internal", smallint, "internal", "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_extract_query_trgm"("text", "internal", smallint, "internal", "internal", "internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_extract_query_trgm"("text", "internal", smallint, "internal", "internal", "internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_extract_query_trgm"("text", "internal", smallint, "internal", "internal", "internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_extract_query_trgm"("text", "internal", smallint, "internal", "internal", "internal", "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_extract_query_uuid"("uuid", "internal", smallint, "internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_extract_query_uuid"("uuid", "internal", smallint, "internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_extract_query_uuid"("uuid", "internal", smallint, "internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_extract_query_uuid"("uuid", "internal", smallint, "internal", "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_extract_query_varbit"(bit varying, "internal", smallint, "internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_extract_query_varbit"(bit varying, "internal", smallint, "internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_extract_query_varbit"(bit varying, "internal", smallint, "internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_extract_query_varbit"(bit varying, "internal", smallint, "internal", "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_extract_value_anyenum"("anyenum", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_extract_value_anyenum"("anyenum", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_extract_value_anyenum"("anyenum", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_extract_value_anyenum"("anyenum", "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_extract_value_bit"(bit, "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_extract_value_bit"(bit, "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_extract_value_bit"(bit, "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_extract_value_bit"(bit, "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_extract_value_bool"(boolean, "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_extract_value_bool"(boolean, "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_extract_value_bool"(boolean, "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_extract_value_bool"(boolean, "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_extract_value_bpchar"(character, "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_extract_value_bpchar"(character, "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_extract_value_bpchar"(character, "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_extract_value_bpchar"(character, "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_extract_value_bytea"("bytea", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_extract_value_bytea"("bytea", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_extract_value_bytea"("bytea", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_extract_value_bytea"("bytea", "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_extract_value_char"("char", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_extract_value_char"("char", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_extract_value_char"("char", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_extract_value_char"("char", "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_extract_value_cidr"("cidr", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_extract_value_cidr"("cidr", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_extract_value_cidr"("cidr", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_extract_value_cidr"("cidr", "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_extract_value_date"("date", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_extract_value_date"("date", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_extract_value_date"("date", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_extract_value_date"("date", "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_extract_value_float4"(real, "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_extract_value_float4"(real, "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_extract_value_float4"(real, "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_extract_value_float4"(real, "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_extract_value_float8"(double precision, "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_extract_value_float8"(double precision, "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_extract_value_float8"(double precision, "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_extract_value_float8"(double precision, "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_extract_value_inet"("inet", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_extract_value_inet"("inet", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_extract_value_inet"("inet", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_extract_value_inet"("inet", "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_extract_value_int2"(smallint, "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_extract_value_int2"(smallint, "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_extract_value_int2"(smallint, "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_extract_value_int2"(smallint, "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_extract_value_int4"(integer, "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_extract_value_int4"(integer, "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_extract_value_int4"(integer, "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_extract_value_int4"(integer, "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_extract_value_int8"(bigint, "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_extract_value_int8"(bigint, "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_extract_value_int8"(bigint, "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_extract_value_int8"(bigint, "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_extract_value_interval"(interval, "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_extract_value_interval"(interval, "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_extract_value_interval"(interval, "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_extract_value_interval"(interval, "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_extract_value_macaddr"("macaddr", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_extract_value_macaddr"("macaddr", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_extract_value_macaddr"("macaddr", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_extract_value_macaddr"("macaddr", "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_extract_value_macaddr8"("macaddr8", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_extract_value_macaddr8"("macaddr8", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_extract_value_macaddr8"("macaddr8", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_extract_value_macaddr8"("macaddr8", "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_extract_value_money"("money", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_extract_value_money"("money", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_extract_value_money"("money", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_extract_value_money"("money", "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_extract_value_name"("name", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_extract_value_name"("name", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_extract_value_name"("name", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_extract_value_name"("name", "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_extract_value_numeric"(numeric, "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_extract_value_numeric"(numeric, "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_extract_value_numeric"(numeric, "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_extract_value_numeric"(numeric, "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_extract_value_oid"("oid", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_extract_value_oid"("oid", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_extract_value_oid"("oid", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_extract_value_oid"("oid", "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_extract_value_text"("text", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_extract_value_text"("text", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_extract_value_text"("text", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_extract_value_text"("text", "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_extract_value_time"(time without time zone, "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_extract_value_time"(time without time zone, "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_extract_value_time"(time without time zone, "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_extract_value_time"(time without time zone, "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_extract_value_timestamp"(timestamp without time zone, "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_extract_value_timestamp"(timestamp without time zone, "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_extract_value_timestamp"(timestamp without time zone, "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_extract_value_timestamp"(timestamp without time zone, "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_extract_value_timestamptz"(timestamp with time zone, "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_extract_value_timestamptz"(timestamp with time zone, "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_extract_value_timestamptz"(timestamp with time zone, "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_extract_value_timestamptz"(timestamp with time zone, "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_extract_value_timetz"(time with time zone, "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_extract_value_timetz"(time with time zone, "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_extract_value_timetz"(time with time zone, "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_extract_value_timetz"(time with time zone, "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_extract_value_trgm"("text", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_extract_value_trgm"("text", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_extract_value_trgm"("text", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_extract_value_trgm"("text", "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_extract_value_uuid"("uuid", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_extract_value_uuid"("uuid", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_extract_value_uuid"("uuid", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_extract_value_uuid"("uuid", "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_extract_value_varbit"(bit varying, "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_extract_value_varbit"(bit varying, "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_extract_value_varbit"(bit varying, "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_extract_value_varbit"(bit varying, "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_numeric_cmp"(numeric, numeric) TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_numeric_cmp"(numeric, numeric) TO "anon";
GRANT ALL ON FUNCTION "public"."gin_numeric_cmp"(numeric, numeric) TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_numeric_cmp"(numeric, numeric) TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_trgm_consistent"("internal", smallint, "text", integer, "internal", "internal", "internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_trgm_consistent"("internal", smallint, "text", integer, "internal", "internal", "internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_trgm_consistent"("internal", smallint, "text", integer, "internal", "internal", "internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_trgm_consistent"("internal", smallint, "text", integer, "internal", "internal", "internal", "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_trgm_triconsistent"("internal", smallint, "text", integer, "internal", "internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_trgm_triconsistent"("internal", smallint, "text", integer, "internal", "internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_trgm_triconsistent"("internal", smallint, "text", integer, "internal", "internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_trgm_triconsistent"("internal", smallint, "text", integer, "internal", "internal", "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gtrgm_compress"("internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gtrgm_compress"("internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gtrgm_compress"("internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gtrgm_compress"("internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gtrgm_consistent"("internal", "text", smallint, "oid", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gtrgm_consistent"("internal", "text", smallint, "oid", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gtrgm_consistent"("internal", "text", smallint, "oid", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gtrgm_consistent"("internal", "text", smallint, "oid", "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gtrgm_decompress"("internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gtrgm_decompress"("internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gtrgm_decompress"("internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gtrgm_decompress"("internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gtrgm_distance"("internal", "text", smallint, "oid", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gtrgm_distance"("internal", "text", smallint, "oid", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gtrgm_distance"("internal", "text", smallint, "oid", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gtrgm_distance"("internal", "text", smallint, "oid", "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gtrgm_options"("internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gtrgm_options"("internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gtrgm_options"("internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gtrgm_options"("internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gtrgm_penalty"("internal", "internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gtrgm_penalty"("internal", "internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gtrgm_penalty"("internal", "internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gtrgm_penalty"("internal", "internal", "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gtrgm_picksplit"("internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gtrgm_picksplit"("internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gtrgm_picksplit"("internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gtrgm_picksplit"("internal", "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gtrgm_same"("public"."gtrgm", "public"."gtrgm", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gtrgm_same"("public"."gtrgm", "public"."gtrgm", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gtrgm_same"("public"."gtrgm", "public"."gtrgm", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gtrgm_same"("public"."gtrgm", "public"."gtrgm", "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gtrgm_union"("internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gtrgm_union"("internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gtrgm_union"("internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gtrgm_union"("internal", "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_accum"(double precision[], "public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_accum"(double precision[], "public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_accum"(double precision[], "public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_accum"(double precision[], "public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_add"("public"."halfvec", "public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_add"("public"."halfvec", "public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_add"("public"."halfvec", "public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_add"("public"."halfvec", "public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_avg"(double precision[]) TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_avg"(double precision[]) TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_avg"(double precision[]) TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_avg"(double precision[]) TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_cmp"("public"."halfvec", "public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_cmp"("public"."halfvec", "public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_cmp"("public"."halfvec", "public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_cmp"("public"."halfvec", "public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_combine"(double precision[], double precision[]) TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_combine"(double precision[], double precision[]) TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_combine"(double precision[], double precision[]) TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_combine"(double precision[], double precision[]) TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_concat"("public"."halfvec", "public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_concat"("public"."halfvec", "public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_concat"("public"."halfvec", "public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_concat"("public"."halfvec", "public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_eq"("public"."halfvec", "public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_eq"("public"."halfvec", "public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_eq"("public"."halfvec", "public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_eq"("public"."halfvec", "public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_ge"("public"."halfvec", "public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_ge"("public"."halfvec", "public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_ge"("public"."halfvec", "public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_ge"("public"."halfvec", "public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_gt"("public"."halfvec", "public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_gt"("public"."halfvec", "public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_gt"("public"."halfvec", "public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_gt"("public"."halfvec", "public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_l2_squared_distance"("public"."halfvec", "public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_l2_squared_distance"("public"."halfvec", "public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_l2_squared_distance"("public"."halfvec", "public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_l2_squared_distance"("public"."halfvec", "public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_le"("public"."halfvec", "public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_le"("public"."halfvec", "public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_le"("public"."halfvec", "public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_le"("public"."halfvec", "public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_lt"("public"."halfvec", "public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_lt"("public"."halfvec", "public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_lt"("public"."halfvec", "public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_lt"("public"."halfvec", "public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_mul"("public"."halfvec", "public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_mul"("public"."halfvec", "public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_mul"("public"."halfvec", "public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_mul"("public"."halfvec", "public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_ne"("public"."halfvec", "public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_ne"("public"."halfvec", "public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_ne"("public"."halfvec", "public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_ne"("public"."halfvec", "public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_negative_inner_product"("public"."halfvec", "public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_negative_inner_product"("public"."halfvec", "public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_negative_inner_product"("public"."halfvec", "public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_negative_inner_product"("public"."halfvec", "public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_spherical_distance"("public"."halfvec", "public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_spherical_distance"("public"."halfvec", "public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_spherical_distance"("public"."halfvec", "public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_spherical_distance"("public"."halfvec", "public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_sub"("public"."halfvec", "public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_sub"("public"."halfvec", "public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_sub"("public"."halfvec", "public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_sub"("public"."halfvec", "public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."hamming_distance"(bit, bit) TO "postgres";
GRANT ALL ON FUNCTION "public"."hamming_distance"(bit, bit) TO "anon";
GRANT ALL ON FUNCTION "public"."hamming_distance"(bit, bit) TO "authenticated";
GRANT ALL ON FUNCTION "public"."hamming_distance"(bit, bit) TO "service_role";



GRANT ALL ON FUNCTION "public"."handle_new_user"() TO "anon";
GRANT ALL ON FUNCTION "public"."handle_new_user"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."handle_new_user"() TO "service_role";



GRANT ALL ON FUNCTION "public"."hnsw_bit_support"("internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."hnsw_bit_support"("internal") TO "anon";
GRANT ALL ON FUNCTION "public"."hnsw_bit_support"("internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."hnsw_bit_support"("internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."hnsw_halfvec_support"("internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."hnsw_halfvec_support"("internal") TO "anon";
GRANT ALL ON FUNCTION "public"."hnsw_halfvec_support"("internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."hnsw_halfvec_support"("internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."hnsw_sparsevec_support"("internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."hnsw_sparsevec_support"("internal") TO "anon";
GRANT ALL ON FUNCTION "public"."hnsw_sparsevec_support"("internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."hnsw_sparsevec_support"("internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."hnswhandler"("internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."hnswhandler"("internal") TO "anon";
GRANT ALL ON FUNCTION "public"."hnswhandler"("internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."hnswhandler"("internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."inner_product"("public"."halfvec", "public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."inner_product"("public"."halfvec", "public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."inner_product"("public"."halfvec", "public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."inner_product"("public"."halfvec", "public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."inner_product"("public"."sparsevec", "public"."sparsevec") TO "postgres";
GRANT ALL ON FUNCTION "public"."inner_product"("public"."sparsevec", "public"."sparsevec") TO "anon";
GRANT ALL ON FUNCTION "public"."inner_product"("public"."sparsevec", "public"."sparsevec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."inner_product"("public"."sparsevec", "public"."sparsevec") TO "service_role";



GRANT ALL ON FUNCTION "public"."inner_product"("public"."vector", "public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."inner_product"("public"."vector", "public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."inner_product"("public"."vector", "public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."inner_product"("public"."vector", "public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."is_manager"() TO "anon";
GRANT ALL ON FUNCTION "public"."is_manager"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."is_manager"() TO "service_role";



GRANT ALL ON FUNCTION "public"."ivfflat_bit_support"("internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."ivfflat_bit_support"("internal") TO "anon";
GRANT ALL ON FUNCTION "public"."ivfflat_bit_support"("internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."ivfflat_bit_support"("internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."ivfflat_halfvec_support"("internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."ivfflat_halfvec_support"("internal") TO "anon";
GRANT ALL ON FUNCTION "public"."ivfflat_halfvec_support"("internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."ivfflat_halfvec_support"("internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."ivfflathandler"("internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."ivfflathandler"("internal") TO "anon";
GRANT ALL ON FUNCTION "public"."ivfflathandler"("internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."ivfflathandler"("internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."jaccard_distance"(bit, bit) TO "postgres";
GRANT ALL ON FUNCTION "public"."jaccard_distance"(bit, bit) TO "anon";
GRANT ALL ON FUNCTION "public"."jaccard_distance"(bit, bit) TO "authenticated";
GRANT ALL ON FUNCTION "public"."jaccard_distance"(bit, bit) TO "service_role";



GRANT ALL ON FUNCTION "public"."l1_distance"("public"."halfvec", "public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."l1_distance"("public"."halfvec", "public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."l1_distance"("public"."halfvec", "public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."l1_distance"("public"."halfvec", "public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."l1_distance"("public"."sparsevec", "public"."sparsevec") TO "postgres";
GRANT ALL ON FUNCTION "public"."l1_distance"("public"."sparsevec", "public"."sparsevec") TO "anon";
GRANT ALL ON FUNCTION "public"."l1_distance"("public"."sparsevec", "public"."sparsevec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."l1_distance"("public"."sparsevec", "public"."sparsevec") TO "service_role";



GRANT ALL ON FUNCTION "public"."l1_distance"("public"."vector", "public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."l1_distance"("public"."vector", "public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."l1_distance"("public"."vector", "public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."l1_distance"("public"."vector", "public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."l2_distance"("public"."halfvec", "public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."l2_distance"("public"."halfvec", "public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."l2_distance"("public"."halfvec", "public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."l2_distance"("public"."halfvec", "public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."l2_distance"("public"."sparsevec", "public"."sparsevec") TO "postgres";
GRANT ALL ON FUNCTION "public"."l2_distance"("public"."sparsevec", "public"."sparsevec") TO "anon";
GRANT ALL ON FUNCTION "public"."l2_distance"("public"."sparsevec", "public"."sparsevec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."l2_distance"("public"."sparsevec", "public"."sparsevec") TO "service_role";



GRANT ALL ON FUNCTION "public"."l2_distance"("public"."vector", "public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."l2_distance"("public"."vector", "public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."l2_distance"("public"."vector", "public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."l2_distance"("public"."vector", "public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."l2_norm"("public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."l2_norm"("public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."l2_norm"("public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."l2_norm"("public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."l2_norm"("public"."sparsevec") TO "postgres";
GRANT ALL ON FUNCTION "public"."l2_norm"("public"."sparsevec") TO "anon";
GRANT ALL ON FUNCTION "public"."l2_norm"("public"."sparsevec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."l2_norm"("public"."sparsevec") TO "service_role";



GRANT ALL ON FUNCTION "public"."l2_normalize"("public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."l2_normalize"("public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."l2_normalize"("public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."l2_normalize"("public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."l2_normalize"("public"."sparsevec") TO "postgres";
GRANT ALL ON FUNCTION "public"."l2_normalize"("public"."sparsevec") TO "anon";
GRANT ALL ON FUNCTION "public"."l2_normalize"("public"."sparsevec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."l2_normalize"("public"."sparsevec") TO "service_role";



GRANT ALL ON FUNCTION "public"."l2_normalize"("public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."l2_normalize"("public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."l2_normalize"("public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."l2_normalize"("public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."search_documents_by_directory"("p_yacht_id" "text", "p_directory_prefix" "text") TO "anon";
GRANT ALL ON FUNCTION "public"."search_documents_by_directory"("p_yacht_id" "text", "p_directory_prefix" "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."search_documents_by_directory"("p_yacht_id" "text", "p_directory_prefix" "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."set_limit"(real) TO "postgres";
GRANT ALL ON FUNCTION "public"."set_limit"(real) TO "anon";
GRANT ALL ON FUNCTION "public"."set_limit"(real) TO "authenticated";
GRANT ALL ON FUNCTION "public"."set_limit"(real) TO "service_role";



GRANT ALL ON FUNCTION "public"."show_limit"() TO "postgres";
GRANT ALL ON FUNCTION "public"."show_limit"() TO "anon";
GRANT ALL ON FUNCTION "public"."show_limit"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."show_limit"() TO "service_role";



GRANT ALL ON FUNCTION "public"."show_trgm"("text") TO "postgres";
GRANT ALL ON FUNCTION "public"."show_trgm"("text") TO "anon";
GRANT ALL ON FUNCTION "public"."show_trgm"("text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."show_trgm"("text") TO "service_role";



GRANT ALL ON FUNCTION "public"."similarity"("text", "text") TO "postgres";
GRANT ALL ON FUNCTION "public"."similarity"("text", "text") TO "anon";
GRANT ALL ON FUNCTION "public"."similarity"("text", "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."similarity"("text", "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."similarity_dist"("text", "text") TO "postgres";
GRANT ALL ON FUNCTION "public"."similarity_dist"("text", "text") TO "anon";
GRANT ALL ON FUNCTION "public"."similarity_dist"("text", "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."similarity_dist"("text", "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."similarity_op"("text", "text") TO "postgres";
GRANT ALL ON FUNCTION "public"."similarity_op"("text", "text") TO "anon";
GRANT ALL ON FUNCTION "public"."similarity_op"("text", "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."similarity_op"("text", "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."sparsevec_cmp"("public"."sparsevec", "public"."sparsevec") TO "postgres";
GRANT ALL ON FUNCTION "public"."sparsevec_cmp"("public"."sparsevec", "public"."sparsevec") TO "anon";
GRANT ALL ON FUNCTION "public"."sparsevec_cmp"("public"."sparsevec", "public"."sparsevec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."sparsevec_cmp"("public"."sparsevec", "public"."sparsevec") TO "service_role";



GRANT ALL ON FUNCTION "public"."sparsevec_eq"("public"."sparsevec", "public"."sparsevec") TO "postgres";
GRANT ALL ON FUNCTION "public"."sparsevec_eq"("public"."sparsevec", "public"."sparsevec") TO "anon";
GRANT ALL ON FUNCTION "public"."sparsevec_eq"("public"."sparsevec", "public"."sparsevec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."sparsevec_eq"("public"."sparsevec", "public"."sparsevec") TO "service_role";



GRANT ALL ON FUNCTION "public"."sparsevec_ge"("public"."sparsevec", "public"."sparsevec") TO "postgres";
GRANT ALL ON FUNCTION "public"."sparsevec_ge"("public"."sparsevec", "public"."sparsevec") TO "anon";
GRANT ALL ON FUNCTION "public"."sparsevec_ge"("public"."sparsevec", "public"."sparsevec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."sparsevec_ge"("public"."sparsevec", "public"."sparsevec") TO "service_role";



GRANT ALL ON FUNCTION "public"."sparsevec_gt"("public"."sparsevec", "public"."sparsevec") TO "postgres";
GRANT ALL ON FUNCTION "public"."sparsevec_gt"("public"."sparsevec", "public"."sparsevec") TO "anon";
GRANT ALL ON FUNCTION "public"."sparsevec_gt"("public"."sparsevec", "public"."sparsevec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."sparsevec_gt"("public"."sparsevec", "public"."sparsevec") TO "service_role";



GRANT ALL ON FUNCTION "public"."sparsevec_l2_squared_distance"("public"."sparsevec", "public"."sparsevec") TO "postgres";
GRANT ALL ON FUNCTION "public"."sparsevec_l2_squared_distance"("public"."sparsevec", "public"."sparsevec") TO "anon";
GRANT ALL ON FUNCTION "public"."sparsevec_l2_squared_distance"("public"."sparsevec", "public"."sparsevec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."sparsevec_l2_squared_distance"("public"."sparsevec", "public"."sparsevec") TO "service_role";



GRANT ALL ON FUNCTION "public"."sparsevec_le"("public"."sparsevec", "public"."sparsevec") TO "postgres";
GRANT ALL ON FUNCTION "public"."sparsevec_le"("public"."sparsevec", "public"."sparsevec") TO "anon";
GRANT ALL ON FUNCTION "public"."sparsevec_le"("public"."sparsevec", "public"."sparsevec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."sparsevec_le"("public"."sparsevec", "public"."sparsevec") TO "service_role";



GRANT ALL ON FUNCTION "public"."sparsevec_lt"("public"."sparsevec", "public"."sparsevec") TO "postgres";
GRANT ALL ON FUNCTION "public"."sparsevec_lt"("public"."sparsevec", "public"."sparsevec") TO "anon";
GRANT ALL ON FUNCTION "public"."sparsevec_lt"("public"."sparsevec", "public"."sparsevec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."sparsevec_lt"("public"."sparsevec", "public"."sparsevec") TO "service_role";



GRANT ALL ON FUNCTION "public"."sparsevec_ne"("public"."sparsevec", "public"."sparsevec") TO "postgres";
GRANT ALL ON FUNCTION "public"."sparsevec_ne"("public"."sparsevec", "public"."sparsevec") TO "anon";
GRANT ALL ON FUNCTION "public"."sparsevec_ne"("public"."sparsevec", "public"."sparsevec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."sparsevec_ne"("public"."sparsevec", "public"."sparsevec") TO "service_role";



GRANT ALL ON FUNCTION "public"."sparsevec_negative_inner_product"("public"."sparsevec", "public"."sparsevec") TO "postgres";
GRANT ALL ON FUNCTION "public"."sparsevec_negative_inner_product"("public"."sparsevec", "public"."sparsevec") TO "anon";
GRANT ALL ON FUNCTION "public"."sparsevec_negative_inner_product"("public"."sparsevec", "public"."sparsevec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."sparsevec_negative_inner_product"("public"."sparsevec", "public"."sparsevec") TO "service_role";



GRANT ALL ON FUNCTION "public"."strict_word_similarity"("text", "text") TO "postgres";
GRANT ALL ON FUNCTION "public"."strict_word_similarity"("text", "text") TO "anon";
GRANT ALL ON FUNCTION "public"."strict_word_similarity"("text", "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."strict_word_similarity"("text", "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."strict_word_similarity_commutator_op"("text", "text") TO "postgres";
GRANT ALL ON FUNCTION "public"."strict_word_similarity_commutator_op"("text", "text") TO "anon";
GRANT ALL ON FUNCTION "public"."strict_word_similarity_commutator_op"("text", "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."strict_word_similarity_commutator_op"("text", "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."strict_word_similarity_dist_commutator_op"("text", "text") TO "postgres";
GRANT ALL ON FUNCTION "public"."strict_word_similarity_dist_commutator_op"("text", "text") TO "anon";
GRANT ALL ON FUNCTION "public"."strict_word_similarity_dist_commutator_op"("text", "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."strict_word_similarity_dist_commutator_op"("text", "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."strict_word_similarity_dist_op"("text", "text") TO "postgres";
GRANT ALL ON FUNCTION "public"."strict_word_similarity_dist_op"("text", "text") TO "anon";
GRANT ALL ON FUNCTION "public"."strict_word_similarity_dist_op"("text", "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."strict_word_similarity_dist_op"("text", "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."strict_word_similarity_op"("text", "text") TO "postgres";
GRANT ALL ON FUNCTION "public"."strict_word_similarity_op"("text", "text") TO "anon";
GRANT ALL ON FUNCTION "public"."strict_word_similarity_op"("text", "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."strict_word_similarity_op"("text", "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."subvector"("public"."halfvec", integer, integer) TO "postgres";
GRANT ALL ON FUNCTION "public"."subvector"("public"."halfvec", integer, integer) TO "anon";
GRANT ALL ON FUNCTION "public"."subvector"("public"."halfvec", integer, integer) TO "authenticated";
GRANT ALL ON FUNCTION "public"."subvector"("public"."halfvec", integer, integer) TO "service_role";



GRANT ALL ON FUNCTION "public"."subvector"("public"."vector", integer, integer) TO "postgres";
GRANT ALL ON FUNCTION "public"."subvector"("public"."vector", integer, integer) TO "anon";
GRANT ALL ON FUNCTION "public"."subvector"("public"."vector", integer, integer) TO "authenticated";
GRANT ALL ON FUNCTION "public"."subvector"("public"."vector", integer, integer) TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_accum"(double precision[], "public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_accum"(double precision[], "public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."vector_accum"(double precision[], "public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_accum"(double precision[], "public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_add"("public"."vector", "public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_add"("public"."vector", "public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."vector_add"("public"."vector", "public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_add"("public"."vector", "public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_avg"(double precision[]) TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_avg"(double precision[]) TO "anon";
GRANT ALL ON FUNCTION "public"."vector_avg"(double precision[]) TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_avg"(double precision[]) TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_cmp"("public"."vector", "public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_cmp"("public"."vector", "public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."vector_cmp"("public"."vector", "public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_cmp"("public"."vector", "public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_combine"(double precision[], double precision[]) TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_combine"(double precision[], double precision[]) TO "anon";
GRANT ALL ON FUNCTION "public"."vector_combine"(double precision[], double precision[]) TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_combine"(double precision[], double precision[]) TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_concat"("public"."vector", "public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_concat"("public"."vector", "public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."vector_concat"("public"."vector", "public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_concat"("public"."vector", "public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_dims"("public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_dims"("public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."vector_dims"("public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_dims"("public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_dims"("public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_dims"("public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."vector_dims"("public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_dims"("public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_eq"("public"."vector", "public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_eq"("public"."vector", "public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."vector_eq"("public"."vector", "public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_eq"("public"."vector", "public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_ge"("public"."vector", "public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_ge"("public"."vector", "public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."vector_ge"("public"."vector", "public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_ge"("public"."vector", "public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_gt"("public"."vector", "public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_gt"("public"."vector", "public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."vector_gt"("public"."vector", "public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_gt"("public"."vector", "public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_l2_squared_distance"("public"."vector", "public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_l2_squared_distance"("public"."vector", "public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."vector_l2_squared_distance"("public"."vector", "public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_l2_squared_distance"("public"."vector", "public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_le"("public"."vector", "public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_le"("public"."vector", "public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."vector_le"("public"."vector", "public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_le"("public"."vector", "public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_lt"("public"."vector", "public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_lt"("public"."vector", "public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."vector_lt"("public"."vector", "public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_lt"("public"."vector", "public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_mul"("public"."vector", "public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_mul"("public"."vector", "public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."vector_mul"("public"."vector", "public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_mul"("public"."vector", "public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_ne"("public"."vector", "public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_ne"("public"."vector", "public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."vector_ne"("public"."vector", "public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_ne"("public"."vector", "public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_negative_inner_product"("public"."vector", "public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_negative_inner_product"("public"."vector", "public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."vector_negative_inner_product"("public"."vector", "public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_negative_inner_product"("public"."vector", "public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_norm"("public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_norm"("public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."vector_norm"("public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_norm"("public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_spherical_distance"("public"."vector", "public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_spherical_distance"("public"."vector", "public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."vector_spherical_distance"("public"."vector", "public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_spherical_distance"("public"."vector", "public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_sub"("public"."vector", "public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_sub"("public"."vector", "public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."vector_sub"("public"."vector", "public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_sub"("public"."vector", "public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."word_similarity"("text", "text") TO "postgres";
GRANT ALL ON FUNCTION "public"."word_similarity"("text", "text") TO "anon";
GRANT ALL ON FUNCTION "public"."word_similarity"("text", "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."word_similarity"("text", "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."word_similarity_commutator_op"("text", "text") TO "postgres";
GRANT ALL ON FUNCTION "public"."word_similarity_commutator_op"("text", "text") TO "anon";
GRANT ALL ON FUNCTION "public"."word_similarity_commutator_op"("text", "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."word_similarity_commutator_op"("text", "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."word_similarity_dist_commutator_op"("text", "text") TO "postgres";
GRANT ALL ON FUNCTION "public"."word_similarity_dist_commutator_op"("text", "text") TO "anon";
GRANT ALL ON FUNCTION "public"."word_similarity_dist_commutator_op"("text", "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."word_similarity_dist_commutator_op"("text", "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."word_similarity_dist_op"("text", "text") TO "postgres";
GRANT ALL ON FUNCTION "public"."word_similarity_dist_op"("text", "text") TO "anon";
GRANT ALL ON FUNCTION "public"."word_similarity_dist_op"("text", "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."word_similarity_dist_op"("text", "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."word_similarity_op"("text", "text") TO "postgres";
GRANT ALL ON FUNCTION "public"."word_similarity_op"("text", "text") TO "anon";
GRANT ALL ON FUNCTION "public"."word_similarity_op"("text", "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."word_similarity_op"("text", "text") TO "service_role";












GRANT ALL ON FUNCTION "public"."avg"("public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."avg"("public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."avg"("public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."avg"("public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."avg"("public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."avg"("public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."avg"("public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."avg"("public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."sum"("public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."sum"("public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."sum"("public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."sum"("public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."sum"("public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."sum"("public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."sum"("public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."sum"("public"."vector") TO "service_role";









GRANT ALL ON TABLE "public"."agents" TO "anon";
GRANT ALL ON TABLE "public"."agents" TO "authenticated";
GRANT ALL ON TABLE "public"."agents" TO "service_role";



GRANT ALL ON TABLE "public"."api_keys" TO "anon";
GRANT ALL ON TABLE "public"."api_keys" TO "authenticated";
GRANT ALL ON TABLE "public"."api_keys" TO "service_role";



GRANT ALL ON TABLE "public"."document_chunks" TO "anon";
GRANT ALL ON TABLE "public"."document_chunks" TO "authenticated";
GRANT ALL ON TABLE "public"."document_chunks" TO "service_role";



GRANT ALL ON TABLE "public"."document_counts_by_department" TO "anon";
GRANT ALL ON TABLE "public"."document_counts_by_department" TO "authenticated";
GRANT ALL ON TABLE "public"."document_counts_by_department" TO "service_role";



GRANT ALL ON TABLE "public"."document_directory_tree" TO "anon";
GRANT ALL ON TABLE "public"."document_directory_tree" TO "authenticated";
GRANT ALL ON TABLE "public"."document_directory_tree" TO "service_role";



GRANT ALL ON TABLE "public"."embedding_jobs" TO "anon";
GRANT ALL ON TABLE "public"."embedding_jobs" TO "authenticated";
GRANT ALL ON TABLE "public"."embedding_jobs" TO "service_role";



GRANT ALL ON TABLE "public"."equipment" TO "anon";
GRANT ALL ON TABLE "public"."equipment" TO "authenticated";
GRANT ALL ON TABLE "public"."equipment" TO "service_role";



GRANT ALL ON TABLE "public"."equipment_parts" TO "anon";
GRANT ALL ON TABLE "public"."equipment_parts" TO "authenticated";
GRANT ALL ON TABLE "public"."equipment_parts" TO "service_role";



GRANT ALL ON TABLE "public"."event_logs" TO "anon";
GRANT ALL ON TABLE "public"."event_logs" TO "authenticated";
GRANT ALL ON TABLE "public"."event_logs" TO "service_role";



GRANT ALL ON TABLE "public"."faults" TO "anon";
GRANT ALL ON TABLE "public"."faults" TO "authenticated";
GRANT ALL ON TABLE "public"."faults" TO "service_role";



GRANT ALL ON TABLE "public"."graph_edges" TO "anon";
GRANT ALL ON TABLE "public"."graph_edges" TO "authenticated";
GRANT ALL ON TABLE "public"."graph_edges" TO "service_role";



GRANT ALL ON TABLE "public"."graph_nodes" TO "anon";
GRANT ALL ON TABLE "public"."graph_nodes" TO "authenticated";
GRANT ALL ON TABLE "public"."graph_nodes" TO "service_role";



GRANT ALL ON TABLE "public"."handover_items" TO "anon";
GRANT ALL ON TABLE "public"."handover_items" TO "authenticated";
GRANT ALL ON TABLE "public"."handover_items" TO "service_role";



GRANT ALL ON TABLE "public"."handovers" TO "anon";
GRANT ALL ON TABLE "public"."handovers" TO "authenticated";
GRANT ALL ON TABLE "public"."handovers" TO "service_role";



GRANT ALL ON TABLE "public"."hours_of_rest" TO "anon";
GRANT ALL ON TABLE "public"."hours_of_rest" TO "authenticated";
GRANT ALL ON TABLE "public"."hours_of_rest" TO "service_role";



GRANT ALL ON TABLE "public"."inventory_stock" TO "anon";
GRANT ALL ON TABLE "public"."inventory_stock" TO "authenticated";
GRANT ALL ON TABLE "public"."inventory_stock" TO "service_role";



GRANT ALL ON TABLE "public"."ocred_pages" TO "anon";
GRANT ALL ON TABLE "public"."ocred_pages" TO "authenticated";
GRANT ALL ON TABLE "public"."ocred_pages" TO "service_role";



GRANT ALL ON TABLE "public"."parts" TO "anon";
GRANT ALL ON TABLE "public"."parts" TO "authenticated";
GRANT ALL ON TABLE "public"."parts" TO "service_role";



GRANT ALL ON TABLE "public"."predictive_insights" TO "anon";
GRANT ALL ON TABLE "public"."predictive_insights" TO "authenticated";
GRANT ALL ON TABLE "public"."predictive_insights" TO "service_role";



GRANT ALL ON TABLE "public"."predictive_state" TO "anon";
GRANT ALL ON TABLE "public"."predictive_state" TO "authenticated";
GRANT ALL ON TABLE "public"."predictive_state" TO "service_role";



GRANT ALL ON TABLE "public"."purchase_order_items" TO "anon";
GRANT ALL ON TABLE "public"."purchase_order_items" TO "authenticated";
GRANT ALL ON TABLE "public"."purchase_order_items" TO "service_role";



GRANT ALL ON TABLE "public"."purchase_orders" TO "anon";
GRANT ALL ON TABLE "public"."purchase_orders" TO "authenticated";
GRANT ALL ON TABLE "public"."purchase_orders" TO "service_role";



GRANT ALL ON TABLE "public"."search_queries" TO "anon";
GRANT ALL ON TABLE "public"."search_queries" TO "authenticated";
GRANT ALL ON TABLE "public"."search_queries" TO "service_role";



GRANT ALL ON TABLE "public"."suppliers" TO "anon";
GRANT ALL ON TABLE "public"."suppliers" TO "authenticated";
GRANT ALL ON TABLE "public"."suppliers" TO "service_role";



GRANT ALL ON TABLE "public"."user_roles" TO "anon";
GRANT ALL ON TABLE "public"."user_roles" TO "authenticated";
GRANT ALL ON TABLE "public"."user_roles" TO "service_role";



GRANT ALL ON TABLE "public"."users" TO "anon";
GRANT ALL ON TABLE "public"."users" TO "authenticated";
GRANT ALL ON TABLE "public"."users" TO "service_role";



GRANT ALL ON TABLE "public"."work_order_history" TO "anon";
GRANT ALL ON TABLE "public"."work_order_history" TO "authenticated";
GRANT ALL ON TABLE "public"."work_order_history" TO "service_role";



GRANT ALL ON TABLE "public"."work_orders" TO "anon";
GRANT ALL ON TABLE "public"."work_orders" TO "authenticated";
GRANT ALL ON TABLE "public"."work_orders" TO "service_role";



GRANT ALL ON TABLE "public"."yachts" TO "anon";
GRANT ALL ON TABLE "public"."yachts" TO "authenticated";
GRANT ALL ON TABLE "public"."yachts" TO "service_role";









ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "service_role";






ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "service_role";






ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "service_role";






























\unrestrict LvRpyC4XKNPiNuNhcOOBmSUbhfFL8hnOV4fOdZaHhipT7PzohvwkgLX6phIMR9i

RESET ALL;
