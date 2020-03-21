import time
import uuid
import datetime
from deribitv2 import *
from pymysql import connect, err, sys, cursors

def connect_db(local=False):

    if local==True:
        conn_db = connect(host='localhost',
                          user='root',
                          passwd='FN891124mysql',
                          db='tradingdb')

    else:

        conn_db = connect(host='mysqlaws.cwdlc79zzkjv.us-east-2.rds.amazonaws.com',
                          user='mysqlaws',
                          passwd='FN891124mysqlaws',
                          db='tradingdb')

    return conn_db

def pxConvt(px):
    if isinstance(px,str) or px==None:
        return -999999
    else:
        return px


def insertVolRec(conn_db, rec):

    try:
        cur = conn_db.cursor()

        values = ''
        key_list = ['DateTime', 'ID', 'Ticker', 'TickerUdly', 'InstrType', 'CallPut', 'Maturity', 'Strike', 'BidPx', 'AskPx', 'MarkPx']

        for key in key_list:
            value_tmp = str(rec[key])
            values += value_tmp + ','
        values = values[0:-1]

        sql = "INSERT INTO bitvol VALUES (" + values + ");"

        #print (sql)
        cur.execute(str(sql))
        cur.close()
        conn_db.commit()
    except Exception as error:
        if ('ConnectionAbortedError' in str(error)) == True:
            print(str(error))
            print('error encounted, reconnecting...')
            time.sleep(15)
            connect_db()
            insertVolRec(conn_db, rec)


def flashVol(live=False):

    try:

        optChain=getOptionChain()
        volId = str(uuid.uuid1())

        if live == True:
            volId = volId+'LIVE'
            db = connect_db(True)
        else:
            db = connect_db()

        snapShotTime=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print('Snapshoting BitCoin Volatility:', snapShotTime, volId)

        volRec = {'DateTime': '\'' + snapShotTime + '\'',
                  'ID': '\'' + str(volId) + '\'',
                  'Ticker': '\'' + 'BTCUSD' + '\'',
                  'TickerUdly': '\'' + 'N/A' + '\'',
                  'InstrType': '\'' + 'spot' + '\'',
                  'CallPut': '\'' + 'N/A' + '\'',
                  'Maturity': '\'' + snapShotTime + '\'',
                  'Strike': pxConvt('N/A'),
                  'BidPx': getIndexValue(),
                  'AskPx': getIndexValue(),
                  'MarkPx': getIndexValue()
                  }
        insertVolRec(db, volRec)

        for secTk in optChain:

            instrInfoTmp=optChain[secTk]['instrInfo']
            prcInfoTmp=optChain[secTk]['prcInfo']

            if instrInfoTmp['kind']=='option':
                volRec={'DateTime':'\''+snapShotTime+'\'',
                        'ID':'\''+str(volId)+'\'',
                        'Ticker':'\''+secTk+'\'',
                        'TickerUdly':'\''+prcInfoTmp['underlying_index'].split('.')[-1]+'\'',
                        'InstrType':'\''+'option'+'\'',
                        'CallPut': '\''+instrInfoTmp['option_type']+'\'',
                        'Maturity':'\''+datetime.datetime.fromtimestamp(instrInfoTmp['expiration_timestamp']/1e3).strftime("%Y-%m-%d %H:%M:%S")+'\'',
                        'Strike': pxConvt(instrInfoTmp['strike']),
                        'BidPx': pxConvt(prcInfoTmp['bid_price']),
                        'AskPx': pxConvt(prcInfoTmp['ask_price']),
                        'MarkPx':pxConvt(prcInfoTmp['mark_price'])
                }
            elif instrInfoTmp['kind']=='future':
                volRec={'DateTime':'\''+snapShotTime+'\'',
                        'ID':'\''+str(volId)+'\'',
                        'Ticker':'\''+secTk+'\'',
                        'TickerUdly': '\''+'N/A'+'\'',
                        'InstrType':'\''+'future'+'\'',
                        'CallPut': '\''+'N/A'+'\'',
                        'Maturity':'\''+datetime.datetime.fromtimestamp(instrInfoTmp['expiration_timestamp']/1e3).strftime("%Y-%m-%d %H:%M:%S")+'\'',
                        'Strike': pxConvt('N/A'),
                        'BidPx': pxConvt(prcInfoTmp['bid_price']),
                        'AskPx': pxConvt(prcInfoTmp['ask_price']),
                        'MarkPx':pxConvt(prcInfoTmp['mark_price'])
                }

            insertVolRec(db, volRec)

    except Exception as snapShotErr:
        print('Snapshoting BitCoin Volatility Error: ', snapShotErr)
        time.sleep(60)
        flashVol(live=live)


def main(args):

    #flashVol(True)
    volSnapShotTime=['00:00',
                     '01:00',
                     '02:00',
                     '03:00',
                     '04:00',
                     '05:00',
                     '06:00',
                     '07:00',
                     '08:00',
                     '09:00',
                     '10:00',
                     '11:00',
                     '12:00',
                     '13:00',
                     '14:00',
                     '15:00',
                     '16:00',
                     '17:00',
                     '18:00',
                     '19:00',
                     '20:00',
                     '21:00',
                     '22:00',
                     '23:00']
    scheduler(volSnapShotTime,flashVol)

if __name__ == '__main__':
    sys.exit(main(sys.argv))