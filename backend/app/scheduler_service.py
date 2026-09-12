import time
import threading
import logging
from datetime import datetime
from app.database import SessionLocal
from app.models import ScheduledRoutine
from app.agent_planner import plan
from app.agent_executor import execute as execute_plan

logger = logging.getLogger("arya.scheduler")

class SchedulerService:
    def __init__(self):
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.running = False

    def start(self):
        self.running = True
        self.thread.start()
        logger.info("Autonomous Cron Scheduler started in background.")

    def _run_loop(self):
        last_minute = -1
        while self.running:
            now = datetime.now()
            if now.minute != last_minute:
                last_minute = now.minute
                self._check_and_execute_routines(now)
            time.sleep(1)

    def _check_and_execute_routines(self, now: datetime):
        db = SessionLocal()
        try:
            routines = db.query(ScheduledRoutine).filter(ScheduledRoutine.is_active == 1).all()
            for r in routines:
                # Naive cron parsing: minute hour * * *
                parts = r.cron_expr.split()
                if len(parts) >= 5:
                    c_min, c_hour = parts[0], parts[1]
                    match_min = c_min == "*" or str(now.minute) == c_min
                    match_hour = c_hour == "*" or str(now.hour) == c_hour
                    if match_min and match_hour:
                        logger.info(f"[CRON] Executing scheduled command: {r.command}")
                        # Execute autonomously without websocket dependency!
                        action_plan = plan(r.command)
                        if action_plan:
                            execute_plan(action_plan)
        except Exception as e:
            logger.error(f"[CRON] Error executing routines: {e}")
        finally:
            db.close()

scheduler_service = SchedulerService()
