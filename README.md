# bitVolSurfacePublic
BIT Coin Volatility Surface Construction For Share\
This project construct BitCoin(BTC) volatility surface with SABR model as the smoothing function using option data from Deribit.com BTC option exchange (www.deribit.com)

QLib.py: Quant model library \
  generateBV(): generate bitcoin volatility object (BV) \
  get_vol(): vol point query API \
  m_sabr_calib(): run SABR calibration\
  m_sabr_vol(): get SABR fitted vol\
deribitv2.py: Deribit.com v2 API wrapper\
bitVolUtil.py: Utility function library\
bitVolFlash.py: snapshotting hourly bitcoin option data\
