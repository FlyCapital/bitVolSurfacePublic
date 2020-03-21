#Model Library
import math
import copy
import numpy as np
from scipy import interp
from scipy.optimize import minimize
import QuantLib as ql
from datetime import timedelta
from Util import *

class BSmodel:
    
    def __init__(self, strike, matDate, OptType, SpotFwd='spot'):
        
        if strike==0:
            strike=strike+0.001
        
        if OptType=='call':
            payoff = ql.PlainVanillaPayoff(ql.Option.Call, strike)
        elif OptType=='put':
            payoff = ql.PlainVanillaPayoff(ql.Option.Put, strike)
            
        self.SpotFwd=SpotFwd
        
        #setup European call object
        exercise = ql.EuropeanExercise(matDate)
        self.european_option = ql.VanillaOption(payoff, exercise)
    
    def price(self, valDate, und_price, volatility, risk_free_rate, dividend_rate=0):

        day_count = ql.Actual365Fixed()
        calendar = ql.UnitedStates()
        ql.Settings.instance().evaluationDate = valDate

        #form BS model input
        und_handle = ql.QuoteHandle(
                    ql.SimpleQuote(und_price)
                )
        flat_ts = ql.YieldTermStructureHandle(
            ql.FlatForward(valDate, 
                           risk_free_rate, 
                           day_count)
        )
        dividend_yield = ql.YieldTermStructureHandle(
            ql.FlatForward(valDate, 
                           dividend_rate, 
                           day_count)
        )
        flat_vol_ts = ql.BlackVolTermStructureHandle(
            ql.BlackConstantVol(valDate, 
                                calendar, 
                                volatility, 
                                day_count)
        )
        
        #pricing
        if self.SpotFwd=='spot':
            self.process = ql.BlackScholesMertonProcess(und_handle, dividend_yield, flat_ts, flat_vol_ts)
        elif self.SpotFwd=='forward':
            self.process = ql.BlackProcess(und_handle, flat_ts, flat_vol_ts)           
            
        self.european_option.setPricingEngine(ql.AnalyticEuropeanEngine(self.process))

    def view(self):
    
        resultDict={'price':self.european_option.NPV(),
                  'delta':self.european_option.delta(),
                  'gamma':self.european_option.gamma(),
                  'vega':self.european_option.vega(),
                  'theta':self.european_option.thetaPerDay()
                  }
        
        return resultDict
    
    def impv(self, optPx):
    
        return self.european_option.impliedVolatility(optPx, self.process)
    
class yieldCurve:
    
    def __init__(self, curveInstr):
        
        self.calendar = ql.UnitedStates()
        self.business_convention = ql.Unadjusted
        self.day_count = ql.Actual365Fixed()
        self.end_of_month = False
        self.settlement_days = 0
        self.curveInstr=curveInstr
        
    def view(self, calc_date, dateList):
    
        ql.Settings.instance().evaluationDate = calc_date
        
        depo_helpers = [
                        ql.DepositRateHelper(ql.QuoteHandle(ql.SimpleQuote(r)),
                        d,
                        self.settlement_days,
                        self.calendar,
                        self.business_convention,
                        self.end_of_month,
                        self.day_count)
                        for r, d in zip(self.curveInstr['cashRate'], self.curveInstr['cashRateDate'])
                        ]
  
        rate_helpers=depo_helpers
        yieldcurve = ql.PiecewiseLinearZero(calc_date, rate_helpers, self.day_count)

        zero_rate=[]
        
        for dt in dateList:
            yrs = self.day_count.yearFraction(calc_date, dt)
            print(yrs)
            compounding = ql.Compounded
            freq = ql.Continuous
            zero_rate.append(yieldcurve.zeroRate(yrs, compounding, freq).rate())

        return {'zeroRate':zero_rate}
    
