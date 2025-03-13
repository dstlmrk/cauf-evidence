import datetime
import logging

import django_rq
from django_rq.management.commands import rqscheduler

from tournaments.tasks import print_hello_world

scheduler = django_rq.get_scheduler()
log = logging.getLogger(__name__)

def clear_scheduled_jobs():
    # Delete any existing jobs in the scheduler when the app starts up
    for job in scheduler.get_jobs():
        log.debug("Deleting scheduled job %s", job)
        job.delete()

def register_scheduled_jobs():
    # do your scheduling here
    print(scheduler.schedule(
        scheduled_time=datetime.datetime.now(),
        func=print_hello_world,
        interval=10,  # ⏱ každých 10 sekund
        repeat=True,  # repeat forever
        result_ttl=60,  # výsledek se drží v Redis tolik sekund
    ))
    print("Scheduled")


class Command(rqscheduler.Command):
    def handle(self, *args, **kwargs):
        print("--------------------------------")
        # This is necessary to prevent dupes
        clear_scheduled_jobs()
        register_scheduled_jobs()
        super(Command, self).handle(*args, **kwargs)
