import time

from bson import json_util
from producer import produce_router, produce_switch
from database import get_router_info, get_switch_info


def scheduler():

    INTERVAL = 10.0
    next_run = time.monotonic()
    count = 0
    host = os.getenv("RABBITMQ_HOST")
    while True:
        now = time.time()
        now_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now))
        ms = int((now % 1) * 1000)
        now_str_with_ms = f"{now_str}.{ms:03d}"
        print(f"[{now_str_with_ms}] run #{count}")

        try:
            for data in get_router_info():
                body_bytes = json_util.dumps(data).encode("utf-8")
                produce_router(host, body_bytes)
            for datas in get_switch_info():
                body_bytes = json_util.dumps(datas).encode("utf-8")
                produce_switch(host, body_bytes)
        except Exception as e:
            print(e)
            time.sleep(3)
        count += 1
        next_run += INTERVAL
        time.sleep(max(0.0, next_run - time.monotonic()))


if __name__ == "__main__":
    scheduler()
