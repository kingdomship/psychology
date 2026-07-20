"""Aggregate all API route modules."""

from fastapi import APIRouter

from app.routes.chat import router as chat_router
from app.routes.emotions import router as emotions_router
from app.routes.diary import router as diary_router
from app.routes.memory import router as memory_router
from app.routes.config import router as config_router
from app.routes.therapy import router as therapy_router
from app.routes.distill import router as distill_router
from app.routes.personality import router as personality_router
from app.routes.mood import router as mood_router
from app.routes.psych import router as psych_router
from app.routes.report import router as report_router
from app.routes.export import router as export_router
from app.routes.assessment import router as assessment_router
from app.routes.goals import router as goals_router
from app.routes.training import router as training_router

router = APIRouter()
router.include_router(chat_router)
router.include_router(emotions_router)
router.include_router(diary_router)
router.include_router(memory_router)
router.include_router(config_router)
router.include_router(therapy_router)
router.include_router(distill_router)
router.include_router(personality_router)
router.include_router(mood_router)
router.include_router(psych_router)
router.include_router(report_router)
router.include_router(export_router)
router.include_router(assessment_router)
router.include_router(goals_router)
router.include_router(training_router)
