import yaml
from web_monitor.kafka_client import KafkaSink
import time
from web_monitor.check_result import CheckResult

with open("config/web_monitor.yaml", "r") as f:
    config = yaml.safe_load(f)

with KafkaSink(config["kafka"]) as producer:
    print("Sending...")
    for i in range(50000):
        item = CheckResult(
            timestamp=time.time(),
            url="http://example.com",
            response_time=0.1,
            status_code=200,
            match_content=None)
        producer([item])
