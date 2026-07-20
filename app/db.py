"""Emotion database — connects to the `emotion` database on PostgreSQL."""

import os
import logging
import re
import psycopg2
import psycopg2.extras
from psycopg2 import pool

logger = logging.getLogger("emoji-chat")

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "postgres"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "database": os.getenv("DB_NAME", "emotion"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
}

_pool = None


def _get_pool():
    global _pool
    if _pool is None:
        _pool = pool.SimpleConnectionPool(1, 5, **DB_CONFIG)
    return _pool


def _conn():
    c = _get_pool().getconn()
    c.autocommit = True
    return c


def _pg(sql):
    return re.sub(r'\$\d+', '%s', sql)


def q(sql, params=None, fetch="all"):
    sql = _pg(sql)
    conn = _conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params or ())
            if fetch == "one":
                row = cur.fetchone()
                return dict(row) if row is not None else None
            return [dict(r) for r in cur.fetchall()]
    except Exception:
        logger.warning("Operation failed", exc_info=True)
        return [] if fetch == "all" else None
    finally:
        _get_pool().putconn(conn)


def execute(sql, params=None):
    sql = _pg(sql)
    conn = _conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.rowcount
    except Exception:
        logger.warning("Operation failed", exc_info=True)
        return -1
    finally:
        _get_pool().putconn(conn)


_init_done = False


