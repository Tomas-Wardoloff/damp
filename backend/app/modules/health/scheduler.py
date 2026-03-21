import asyncio
import logging
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import func, select

from app.core.config import settings
from app.core.database import SessionLocal
from app.integrations.ai_client import AIClient
from app.modules.cow.models import Cow
from app.modules.health.models import HealthAnalysis, HealthSchedulerConfig
from app.modules.health.service import HealthService

logger = logging.getLogger(__name__)


class HealthCheckScheduler:
    def __init__(self) -> None:
        self._task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()
        self._last_execution_at: datetime | None = None
        self._current_per_cow_seconds: int | None = None

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    @property
    def last_execution_at(self) -> datetime | None:
        return self._last_execution_at

    @property
    def current_per_cow_seconds(self) -> int | None:
        return self._current_per_cow_seconds

    async def start(self) -> None:
        if self.running:
            return
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run_loop(), name="health-check-scheduler")
        logger.info("Health check scheduler started")

    async def stop(self) -> None:
        if not self._task:
            return
        self._stop_event.set()
        await self._task
        self._task = None
        logger.info("Health check scheduler stopped")

    def reset_timing(self) -> None:
        # Trigger a recomputation with the latest configuration right away.
        self._last_execution_at = None

    async def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                sleep_seconds = await self._tick()
            except Exception:
                logger.exception("Unexpected scheduler failure")
                sleep_seconds = 5

            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=sleep_seconds)
            except TimeoutError:
                continue

    async def _tick(self) -> int:
        with SessionLocal() as db:
            config = _get_or_create_config(db)
            if not config.enabled:
                self._current_per_cow_seconds = None
                return 5

            cow_ids = list(db.scalars(select(Cow.id).order_by(Cow.id.asc())).all())
            if not cow_ids:
                self._current_per_cow_seconds = None
                return 5

            cycle_seconds = max(60, config.cycle_minutes * 60)
            per_cow_seconds = max(1, cycle_seconds // len(cow_ids))
            self._current_per_cow_seconds = per_cow_seconds

            now = datetime.utcnow()
            if self._last_execution_at is not None:
                elapsed = int((now - self._last_execution_at).total_seconds())
                if elapsed < per_cow_seconds:
                    return max(1, per_cow_seconds - elapsed)

            ordered_candidates = _ordered_cow_ids_by_oldest_health(db)
            service = HealthService(db=db, ai_client=AIClient())

            for cow_id in ordered_candidates:
                try:
                    await service.analyze(cow_id=cow_id)
                    self._last_execution_at = now
                    logger.info("Scheduler analyzed cow_id=%s", cow_id)
                    break
                except HTTPException as exc:
                    # Skip cows not analyzable yet (e.g., missing readings) and continue.
                    if exc.status_code in {400, 404}:
                        logger.debug("Scheduler skipped cow_id=%s reason=%s", cow_id, exc.detail)
                        continue
                    logger.warning("Scheduler analysis error cow_id=%s status=%s", cow_id, exc.status_code)
                except Exception:
                    logger.exception("Scheduler failed analyzing cow_id=%s", cow_id)

            return 1


def _get_or_create_config(db) -> HealthSchedulerConfig:
    HealthSchedulerConfig.__table__.create(bind=db.get_bind(), checkfirst=True)
    config = db.scalar(select(HealthSchedulerConfig).order_by(HealthSchedulerConfig.id.asc()).limit(1))
    if config is not None:
        return config

    config = HealthSchedulerConfig(
        enabled=settings.health_scheduler_enabled,
        cycle_minutes=settings.health_scheduler_cycle_minutes,
        updated_at=datetime.utcnow(),
    )
    db.add(config)
    db.commit()
    db.refresh(config)
    return config


def _ordered_cow_ids_by_oldest_health(db) -> list[int]:
    latest_health_subquery = (
        select(
            HealthAnalysis.cow_id.label("cow_id"),
            func.max(HealthAnalysis.created_at).label("latest_at"),
        )
        .group_by(HealthAnalysis.cow_id)
        .subquery()
    )

    stmt = (
        select(Cow.id)
        .outerjoin(latest_health_subquery, latest_health_subquery.c.cow_id == Cow.id)
        .order_by(latest_health_subquery.c.latest_at.asc().nullsfirst(), Cow.id.asc())
    )
    return list(db.scalars(stmt).all())
