"""Centralized path configuration for Psychology."""

import os
import threading

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEMORY_DIR = os.environ.get("MEMORY_DIR", os.path.join(BASE_DIR, "memory"))

ARCHIVE_PATH = os.path.join(MEMORY_DIR, "conversation_archive.jsonl")
SUMMARY_PATH = os.path.join(MEMORY_DIR, "conversation_summary.md")
PROFILE_PATH = os.path.join(MEMORY_DIR, "user_profile.md")
PERSONA_PATH = os.path.join(MEMORY_DIR, "user_persona.md")
CRYSTAL_PATH = os.path.join(MEMORY_DIR, "crystals.jsonl")
SITUATIONS_PATH = os.path.join(MEMORY_DIR, "situations.jsonl")
EPISODES_PATH = os.path.join(MEMORY_DIR, "episodes.jsonl")
MILESTONE_PATH = os.path.join(MEMORY_DIR, "milestones.jsonl")
STYLE_PATH = os.path.join(MEMORY_DIR, "attachment_style.json")
DRIFT_LOG_PATH = os.path.join(MEMORY_DIR, "drift_log.jsonl")
PREDICTION_PATH = os.path.join(MEMORY_DIR, "prediction.json")
SALIENCE_PREV_PATH = os.path.join(MEMORY_DIR, "salience_prev.json")
VALENCE_PREV_PATH = os.path.join(MEMORY_DIR, "valence_prev.json")
PERSONALITY_CONFIG_PATH = os.path.join(MEMORY_DIR, "personality_config.json")
APIKEY_PATH = os.path.join(MEMORY_DIR, "api_key.txt")

LIFE_DOMAINS_PATH = os.path.join(MEMORY_DIR, "life_domains.json")
CURIOSITY_PATH = os.path.join(MEMORY_DIR, "curiosity_queue.json")

USER_VALUES_PATH = os.path.join(MEMORY_DIR, "user_values.json")
USER_STRENGTHS_PATH = os.path.join(MEMORY_DIR, "user_strengths.json")

CRISIS_LOG_PATH = os.path.join(MEMORY_DIR, "crisis_log.jsonl")
DISTILL_DIR = os.path.join(MEMORY_DIR, "distilled_profiles")

# Lock for thread-safe archive file access
archive_lock = threading.Lock()


def atomic_write(path: str, data: str):
    """Write data to a file atomically via temp file + rename."""
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        f.write(data)
    os.replace(tmp, path)
