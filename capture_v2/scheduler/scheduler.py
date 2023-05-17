from dataclasses import dataclass
from datetime import datetime, timedelta
import os
from typing import Callable

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.date import DateTrigger
import dateutil
import dateutil.tz

from capture_v2.honeycomb_service import HoneycombCachingClient
from capture_v2.log import logger


@dataclass
class SchedulerTask:
    name: str
    callback: Callable
    kwargs: dict


@dataclass
class ClassHoursTasks:
    during_class_hours: SchedulerTask
    outside_class_hours: SchedulerTask


class Scheduler:
    def __init__(self, environment_id: str):
        self.honeycomb_client = HoneycombCachingClient()
        self.environment_id = environment_id

        self.coordinating_scheduler = BlockingScheduler()
        self.coordinating_scheduler.add_job(
            self.update_tasks,
            trigger="interval",
            minutes=10,
            id="coordinating_scheduler",
            next_run_time=datetime.now(dateutil.tz.tzutc()),
            misfire_grace_time=5,
        )

        self.tasks_scheduler = BackgroundScheduler()

        self.class_hours_tasks: list[ClassHoursTasks] = []
        self.all_hours_tasks: list[SchedulerTask] = []

    def add_class_hours_tasks(
        self,
        name: str,
        during_class_hours_callback: Callable,
        outside_class_hours_callback: Callable,
        during_class_hours_kwargs: dict = None,
        outside_class_hours_kwargs: dict = None,
    ):
        self.class_hours_tasks.append(
            ClassHoursTasks(
                during_class_hours=SchedulerTask(
                    name=f"start_{name}",
                    callback=during_class_hours_callback,
                    kwargs=during_class_hours_kwargs,
                ),
                outside_class_hours=SchedulerTask(
                    name=f"stop_{name}",
                    callback=outside_class_hours_callback,
                    kwargs=outside_class_hours_kwargs,
                ),
            )
        )

    def add_all_hours_tasks(self, name: str, callback: Callable, kwargs: dict = None):
        self.all_hours_tasks.append(
            SchedulerTask(name=name, callback=callback, kwargs=kwargs)
        )

    def _update_active_hours_tasks(
        self,
        classroom_start_time: datetime,
        classroom_end_time: datetime,
        timezone: dateutil.tz
    ):
        for class_hours_task in self.class_hours_tasks:
            tz_aware_datetime = datetime.now(tz=timezone)

            next_start: datetime
            next_stop: datetime
            if classroom_start_time <= tz_aware_datetime <= classroom_end_time:
                job = self.tasks_scheduler.get_job(
                    job_id=class_hours_task.outside_class_hours.name
                )
                if job is not None:
                    self.tasks_scheduler.remove_job(
                        job_id=class_hours_task.outside_class_hours.name
                    )

                next_start = tz_aware_datetime
                next_stop = classroom_end_time + timedelta(seconds=10)
            else:
                job = self.tasks_scheduler.get_job(
                    job_id=class_hours_task.during_class_hours.name
                )
                if job is not None:
                    self.tasks_scheduler.remove_job(
                        job_id=class_hours_task.during_class_hours.name
                    )
                next_start = classroom_start_time - timedelta(seconds=10)
                next_stop = tz_aware_datetime

            start_extra_job_args = {}
            DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")
            if DEBUG:
                start_extra_job_args["next_run_time"] = datetime.now(dateutil.tz.tzutc())
                
            logger.info(
                f"Scheduling {class_hours_task.during_class_hours.name} to run at {next_start}"
            )
            self.tasks_scheduler.add_job(
                func=class_hours_task.during_class_hours.callback,
                id=class_hours_task.during_class_hours.name,
                trigger=DateTrigger(
                    run_date=next_start  # Run during school capture window
                ),
                replace_existing=True,
                coalesce=True,
                misfire_grace_time=5,
                kwargs=class_hours_task.during_class_hours.kwargs,
                **start_extra_job_args,
            )

            logger.info(
                f"Scheduling {class_hours_task.outside_class_hours.name} to run at {next_stop}"
            )
            self.tasks_scheduler.add_job(
                func=class_hours_task.outside_class_hours.callback,
                id=class_hours_task.outside_class_hours.name,
                trigger=DateTrigger(
                    run_date=next_stop  # Run outside school capture window
                ),
                replace_existing=True,
                coalesce=True,
                misfire_grace_time=5,
                kwargs=class_hours_task.outside_class_hours.kwargs
            )

    def update_tasks(self):
        logger.info("Updating tasks")
        environment = self.honeycomb_client.fetch_environment_by_id(
            environment_id=self.environment_id
        )

        if environment is None:
            logger.error(
                f"Unable to find an environment for environment ID: {self.environment_id}"
            )
            return

        if environment["timezone_name"] is None or environment["timezone_name"] == "":
            logger.warning(
                f"Will not schedule jobs against '{environment['name']}' ({environment['environment_id']}), environment has not specified a timezone"
            )
            return

        if environment["name"] != "dahlia":
            logger.warning(
                f"Temporarily skipping {environment['name']} until we can flexibly grab start/end times"
            )
            return

        # TODO: Fetch start/end times from Honeycomb
        logger.info(f"Scheduling tasks for {environment['name']}")
        tz = dateutil.tz.gettz(environment["timezone_name"])
        tz_aware_datetime = datetime.now(tz=tz)
        environment_start_datetime = datetime.combine(
            date=tz_aware_datetime.date(),
            time=datetime.strptime("07:30", "%H:%M").time(),
            tzinfo=tz,
        )
        environment_end_datetime = datetime.combine(
            date=tz_aware_datetime.date(),
            time=datetime.strptime("17:30", "%H:%M").time(),
            tzinfo=tz,
        )

        self._update_active_hours_tasks(
            classroom_start_time=environment_start_datetime,
            classroom_end_time=environment_end_datetime,
            timezone=tz
        )

    def start(self):
        self.tasks_scheduler.start()
        self.coordinating_scheduler.start()
