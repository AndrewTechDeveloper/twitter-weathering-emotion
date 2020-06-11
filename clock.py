from apscheduler.schedulers.blocking import BlockingScheduler
import main

twische = BlockingScheduler()

@twische.scheduled_job('interval',minutes=5)
def timed_job():
    main.cron_worker()

if __name__ == "__main__":
    twische.start()
