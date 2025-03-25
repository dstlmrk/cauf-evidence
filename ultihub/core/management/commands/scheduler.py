import datetime
import logging

import django_rq
from django.utils.timezone import now
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

    # print(datetime.datetime.now())
    # print(datetime.datetime.utcnow())
    # print(now())

    # res = scheduler.schedule(
    #     scheduled_time=now(),
    #     func=print_hello_world,
    #     interval=10,  # každých 10 sekund
    #     repeat=None,  # repeat forever
    #     result_ttl=60,  # výsledek se drží v Redis tolik sekund
    # )
    res = scheduler.cron(
        "* * * * *",  # A cron string (e.g. "0 0 * * 0")
        func=print_hello_world,  # Function to be queued
        # args=[arg1, arg2],  # Arguments passed into function when executed
        # kwargs={'foo': 'bar'},  # Keyword arguments passed into function when executed
        repeat=None,  # Repeat this number of times (None means repeat forever)
        result_ttl=300,
        # Specify how long (in seconds) successful jobs and their results are kept. Defaults to -1 (forever)
        ttl=200,
        # Specifies the maximum queued time (in seconds) before it's discarded. Defaults to None (infinite TTL).
        # queue_name=queue_name,  # In which queue the job should be put in
        meta={'foo': 'bar'},  # Arbitrary pickleable data on the job itself
        # use_local_timezone=False  # Interpret hours in the local timezone
    )

    # res = scheduler.cron(
    #     cron_string="* * * * *",
    #     func=print_hello_world,
    #     repeat=None,  # repeat forever
    #     result_ttl=60,  # výsledek se drží v Redis tolik sekund
    # )
    print("scheduled cron", res)


class Command(rqscheduler.Command):
    def handle(self, *args, **kwargs):
        print("--------------------------------")
        # This is necessary to prevent dupes
        print("clearing scheduled jobs")
        clear_scheduled_jobs()
        print("registering scheduled jobs")
        register_scheduled_jobs()
        print("call super")
        super(Command, self).handle(*args, **kwargs)