def m_sabr_vol(Input):

    f=Input['forward']
    k=Input['strike']
    expiry=Input['expiry']
    alpha=Input['alpha']
    beta=Input['beta']
    nu=Input['nu']
    rho=Input['rho']
    volType=Input['volType']

    if volType=='lognormal':
        if k != f:
            A = alpha/((f*k)**((1-beta)/2)*(1+(1-beta)**2/24*(math.log(f/k))**2+(1-beta)**4/1920*math.log(f/k)**4))
            B = 1+((1-beta)**2/24*alpha**2/((f*k)**(1-beta))+1/4*alpha*beta*rho*nu/((f*k)**((1-beta)/2))+(2-3*rho**2)/24*nu**2)*expiry
            z = nu/alpha*(f*k)**((1-beta)/2)*math.log(f/k)

            X = math.log((math.sqrt(1-2*rho*z+z**2)+z-rho)/(1-rho))
            return A*z/X*B
        else:

            B =1+((1-beta)**2/24*alpha**2/(f**(2-2*beta))+1/4*alpha*beta*rho*nu/(f**(1-beta))+(2-3*rho**2)/24*nu**2)*expiry
            return alpha*f**(beta-1)*B
    elif volType=='normal':
        if k != f:
            A = f-k
            B = 1+(beta*(beta-2)/24*alpha**2/(((f+k)/2)**(2-2*beta))+1/4*alpha*beta*rho*nu/(((f+k)/2)**(1-beta))+(2-3*rho**2)/24*nu**2)*expiry
            z = nu/alpha*(f**(1-beta)-k**(1-beta))/(1-beta)

            X = math.log((math.sqrt(1-2*rho*z+z**2)+z-rho)/(1-rho))
            return A*nu/X*B
        else:
            B = 1+(beta*(beta-2)/24*alpha**2/(f**(2-2*beta))+1/4*alpha*beta*rho*nu/(f**(1-beta))+(2-3*rho**2)/24*nu**2)*expiry
            return alpha*f**beta*B


def m_sabr_calib_func(param, Input):
    alpha, nu, rho=param

    f = Input['forward']
    expiry=Input['expiry']
    kList=Input['strike']
    volList=Input['volatility']
    volType=Input['volType']

    objFuncVal=0
    for i in range(0,len(kList)):
        inputSABR={'forward':f,
                   'strike':kList[i],
                   'expiry':expiry,
                   'alpha':alpha,
                   'beta':Input['beta'],
                   'nu':nu,
                   'rho':rho,
                   'volType': volType
                   }

        volSABR=m_sabr_vol(inputSABR)
        #objFuncVal+=1/(1+(f-kList[i])**2)*(volSABR/volList[i]-1)**2
        objFuncVal+=(volSABR/volList[i]-1)**2
        #objFuncVal+=abs(volSABR/volList[i]-1)
        #objFuncVal+=(volSABR-volList[i])**2

    return objFuncVal

def m_sabr_calib(Input, calibType='fixBeta'):

    if calibType=='fixBeta':
        
        x0=np.array([np.median(Input['volatility']),1,0.0])
        lb=0.001
        bnds=[(lb,10), (lb,20), (-0.999,0.999)]
        
        try:
            result = minimize(m_sabr_calib_func, x0, args=(Input,), method='TNC', bounds=bnds, options={'maxiter': 99999999, 'disp': False}) #TNC, L-BFGS-B
        except:
            result = minimize(m_sabr_calib_func, x0, args=(Input,), method='L-BFGS-B', bounds=bnds, options={'maxiter': 99999999, 'disp': False}) #TNC, L-BFGS-B

        calibResult={'alpha':result.x[0],
                     'beta':Input['beta'],
                     'nu': result.x[1],
                     'rho': result.x[2]
                     }

        return calibResult

    elif calibType=='MF': #Mengfei-Fabozzi (2016)

        None
        
    
