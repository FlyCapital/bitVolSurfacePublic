import sys
import time
import pytz
import schedule
import json
import math
import numpy as np
import pandas as pd
import QuantLib as ql
from datetime import timezone
from pymysql import connect, err, sys, cursors


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


def connect_db(local=False):
    if local == True:
        conn_db = connect(host='root',
                          user='localdbusername',
                          passwd='dbpwd',
                          db='dbname')

    else:

        conn_db = connect(host='dburl',
                          user='dbusername',
                          passwd='dbpwd',
                          db='dbname')

    return conn_db


def getLatestOptionChain(live=True):
    conn_db = connect_db(live)
    sql = "SELECT * FROM bitvol where ID=(SELECT ID FROM bitvol ORDER BY DateTime DESC LIMIT 1)"

    opt_df = pd.read_sql(sql, con=conn_db)

    return opt_df


def getOptionChainViaId(snapShotId):
    conn_db = connect_db()
    sql = "SELECT * FROM bitvol where ID='" + str(snapShotId) + "'"

    opt_df = pd.read_sql(sql, con=conn_db)

    return opt_df


def py2ql_date(pydate):
    return ql.Date(pydate.day, pydate.month, pydate.year)


def getYearFrac(date0, date1):
    day_count = ql.Actual365Fixed()
    yrs = day_count.yearFraction(py2ql_date(date0), py2ql_date(date1))

    if yrs == 0:
        yrs += 0.001

    return yrs


def jsonPrint(d):
    print(json.dumps(d, indent=2))


def printList(l):
    for item in l:
        print(item)


def getATMstk(F0, Klist):
    K0 = Klist[0]
    Kdis = abs(K0 - F0)
    K0pos = 0

    for i in range(0, len(Klist)):
        if abs(Klist[i] - F0) < Kdis:
            K0pos = i
            K0 = Klist[i]
            Kdis = abs(Klist[i] - F0)

    return K0


def volRealized(pxList, annu_factor=365):
    retList = []
    for i in range(1, len(pxList)):
        retList.append(pxList[i] / pxList[i - 1] - 1)

    return np.std(retList) * math.sqrt(annu_factor) * 100


def main(args):

    timeList=['21:42','21:43','21:44','21:45']
    scheduler(timeList,job)


if __name__ == '__main__':
    sys.exit(main(sys.argv))
