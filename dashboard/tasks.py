from celery import shared_task
import random


@shared_task
def test_number():
    number = random.randint(1, 100)
    return number
