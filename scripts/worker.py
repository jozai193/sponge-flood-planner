from redis import Redis
from rq import Queue, SimpleWorker
from rq.timeouts import TimerDeathPenalty

from services.api.settings import settings


class WindowsWorker(SimpleWorker):
    death_penalty_class=TimerDeathPenalty

if __name__=="__main__":
    connection=Redis.from_url(settings.redis_url)
    WindowsWorker([Queue("prepare",connection=connection),Queue("reference",connection=connection),
                   Queue("report",connection=connection)],connection=connection).work(with_scheduler=False)
