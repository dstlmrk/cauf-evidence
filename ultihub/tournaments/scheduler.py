# import django_rq
# from datetime import datetime
# from tournaments.tasks import print_hello_world

def schedule_hello_world_task():
    pass
    # scheduler = django_rq.get_scheduler('default')
    #
    # # Zkontroluj, jestli už není naplánovaný (aby se nespouštěl vícenásobně při restartu)
    # for job in scheduler.get_jobs():
    #     if job.func_name == 'myapp.tasks.print_hello_world':
    #         print("Task už je naplánován ✅")
    #         return
    #
    # # Plánuj každých 10 sekund
    # scheduler.schedule(
    #     scheduled_time=datetime.now(),  # první spuštění
    #     func=print_hello_world,
    #     interval=10,        # ⏱ každých 10 sekund
    #     repeat=None,        # repeat forever
    #     result_ttl=60,      # výsledek se drží v Redis tolik sekund
    # )
    # print("Naplánován nový Hello World task ✅")