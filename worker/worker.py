from consumer import consume
import os

consume(os.getenv("RABBITMQ_HOST"))