def get_vol(qLibVol, exp, stk):

    #interpolate on strike dimension for each expiry
    volInfo=qLibVol['volInfo']
    volDate=qLibVol['volDate']
    fwdCrv=qLibVol['fwdCurve']['rate']
    yieldCurve=qLibVol['yieldCurve']['rate']
    
    sabrVolExp=[]
    expYfracList=[]

    for i in range(0,len(volInfo.keys())):
        volExp=list(volInfo.keys())[i]
        expYfrac=getYearFrac(volDate, volExp)

        sabrInput={'forward':fwdCrv[i+1],
                   'strike':stk,
                   'expiry':expYfrac,
                   'volType':'lognormal'
                  }

        if volInfo[volExp]['sabrParam']=={}:
            if i!=len(volInfo.keys())-1:
                j=i+1
                while volInfo[list(volInfo.keys())[j]]['sabrParam']=={}:
                    j+=1
                sabrInput.update(volInfo[list(volInfo.keys())[j]]['sabrParam'])
            else:
                sabrInput.update(volInfo[list(volInfo.keys())[i-1]]['sabrParam'])
        else:
            sabrInput.update(volInfo[volExp]['sabrParam'])

        sabrVolTmp=m_sabr_vol(sabrInput)
        expYfracList.append(expYfrac)
        sabrVolExp.append(sabrVolTmp**2) #variance

    #interpolate on expiry dimension in variance space

    sabrVol=interp(exp, expYfracList, sabrVolExp)

    return math.sqrt(sabrVol)
    
def generateBV(mktSide='Mid',snapId=None):

    #load option chain data
    if snapId==None:
        chainData=getLatestOptionChain()
    else:
        chainData=getOptionChainViaId(snapId)

    futData=chainData.loc[((chainData['InstrType']=='future') | (chainData['InstrType']=='spot')) & (chainData['Ticker']!='BTC-PERPETUAL')]
    optData=chainData.loc[chainData['InstrType']=='option']

    futData=futData.sort_values(by=['Maturity'])
    optData=optData.sort_values(by=['Maturity','Strike','CallPut'],ascending=[1, 1, 0])

    snapDateTime=futData['DateTime'].tolist()[0]

    futPx=[]
    futExp=[]
    futExpYfrac=[]

    for index, row in futData.iterrows():
        futPx.append((row['BidPx']+row['AskPx'])/2)
        futExp.append(row['Maturity'])
        futExpYfrac.append(getYearFrac(snapDateTime, row['Maturity']))

    optExp=[]
    optExpYfrac=[]

    for optE in optData['Maturity'].unique():
        optExp.append(optE)
        optExpYfrac.append(getYearFrac(snapDateTime, optE))


    #construct yield/future curve
    bitYield=[]
    futCrv=[futPx[0]]
    for i in range(1,len(futPx)):
        bitYield.append(math.log(futPx[i]/futPx[0])/futExpYfrac[i]) #in math unit

    bitYieldCrv=interp(optExpYfrac,futExpYfrac, [bitYield[0]]+bitYield)

    for i in range(0,len(optExpYfrac)):
        futCrv.append(futCrv[0]*math.exp(bitYieldCrv[i]*optExpYfrac[i]))

    #calibrate vol smile

    volInfo={}

    S=futCrv[0]

    for i in range(0,len(optExp)):
        calibResult={}
        fwd=futCrv[i+1]
        optPx=[]
        strike=[]
        vol=[]
        optType=[]
        optTicker=[]
        r=bitYieldCrv[i]
        stkATM=None

        if optExpYfrac[i]>1.0/365:
            optDataSub=optData.loc[optData['Maturity']==optExp[i]]
            #print('=====',optExp[i],'=====')
            #print(optDataSub)
            
            #find ATM strike
            stkATM=getATMstk(fwd, optDataSub['Strike'].unique().tolist())

            for index, row in optDataSub.iterrows():  
                if (row['CallPut']=='call' and row['Strike']>=stkATM) or (row['CallPut']=='put' and row['Strike']<=stkATM):
                    if row['BidPx']!=-999999 and row['AskPx']!=-999999 and row['BidPx']*S>5.0 and 3*row['BidPx']*S>row['AskPx']*S:
                        if mktSide=='Mid':
                            optPxTmp=(row['BidPx']+row['AskPx'])/2*S
                        elif mktSide=='Ask':
                            optPxTmp=row['AskPx']*S
                        elif mktSide=='Bid':
                            optPxTmp=row['BidPx']*S
                            
                        optPx.append(optPxTmp)
                        strike.append(row['Strike'])
                        optType.append(row['CallPut'])
                        optTicker.append(row['Ticker'])
                        BSpricing=BSmodel(row['Strike'], py2ql_date(optExp[i]), row['CallPut'], 'forward')
                        BSpricing.price(py2ql_date(snapDateTime), fwd, 1, r)
                        vol.append(BSpricing.impv(optPxTmp))

            if len(strike)>=5:
                sabrCalibInput={'forward':fwd,
                                'expiry':optExpYfrac[i],
                                'strike': strike,
                                'volatility': vol,
                                'beta':1,
                                'volType':'lognormal'
                               }
                calibResult=m_sabr_calib(sabrCalibInput)


        volInfo[optExp[i]]={'ATMstrike': stkATM, 'strike':strike,'mktVol':vol,'sabrParam':calibResult,'optPx': optPx, 'optType':optType, 'optTicker':optTicker}
        
        
    qlibVol={'volDate':snapDateTime,
             'volInfo':volInfo,
             'fwdCurve':{'rate':futCrv,'tenor':[0]+optExpYfrac},
             'yieldCurve':{'rate':bitYieldCrv,'tenor':optExpYfrac}
            }

    
    return qlibVol

