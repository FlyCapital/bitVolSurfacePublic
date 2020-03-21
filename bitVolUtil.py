import sys
import json
import time
import pytz
import schedule
import smtplib, ssl
from datetime import timezone
from email.mime.text import MIMEText


class set:

    def __init__(self):
        None


def printJson(content):
    print(json.dumps(content, indent=2))



def scheduler(scheTime, job):

    for shTime in scheTime:

        schedule.every().day.at(shTime).do(job)

    while True:
        schedule.run_pending()


def job():
    print('Hello')


def utc_to_local(utc_dt):
    return utc_dt.replace(tzinfo=timezone.utc).astimezone(tz=pytz.timezone('US/Eastern'))


def main(args):

    timeList=['21:42','21:43','21:44','21:45']
    scheduler(timeList,job)


if __name__ == '__main__':
    sys.exit(main(sys.argv))
