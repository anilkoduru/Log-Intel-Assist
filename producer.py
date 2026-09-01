import os
from itertools import islice
from kafka import KafkaProducer

TOPIC = 'raw-logs'
LOG_FILE = os.path.join('HDFS_v1', 'HDFS.log')
MAX_LINES = None

producer = KafkaProducer(
    bootstrap_servers=['localhost:9092'],
    value_serializer=lambda v: v.encode('utf-8')
)


def send_log(log_message: str):
    producer.send(TOPIC, log_message)


def send_lines(file_path: str = LOG_FILE, max_lines: int = MAX_LINES):
    sent_count = 0
    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
        for index, line in enumerate(islice(f, max_lines), start=1):
            try:
                future = producer.send(TOPIC, line.rstrip('\n'))
                record_metadata = future.get(timeout=10)
                if index <= 3:  # Print first 3 lines for verification
                    print(f"Line {index}: Sent to partition {record_metadata.partition}, offset {record_metadata.offset}")
                sent_count += 1
            except Exception as e:
                print(f"Error sending line {index}: {e}")

    producer.flush()
    print(f"Sent {sent_count} lines from {file_path} to topic '{TOPIC}'.")


if __name__ == '__main__':
    send_lines()