def init_db():
    global _init_done
    if _init_done:
        return
    execute("CREATE EXTENSION IF NOT EXISTS vector")

    execute("""
        CREATE TABLE IF NOT EXISTS emotion_cache (
            id SERIAL PRIMARY KEY,
            label VARCHAR(100) UNIQUE NOT NULL,
            eye_curve REAL NOT NULL DEFAULT 0,
            eye_open REAL NOT NULL DEFAULT 0.5,
            eye_pupil REAL NOT NULL DEFAULT 0,
            mouth_curve REAL NOT NULL DEFAULT 0,
            mouth_open REAL NOT NULL DEFAULT 0,
            mouth_width REAL NOT NULL DEFAULT 0.8,
            sparkle REAL NOT NULL DEFAULT 0.5,
            brow_angle REAL NOT NULL DEFAULT 0,
            brow_height REAL NOT NULL DEFAULT 0.5,
            brow_asym REAL NOT NULL DEFAULT 0,
            reply TEXT NOT NULL DEFAULT '',
            sequence_data JSONB,
            use_count INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)
    # Migration for missing columns
    for col, typ in [
        ("eye_pupil", "REAL NOT NULL DEFAULT 0"),
        ("brow_angle", "REAL NOT NULL DEFAULT 0"),
        ("brow_height", "REAL NOT NULL DEFAULT 0.5"),
        ("brow_asym", "REAL NOT NULL DEFAULT 0"),
        ("sequence_data", "JSONB"),
        ("blush", "REAL NOT NULL DEFAULT 0"),
        ("head_tilt", "REAL NOT NULL DEFAULT 0"),
        ("tear", "REAL NOT NULL DEFAULT 0"),
        ("mouth_asym", "REAL NOT NULL DEFAULT 0"),
        ("eye_wink", "REAL NOT NULL DEFAULT 0"),
        ("eye_tension", "REAL NOT NULL DEFAULT 0"),
        ("iris_size", "REAL NOT NULL DEFAULT 0.5"),
        ("lip_pout", "REAL NOT NULL DEFAULT 0"),
        ("lip_stretch", "REAL NOT NULL DEFAULT 0"),
        ("lip_bite", "REAL NOT NULL DEFAULT 0"),
        ("jaw_drop", "REAL NOT NULL DEFAULT 0"),
        ("tongue_out", "REAL NOT NULL DEFAULT 0"),
        ("nose_wrinkle", "REAL NOT NULL DEFAULT 0"),
        ("cheek_raise", "REAL NOT NULL DEFAULT 0"),
        ("cheek_puff", "REAL NOT NULL DEFAULT 0"),
        ("sweat_drop", "REAL NOT NULL DEFAULT 0"),
        ("vein_pop", "REAL NOT NULL DEFAULT 0"),
        ("color_fields", "TEXT"),
        ("background", "TEXT"),
        ("whiteboard", "TEXT"),
    ]:
        try:
            execute(f"ALTER TABLE emotion_cache ADD COLUMN IF NOT EXISTS {col} {typ}")
        except Exception:
            logger.warning("Operation failed", exc_info=True)

    # Chat history
    execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id SERIAL PRIMARY KEY,
            user_msg TEXT NOT NULL,
            avatar_reply TEXT NOT NULL DEFAULT '',
            emotion_label VARCHAR(100) NOT NULL DEFAULT '',
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Semantic memory vectors for similarity search
    execute("""
        CREATE TABLE IF NOT EXISTS memory_vectors (
            id SERIAL PRIMARY KEY,
            chat_id INTEGER NOT NULL REFERENCES chat_history(id),
            embedding halfvec(256),
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    execute("""
        CREATE INDEX IF NOT EXISTS idx_memory_vectors_embedding
        ON memory_vectors USING hnsw (embedding halfvec_cosine_ops)
    """)

    # Diary entries
    execute("""
        CREATE TABLE IF NOT EXISTS diary_entries (
            id SERIAL PRIMARY KEY,
            date DATE UNIQUE NOT NULL,
            content TEXT NOT NULL DEFAULT '',
            chat_count INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Diary entries — dual-perspective columns
    for col, typ in [
        ("user_content", "TEXT DEFAULT ''"),
        ("mood_emoji", "VARCHAR(10) DEFAULT '✨'"),
        ("user_mood_emoji", "VARCHAR(10) DEFAULT ''"),
        ("has_user_diary", "BOOLEAN DEFAULT FALSE"),
    ]:
        try:
            execute(f"ALTER TABLE diary_entries ADD COLUMN IF NOT EXISTS {col} {typ}")
        except Exception:
            pass

    # Panksepp affect state (6 primary emotional dimensions)
    execute("""
        CREATE TABLE IF NOT EXISTS affect_state (
            id SERIAL PRIMARY KEY,
            dimension VARCHAR(20) UNIQUE NOT NULL,
            value REAL NOT NULL DEFAULT 0.0,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Performance indexes
    execute("CREATE INDEX IF NOT EXISTS idx_chat_history_created_at ON chat_history (created_at)")
    execute("CREATE INDEX IF NOT EXISTS idx_memory_vectors_chat_id ON memory_vectors (chat_id)")
    execute("CREATE INDEX IF NOT EXISTS idx_emotion_cache_use_count ON emotion_cache (use_count DESC)")

    # ── Drift detection tables (Mahalanobis + multi-level) ────────────

    execute("""
        CREATE TABLE IF NOT EXISTS drift_baseline (
            id SERIAL PRIMARY KEY,
            mean_embedding halfvec(256),
            covariance_diag halfvec(256),
            built_at TIMESTAMP DEFAULT NOW(),
            sample_count INTEGER NOT NULL DEFAULT 0
        )
    """)

    execute("""
        CREATE TABLE IF NOT EXISTS drift_coreset (
            id SERIAL PRIMARY KEY,
            reply_text TEXT NOT NULL,
            embedding halfvec(256),
            weight REAL NOT NULL DEFAULT 1.0,
            distance REAL NOT NULL DEFAULT 0.0,
            recorded_at TIMESTAMP DEFAULT NOW()
        )
    """)

    execute("""
        CREATE TABLE IF NOT EXISTS drift_log (
            id SERIAL PRIMARY KEY,
            level VARCHAR(10) NOT NULL,
            mahalanobis_distance REAL NOT NULL,
            predicted_distance REAL,
            turns_until_threshold REAL,
            intervention TEXT,
            details JSONB,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # ── Knowledge graph tables ───────────────────────────────────────

    execute("""
        CREATE TABLE IF NOT EXISTS kg_entities (
            id SERIAL PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            type VARCHAR(50) NOT NULL DEFAULT 'unknown',
            first_seen TIMESTAMP DEFAULT NOW(),
            last_seen TIMESTAMP DEFAULT NOW(),
            metadata JSONB DEFAULT '{}',
            UNIQUE(name, type)
        )
    """)

    execute("""
        CREATE TABLE IF NOT EXISTS kg_relationships (
            id SERIAL PRIMARY KEY,
            source_id INTEGER NOT NULL REFERENCES kg_entities(id),
            target_id INTEGER NOT NULL REFERENCES kg_entities(id),
            relation VARCHAR(100) NOT NULL,
            valid_at TIMESTAMP DEFAULT NOW(),
            invalid_at TIMESTAMP DEFAULT NULL,
            strength REAL NOT NULL DEFAULT 0.5,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)
    execute("CREATE INDEX IF NOT EXISTS idx_kg_entities_name ON kg_entities(name)")
    execute("CREATE INDEX IF NOT EXISTS idx_kg_entities_last_seen ON kg_entities(last_seen)")

    # ── Predictive agent table ───────────────────────────────────────

    execute("""
        CREATE TABLE IF NOT EXISTS prediction_history (
            id SERIAL PRIMARY KEY,
            predicted_need VARCHAR(50),
            predicted_emotion VARCHAR(50),
            predicted_topic VARCHAR(200),
            actual_need VARCHAR(50),
            actual_emotion VARCHAR(50),
            actual_topic VARCHAR(200),
            prediction_error REAL,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # ── Dual-system insights table ────────────────────────────────────

    execute("""
        CREATE TABLE IF NOT EXISTS system2_insights (
            id SERIAL PRIMARY KEY,
            insight TEXT NOT NULL,
            source_message TEXT,
            category VARCHAR(50),
            applied_to_system1 BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Self-evaluation log for reply quality tracking
    execute("""
        CREATE TABLE IF NOT EXISTS self_eval_log (
            id SERIAL PRIMARY KEY,
            turn_id INTEGER REFERENCES chat_history(id),
            user_msg TEXT NOT NULL DEFAULT '',
            avatar_reply TEXT NOT NULL DEFAULT '',
            trust_impact REAL DEFAULT 0,
            warmth_impact REAL DEFAULT 0,
            engagement_impact REAL DEFAULT 0,
            risk_level REAL DEFAULT 0,
            impact_assessment TEXT DEFAULT '',
            has_contradiction BOOLEAN DEFAULT FALSE,
            contradiction_desc TEXT DEFAULT '',
            contradiction_confidence REAL DEFAULT 0,
            overall_score REAL DEFAULT 0,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    execute("""
        CREATE INDEX IF NOT EXISTS idx_self_eval_log_created_at
        ON self_eval_log (created_at)
    """)
    execute("""
        CREATE INDEX IF NOT EXISTS idx_self_eval_log_turn_id
        ON self_eval_log (turn_id)
    """)

    # ── 心理健康辅助: 危机检测 ──────────────────────────────
    execute("""
        CREATE TABLE IF NOT EXISTS crisis_events (
            id SERIAL PRIMARY KEY,
            session_id VARCHAR(50) NOT NULL DEFAULT '',
            severity REAL NOT NULL DEFAULT 0,
            user_msg TEXT NOT NULL DEFAULT '',
            crisis_type VARCHAR(50) NOT NULL DEFAULT 'keyword',
            has_method BOOLEAN NOT NULL DEFAULT FALSE,
            llm_verified BOOLEAN NOT NULL DEFAULT FALSE,
            llm_severity INTEGER,
            urgency VARCHAR(20),
            acknowledged BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            acknowledged_at TIMESTAMP
        )
    """)

    execute("""
        CREATE TABLE IF NOT EXISTS crisis_resources (
            id SERIAL PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            phone VARCHAR(50) NOT NULL,
            description TEXT DEFAULT '',
            country VARCHAR(50) DEFAULT '中国',
            hours VARCHAR(100) DEFAULT '24小时',
            active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
    """)

    execute("""
        CREATE TABLE IF NOT EXISTS risk_snapshot (
            id SERIAL PRIMARY KEY,
            session_id VARCHAR(50) NOT NULL DEFAULT '',
            valence_ema REAL DEFAULT 0.5,
            distress_ema REAL DEFAULT 0.0,
            crisis_count_24h INTEGER DEFAULT 0,
            risk_level INTEGER DEFAULT 0,
            last_check_at TIMESTAMP NOT NULL DEFAULT NOW(),
            created_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
    """)

    execute("""
        CREATE TABLE IF NOT EXISTS cbt_records (
            id SERIAL PRIMARY KEY,
            situation TEXT DEFAULT '',
            auto_thought TEXT DEFAULT '',
            evidence_for TEXT DEFAULT '',
            evidence_against TEXT DEFAULT '',
            alternative TEXT DEFAULT '',
            reframed TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)

    execute("""
        CREATE TABLE IF NOT EXISTS affect_history (
            id SERIAL PRIMARY KEY,
            date DATE UNIQUE NOT NULL,
            seeking REAL DEFAULT 0.35,
            play REAL DEFAULT 0.25,
            care REAL DEFAULT 0.2,
            fear REAL DEFAULT 0.1,
            rage REAL DEFAULT 0.05,
            panic REAL DEFAULT 0.1,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # ── Mood self-checkin ──────────────────────────────────────────
    execute("""
        CREATE TABLE IF NOT EXISTS mood_checkins (
            id SERIAL PRIMARY KEY,
            mood_emoji VARCHAR(10) NOT NULL,
            intensity INTEGER NOT NULL DEFAULT 5,
            tags TEXT[] DEFAULT '{}',
            note TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Hebbian crystal associations (Module 6: Memory upgrade)
    execute("""
        CREATE TABLE IF NOT EXISTS crystal_associations (
            id SERIAL PRIMARY KEY,
            crystal_id_a TEXT NOT NULL,
            crystal_id_b TEXT NOT NULL,
            weight REAL DEFAULT 0.1,
            last_co_accessed TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(crystal_id_a, crystal_id_b)
        )
    """)

    # Behavioral markers (trend analysis)
    execute("""
        CREATE TABLE IF NOT EXISTS behavioral_markers (
            id SERIAL PRIMARY KEY,
            session_id VARCHAR(50) DEFAULT 'default',
            window_start TIMESTAMPTZ NOT NULL,
            window_end TIMESTAMPTZ NOT NULL,
            avg_latency_seconds REAL DEFAULT 0,
            latency_trend_slope REAL DEFAULT 0,
            latency_trend_direction VARCHAR(20) DEFAULT 'stable',
            avg_user_msg_length REAL DEFAULT 0,
            length_trend_slope REAL DEFAULT 0,
            length_trend_direction VARCHAR(20) DEFAULT 'stable',
            late_night_ratio REAL DEFAULT 0,
            late_night_frequency INTEGER DEFAULT 0,
            rhythm_stability REAL DEFAULT 0,
            preferred_hour REAL DEFAULT 12,
            circadian_consistency REAL DEFAULT 0,
            computed_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    execute("""
        CREATE INDEX IF NOT EXISTS idx_behavioral_markers_window
        ON behavioral_markers (window_start, window_end)
    """)

    # Trend warnings (trend analysis alerts)
    execute("""
        CREATE TABLE IF NOT EXISTS trend_warnings (
            id SERIAL PRIMARY KEY,
            session_id VARCHAR(50) DEFAULT 'default',
            warning_type VARCHAR(30) NOT NULL,
            severity REAL NOT NULL DEFAULT 0,
            details JSONB DEFAULT '{}',
            acknowledged BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    execute("""
        CREATE INDEX IF NOT EXISTS idx_trend_warnings_type
        ON trend_warnings (warning_type)
    """)
    execute("""
        CREATE INDEX IF NOT EXISTS idx_trend_warnings_created
        ON trend_warnings (created_at)
    """)

    # Intervention outcomes (effectiveness tracking)
    execute("""
        CREATE TABLE IF NOT EXISTS intervention_outcomes (
            id SERIAL PRIMARY KEY,
            turn_id INTEGER,
            intervention_type VARCHAR(50) NOT NULL,
            trigger_intent VARCHAR(50) DEFAULT '',
            affect_before JSONB NOT NULL DEFAULT '{}',
            affect_after JSONB NOT NULL DEFAULT '{}',
            affect_delta JSONB NOT NULL DEFAULT '{}',
            distress_reduction REAL DEFAULT 0,
            valence_improvement REAL DEFAULT 0,
            user_msg TEXT DEFAULT '',
            session_id VARCHAR(50) DEFAULT 'default',
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    execute("""
        CREATE INDEX IF NOT EXISTS idx_intervention_type
        ON intervention_outcomes (intervention_type)
    """)
    execute("""
        CREATE INDEX IF NOT EXISTS idx_intervention_created
        ON intervention_outcomes (created_at)
    """)

    # ── 治疗会话状态机 ────────────────────────────────────────────
    execute("""
        CREATE TABLE IF NOT EXISTS therapy_sessions (
            id SERIAL PRIMARY KEY,
            session_type VARCHAR(20) NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'active',
            current_step INTEGER NOT NULL DEFAULT 0,
            total_steps INTEGER NOT NULL,
            step_names TEXT[] DEFAULT '{}',
            context JSONB DEFAULT '{}',
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    execute("""
        CREATE TABLE IF NOT EXISTS therapy_session_steps (
            id SERIAL PRIMARY KEY,
            session_id INTEGER NOT NULL REFERENCES therapy_sessions(id),
            step_index INTEGER NOT NULL,
            step_name VARCHAR(50) NOT NULL DEFAULT '',
            user_input TEXT DEFAULT '',
            ai_response TEXT DEFAULT '',
            turn_id INTEGER REFERENCES chat_history(id),
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    execute("""
        CREATE INDEX IF NOT EXISTS idx_therapy_sessions_status
        ON therapy_sessions (status, session_type)
    """)
    execute("""
        CREATE INDEX IF NOT EXISTS idx_session_steps_session
        ON therapy_session_steps (session_id, step_index)
    """)

    # ── 分析报告缓存 ────────────────────────────────────────────
    execute("""
        CREATE TABLE IF NOT EXISTS report_cache (
            id SERIAL PRIMARY KEY,
            report_type VARCHAR(20) NOT NULL,
            milestone_label VARCHAR(20),
            period_days INTEGER NOT NULL,
            active_days INTEGER NOT NULL DEFAULT 0,
            date_from DATE NOT NULL,
            date_to DATE NOT NULL,
            dashboard JSONB NOT NULL DEFAULT '{}',
            ai_insight JSONB NOT NULL DEFAULT '{}',
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    execute("""
        CREATE INDEX IF NOT EXISTS idx_report_cache_created
        ON report_cache (created_at DESC)
    """)
    execute("""
        CREATE INDEX IF NOT EXISTS idx_report_cache_type
        ON report_cache (report_type, milestone_label)
    """)

    # ── 临床评估 ────────────────────────────────────────────────
    execute("""
        CREATE TABLE IF NOT EXISTS assessment_sessions (
            id SERIAL PRIMARY KEY,
            scale_id VARCHAR(20) NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'in_progress',
            current_question INTEGER NOT NULL DEFAULT 1,
            answers JSONB DEFAULT '[]',
            total_score INTEGER,
            completed_at TIMESTAMPTZ DEFAULT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    # ── 治疗目标 ────────────────────────────────────────────────
    execute("""
        CREATE TABLE IF NOT EXISTS therapy_goals (
            id SERIAL PRIMARY KEY,
            goal_text TEXT NOT NULL DEFAULT '',
            category VARCHAR(30) NOT NULL DEFAULT 'general',
            progress_pct INTEGER NOT NULL DEFAULT 0,
            status VARCHAR(20) NOT NULL DEFAULT 'active',
            evidence TEXT DEFAULT '',
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    # ── 知情同意记录 ────────────────────────────────────────────
    execute("""
        CREATE TABLE IF NOT EXISTS user_consent (
            id SERIAL PRIMARY KEY,
            session_id VARCHAR(50) NOT NULL DEFAULT '',
            consented BOOLEAN NOT NULL DEFAULT TRUE,
            consent_version VARCHAR(20) DEFAULT '1.0',
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    _init_done = True
