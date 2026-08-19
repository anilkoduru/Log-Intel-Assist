import os
from kafka import KafkaProducer

TOPIC = 'raw-logs'
LOG_FILE = os.path.join('HDFS_v1', 'HDFS.log')
MAX_LINES = 1000

producer = KafkaProducer(
    bootstrap_servers=['localhost:9092'],
    value_serializer=lambda v: v.encode('utf-8')
)


def send_log(log_message: str):
    producer.send(TOPIC, log_message)


def send_first_n_lines(file_path: str = LOG_FILE, limit: int = MAX_LINES):
    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
        for index, line in enumerate(f, start=1):
            if index > limit:
                break
            send_log(line.rstrip('\n'))

    producer.flush()
    print(f"Sent {limit} lines from {file_path} to topic '{TOPIC}'.")


if __name__ == '__main__':
    send_first_n_lines()