def fv(x, T, K0):
    
    return 2/T*((x-K0)/K0-math.log(x/K0))


def VarSwapTho(F0,r,vDate, Strike, qlibVol):
    
    volDate=qlibVol['volDate']
    T=getYearFrac(volDate, vDate)
    
    optPort=0
    
    for i in range(0,len(Strike)):
        k=Strike[i]
        if i==0:
            dk=Strike[i+1]-Strike[i]
        else:
            dk=Strike[i]-Strike[i-1]

        if k<F0:
            vol=get_vol(qlibVol,T,k)
            p=BSmodel(k, py2ql_date(vDate), 'put', 'forward')
            p.price(py2ql_date(volDate), F0, vol, r)
            optPort+=p.view()['price']/k**2*dk
        else:
            vol=get_vol(qlibVol,T,k)
            c=BSmodel(k, py2ql_date(vDate), 'call', 'forward')
            c.price(py2ql_date(volDate), F0, vol, r)
            optPort+=c.view()['price']/k**2*dk
        
    return math.exp(r*T)*2/T*optPort


def VarSwapMkt(F0, r, vDate, volDate, Strike, ATMStrike, optPx, optType, kInt=500):
    
    T=getYearFrac(volDate, vDate)
    
    K0=ATMStrike
    
    Kc=[]
    Kp=[]
    
    Pxc=[]
    Pxp=[]
    
    for i in range(0,len(optType)):
        if optType[i]=='call':
            Kc.append(Strike[i])
            Pxc.append(optPx[i])
        elif optType[i]=='put':
            Kp.append(Strike[i])
            Pxp.append(optPx[i])
            
    Kc.append(Kc[-1]+kInt)
    Kp=[Kp[0]-kInt]+Kp
    
    wc0=(fv(Kc[1], T, K0)-fv(Kc[0], T, K0))/(Kc[1]-Kc[0])
    wp0=(fv(Kp[-2], T, K0)-fv(Kp[-1], T, K0))/(Kp[-1]-Kp[-2])
    
    wc=[wc0]
    wp=[wp0]
        
    for i in range(1,len(Kc)-1):
        w=(fv(Kc[i+1], T, K0)-fv(Kc[i], T, K0))/(Kc[i+1]-Kc[i])-sum(wc)
        wc.append(w)
        
    for i in range(len(Kp)-2,0,-1):
        w=(fv(Kp[i-1], T, K0)-fv(Kp[i], T, K0))/(Kp[i]-Kp[i-1])-sum(wp)
        wp=[w]+wp
        
    wTotal=wp+wc
    optPxTotal=Pxp+Pxc
    

    optPort=0
    wFinal=[]

    for i in range(0,len(optPxTotal)):
        
        optPort+=wTotal[i]*math.exp(r*T)*10000*optPxTotal[i]
        wFinal.append(wTotal[i]*math.exp(r*T)*10000)
        
    return optPort, wFinal#-2/T*(math.log(K0/F0)+(F0/K0-1))+math.exp(r*T)*optPort
        
        
    
        
    
    
            
            






