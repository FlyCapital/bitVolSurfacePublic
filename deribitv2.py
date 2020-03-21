import time
import sys
import hmac
import hashlib
import sys
import time
import json
from collections import OrderedDict
import ssl
import json
import random
import asyncio
from bitVolUtil import *
from websocket import create_connection

account_credential={
    'main':('client_id','client_secret'),
}

#public API

def sendReq(req):
    ws = create_connection('wss://www.deribit.com/ws/api/v2',
                           sslopt={"cert_reqs": ssl.CERT_NONE, "check_hostname": False,
                                   "ssl_version": ssl.PROTOCOL_TLSv1_2})
    ws.send(json.dumps(req))
    resp = json.loads(ws.recv())
    ws.close()
    #printJson(resp)
    return resp


def getContracts(instrType):
    req = \
        {
            "jsonrpc": "2.0",
            "id": 16,
            "method": "public/get_instruments",
            "params": {
                "currency": "BTC",
                "kind": instrType,
                "expired": False
            }
        }

    resp = sendReq(req)

    result={}

    for item in resp['result']:
        result[item['instrument_name']]=item

    return result


def getOrderBook(instrType):
    req = \
        {
            "jsonrpc": "2.0",
            "id": 17,
            "method": "public/get_book_summary_by_currency",
            "params": {
                "currency": "BTC",
                "kind": instrType
            }
        }

    resp = sendReq(req)
    result = {}

    for item in resp['result']:
        result[item['instrument_name']] = item

    return result

def getOrderBookInstr(Instr):
    req = \
        {
            "jsonrpc": "2.0",
            "id": 18,
            "method": "public/get_order_book",
            "params": {
                "instrument_name": Instr,
                "depth": 1
            }
        }

    resp = sendReq(req)

    return resp['result']


def getIndexValue():

    req = \
        {"jsonrpc": "2.0",
         "method": "public/get_index",
         "id": 19,
         "params": {
             "currency": "BTC"}
         }
    resp = sendReq(req)

    return resp['result']['BTC']


def getOptionChain():

    optChain={}

    optInstrInfo=getContracts('option')
    optPrcInfo=getOrderBook('option')

    futInstrInfo=getContracts('future')
    futPrcInfo=getOrderBook('future')

    for optInstr in optInstrInfo:

        if optInstr in optPrcInfo:
            optChain[optInstr]={'instrInfo': optInstrInfo[optInstr], 'prcInfo': optPrcInfo[optInstr]}
        else:
            optChain[optInstr]={'instrInfo': optInstrInfo[optInstr], 'prcInfo': {}}

    for futInstr in futInstrInfo:
        if futInstr in futPrcInfo:
            optChain[futInstr]={'instrInfo': futInstrInfo[futInstr], 'prcInfo': futPrcInfo[futInstr]}
        else:
            optChain[futInstr]={'instrInfo': futInstrInfo[futInstr], 'prcInfo': {}}

    return optChain

#private API

class deribit_v2:

    def __init__(self, client_id, client_secret):
        self.ws=None
        self.client_id=client_id
        self.client_secret=client_secret

    def sendReq(self, req):

        self.auth()
        self.ws.send(json.dumps(req))
        resp = json.loads(self.ws.recv())
        self.ws.close()
        # printJson(resp)
        return resp

    def auth(self):

        req = \
            {
                "jsonrpc": "2.0",
                "id": 11,
                "method": "public/auth",
                "params": {
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret
                }
            }

        self.ws = create_connection('wss://www.deribit.com/ws/api/v2',sslopt={"cert_reqs": ssl.CERT_NONE, "check_hostname": False,"ssl_version": ssl.PROTOCOL_TLSv1_2})
        self.ws.send(json.dumps(req))
        resp = json.loads(self.ws.recv())

    def close(self):
        self.ws.close()

    def getAcctSummary(self):

        req = \
            {
                "jsonrpc": "2.0",
                "id": 12,
                "method": "private/get_account_summary",
                "params": {
                    "currency": "BTC",
                    "extended": True
                }
            }

        resp = self.sendReq(req)
        return resp


    def makeMktOrder(self, Instr, amount, side):

        req = \
            {
                "jsonrpc": "2.0",
                "id": 13,
                "method": "private/" + str(side),
                "params": {
                    "instrument_name": Instr,
                    "amount": amount,
                    "type": "market",
                    "label": "myMktOrder"
                }
            }

        resp = self.sendReq(req)

        return resp

    def makeLmtOrder(self, Instr, amount, price, side):

        req = \
            {
                "jsonrpc": "2.0",
                "id": 16,
                "method": "private/" + str(side),
                "params": {
                    "instrument_name": Instr,
                    "amount": amount,
                    "type": "limit",
                    "price": price,
                    "label": "myLmtOrder"
                }
            }

        resp = self.sendReq(req)

        return resp

    def closePosition(self, Instr):

        req = \
            {
                "jsonrpc": "2.0",
                "id": 14,
                "method": "private/close_position",
                "params": {
                    "instrument_name": Instr,
                    "type": "market",
                }
            }


        resp = self.sendReq(req)

        return resp

    def getPosition(self, Instr):

        req = \
            {
                "jsonrpc": "2.0",
                "id": 15,
                "method": "private/get_position",
                "params": {
                    "instrument_name": Instr
                }
            }

        resp = self.sendReq(req)

        return resp

    def getOpenOrders(self, Instr):

        req = \
            {
                "jsonrpc": "2.0",
                "id": 17,
                "method": "private/get_open_orders_by_instrument",
                "params": {
                    "instrument_name": Instr
                }
            }

        resp = self.sendReq(req)

        return resp

    def cancelOrder(self):


        req = \
            {
            "jsonrpc": "2.0",
            "id": 8748,
            "method": "private/cancel_all",
            "params": {

            }
        }

        resp = self.sendReq(req)

        return resp

    def pingTest(self):


        req = \
            {
                "jsonrpc": "2.0",
                "id": 8212,
                "method": "public/test",
                "params": {

                }
            }

        st=time.time()
        resp = self.sendReq(req)
        et=time.time()

        print('latency: '+str(1000*(et-st))+' ms')

        return resp


def main(args):

    #print(getOrderBookInstr('BTC-PERPETUAL'))
    dv2=deribit_v2(account_credential['main'][0],account_credential['main'][1])
    printJson(dv2.getAcctSummary())

if __name__ == '__main__':
    sys.exit(main(sys.argv))