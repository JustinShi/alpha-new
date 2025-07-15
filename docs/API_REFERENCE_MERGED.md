# 币安Alpha交易平台API参考文档

## 目录
- [用户会话管理](#用户会话管理)
- [钱包余额查询](#钱包余额查询)
- [空投服务](#空投服务)
- [交易服务](#交易服务)
- [订单历史查询](#订单历史查询)
- [WebSocket连接](#websocket连接)

---

## 用户管理
post https://www.binance.com/bapi/accounts/v1/private/account/user/base-detail
**发送数据**
{}
**返回数据**
{
  "code": "000000",
  "message": null,
  "messageDetail": null,
  "data": {
    "email": "15549084991@163.com",
    "tradeLevel": 0,
    "agentId": 10000001,
    "agentRewardRatio": 0.2,
    "referralRewardRatio": null,
    "buyerCommission": 0,
    "makerCommission": 0.001,
    "sellerCommission": 0,
    "takerCommission": 0.001,
    "gauth": false,
    "mobileSecurity": true,
    "mobileNo": "155*****991",
    "mobileCode": "CN",
    "withdrawWhiteStatus": false,
    "commissionStatus": 1,
    "userId": "1107038055",
    "forbidAppTrade": "0",
    "lastLoginIp": "91.199.84.114",
    "lastLoginCountry": "HK",
    "lastLoginCity": "Hong Kong",
    "lastLoginTime": 1752086883000,
    "idPhoto": "1",
    "idPhotoMsg": null,
    "firstName": "施莲",
    "middleName": "",
    "lastName": "",
    "companyName": "",
    "authenticationType": 1,
    "jumioEnable": 1,
    "level": 2,
    "levelWithdraw": [
      2,
      100,
      101
    ],
    "certificateAddress": null,
    "isExistMarginAccount": true,
    "isUserProtocol": false,
    "securityKeyStatus": {
      "origins": [],
      "withdrawAndApi": true,
      "resetPassword": false,
      "login": false
    },
    "orderConfirmStatus": {
      "limitOrder": false,
      "marketOrder": false,
      "stopLossOrder": true,
      "marginAutoBorrow": true,
      "marginAutoRepay": true,
      "oco": false,
      "autoBorrowRepay": true,
      "trailingStopOrder": true,
      "stopMarketOrder": true,
      "marginAutoTransfer": true
    },
    "isExistFutureAccount": true,
    "isReferralSettingSubmitted": false,
    "nickName": "P2P-271381c5",
    "nickColor": "225|#ABE800|#00837B",
    "isAssetSubAccount": false,
    "isExistFiatAccount": false,
    "isExistMiningAccount": false,
    "isExistCardAccount": true,
    "isSignedLVTRiskAgreement": false,
    "isBindEmail": true,
    "isMobileUser": true,
    "userFastWithdrawEnabled": true,
    "isNoEmailSubUser": false,
    "isManagerSubUserFunctionEnabled": false,
    "isAllowBatchAddWhiteAddress": false,
    "isLockWhiteAddress": false,
    "isUserNeedKyc": false,
    "isCommonMerchantSubUser": false,
    "isEnterpriseRoleUser": false,
    "isCustodianSubUser": false,
    "isOneButtonClearPosition": false,
    "isPortfolioMarginRetailUser": true,
    "isOneButtonManagerSubUserClearPosition": false,
    "isUserPersonalOrEnterpriseAccount": false,
    "registerChannel": null,
    "isExistOptionAccount": false,
    "isSubGroupFunctionEnable": false,
    "isExistCopyTradingLeader": false,
    "needSetPassword": false,
    "isBindFido": true,
    "brokerParentUser": false,
    "subUser": false,
    "brokerSubUser": false,
    "subUserEnabled": false,
    "parentUser": false
  },
  "success": true
}

get https://www.binance.com/bapi/accounts/v1/private/account/user/userInfo
**返回数据**
{
    "code": "000000",
    "message": null,
    "messageDetail": null,
    "data": {
        "parent": null,
        "isBindEmail": true,
        "email": "15549084991@163.com",
        "isBindMobile": true,
        "mobileCode": "CN",
        "mobile": "15549084991",
        "userId": "1107038055",
        "switchAccountShowEntity": null
    },
    "success": true
}

## 钱包余额查询

### 查询Alpha钱包余额
```
GET https://www.binance.com/bapi/defi/v1/private/wallet-direct/cloud-wallet/alpha?includeCex=1
get https://www.binance.com/bapi/defi/v1/private/wallet-direct/cloud-wallet/alpha
```
**请求头:**
```json
{
  "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
  "Accept": "application/json"
}
```

**返回数据:**
```json
{
  "code": "000000",
  "data": {
    "totalValuation": "0.01310512",
    "list": [
      {
        "chainId": "56",
        "contractAddress": "0xff7d6a96ae471bbcd7713af9cb1feeb16cf56b41",
        "cexAsset": false,
        "name": "Bedrock",
        "symbol": "BR",
        "tokenId": "ALPHA_118",
        "free": "0.00847907",
        "freeze": "0",
        "locked": "0",
        "withdrawing": "0",
        "amount": "0.00847907",
        "valuation": "0.00060725"
      }
    ]
  },
  "success": true
}
```

---

## 空投服务

### 查询空投列表
```
POST https://www.binance.com/bapi/defi/v1/friendly/wallet-direct/buw/growth/query-alpha-airdrop
```
**发送数据:**
```json
{
  "page": 1,
  "rows": 50
}
```

**返回数据:**
```json
{
  "success": true,
  "code": "000000",
  "data": {
    "tokens": [
      {
        "configInfo": {
          "configId": "string",
          "tokenSymbol": "string",
          "airdropAmount": "float",
          "configName": "string",
          "configDescription": "string",
          "displayStartTime": "timestamp",
          "claimStartTime": "timestamp",
          "claimEndTime": "timestamp",
          "contractAddress": "string",
          "binanceChainId": "string",
          "alphaId": "string"
        },
        "claimInfo": {
          "canClaim": "boolean",
          "isClaimed": "boolean",
          "isEligible": "boolean",
          "claimStatus": "string"
        }
      }
    ]
  }
}
```

### 领取空投
```
POST https://www.binance.com/bapi/defi/v1/private/wallet-direct/buw/growth/claim-alpha-airdrop
```
**发送数据:**
```json
{
  "configId": "string"
}
```

---

## 交易服务

### 下限价单
```
POST https://www.binance.com/bapi/asset/v1/private/alpha-trade/order/place
```
**发送数据:**
```json
{
  "baseAsset": "ALPHA_118",
  "quoteAsset": "USDT",
  "side": "BUY",
  "price": 0.07234126,
  "quantity": 13.82,
  "paymentDetails": [
    {
      "amount": 0.99975621,
      "paymentWalletType": "CARD"
    }
  ]
}
```

**返回数据:**
```json
{
  "code": "000000",
  "data": "22306445",
  "success": true
}
```
### 市价单获取报价
'''
post https://www.binance.com/bapi/defi/v1/private/wallet-direct/swap/cex/get-quote
'''
**发送数据**
''' json
{"fromToken":"BR","fromContractAddress":"0xff7d6a96ae471bbcd7713af9cb1feeb16cf56b41","fromBinanceChainId":"56","fromCoinAmount":"152.08479","toToken":"USDT","toContractAddress":"","toBinanceChainId":"56"}
'''
**返回数据**
''' json
{
    "code": "000000",
    "message": null,
    "messageDetail": null,
    "data": {
        "minInputAmount": "43.037515121451686178",
        "maxInputAmount": null,
        "minReceivedAmount": "10.696244584654442804",
        "isMinReceiveTooLow": false,
        "toCoinAmount": "10.886823053792881508",
        "mevProtection": true,
        "rate": {
            "fromToRatio": "0.071583904306228660",
            "basicFromToRatio": "0.071583904306228660",
            "networkFee": "0.08171689",
            "tradingFee": "0.00000000"
        },
        "mode": {
            "priorityOnPrice": {
                "slippage": "0.01",
                "networkFee": "0.08171689",
                "customNetworkFeeMode": null
            },
            "priorityOnSuccess": {
                "slippage": "0.012",
                "networkFee": "0.08580274",
                "customNetworkFeeMode": null
            },
            "priorityOnCustom": null
        },
        "extra": "{\"uniQuoteId\":\"2dad0f5b1d21499b8f101523222a0c4d\"}",
        "priorityMode": "priorityOnPrice",
        "mevDisableWarning": false,
        "fromCoinAmountInUsd": "10.8900630799847973694128807",
        "toCoinAmountInUsd": "10.8877092659805973038195387699790028",
        "minReceivedAmountInUsd": "10.6971152833207913298616769309861564"
    },
    "success": true
}
'''

### 下市价单
```
POST https://www.binance.com/bapi/asset/v1/private/alpha-trade/order/place
```
**发送数据:**
```json
{
  "baseAsset": "ALPHA_118",
  "quoteAsset": "USDT",
  "side": "BUY",
  "type": "MARKET",
  "quantity": 13.82,
  "paymentDetails": [
    {
      "amount": 0.99975621,
      "paymentWalletType": "CARD"
    }
  ]
}
```
'''
**返回数据:**
{
    "code": "000000",
    "message": null,
    "messageDetail": null,
    "data": {
        "orderId": "25071400000882505678",
        "direction": "sell",
        "fromToken": "BR",
        "fromTokenAmount": "152.08479",
        "fromBinanceChainId": "56",
        "fromTokenId": "063898D505CAF5E575D14DC5D5022B2B",
        "fromContractAddress": "0xff7d6a96ae471bbcd7713af9cb1feeb16cf56b41",
        "toToken": "USDT",
        "toTokenAmount": "10.886823053792881508",
        "toBinanceChainId": "56",
        "toTokenId": "A97B597E63B7FCC51BB9E307E13EC2E3",
        "toContractAddress": "0x55d398326f99059ff775485246999027b3197955",
        "status": "processing",
        "dbCreateTime": 1752505383609,
        "dbUpdateTime": 1752505383609,
        "feeDetail": {
            "id": 31,
            "direction": "TO",
            "ratePercent": 0.0000,
            "defaultRatePercent": 0.005,
            "rateCoinAmount": 0,
            "rateFiatValue": 0.00000000,
            "coinPriceInUSD": null,
            "decimals": null
        },
        "intermediateTokens": null,
        "source": "BINANCE_ALPHA_PAY",
        "fromBridgeFee": 0,
        "nativeTokenPrice": 698.4349737306806,
        "vendorFromCoinAmount": 152.084790000000000000,
        "chainGasFeeInUsd": 0.08171689,
        "chainGasTokenAmount": null,
        "chainToAmount": 10.886823053792881508,
        "uniQuoteId": "2dad0f5b1d21499b8f101523222a0c4d",
        "quotePrice": null,
        "chainAmount": null,
        "slippage": 0.01
    },
    "success": true
}
'''

### 撤单
```
POST https://www.binance.com/bapi/asset/v1/private/alpha-trade/order/cancel
```
**发送数据:**
```json
{
  "orderId": "22306445",
  "baseAsset": "ALPHA_118",
  "quoteAsset": "USDT"
}
```

**返回数据:**
```json
{
  "code": "000000",
  "data": {
    "orderId": "22306445",
    "status": "CANCELED"
  },
  "success": true
}
```

---

## 订单历史查询

### 查询订单历史
```
GET https://www.binance.com/bapi/defi/v1/private/alpha-trade/order/get-order-history-web
```
**请求参数:**
```
page=1&rows=2000&orderStatus=FILLED&startTime=timestamp&endTime=timestamp&baseAsset=string&side=string
```

**返回数据:**
```json
{
  "code": "000000",
  "data": [
    {
      "orderId": "string",
      "baseAsset": "string",
      "quoteAsset": "string",
      "side": "BUY",
      "orderType": "string",
      "price": "float",
      "quantity": "float",
      "executedQty": "float",
      "cumQuote": "float",
      "status": "string",
      "time": "timestamp"
    }
  ]
}
```

---

## WebSocket连接

### 获取ListenKey
```
POST https://www.binance.com/bapi/defi/v1/private/alpha-trade/stream/get-listen-key
```
**返回数据:**
```json
{
  "listenKey": "string"
}
```

### 价格推送订阅
```
WebSocket: wss://nbstream.binance.com/w3w/wsa/stream
```
**订阅消息:**
```json
{
  "method": "SUBSCRIBE",
  "params": ["came@0xff7d6a96ae471bbcd7713af9cb1feeb16cf56b41@56@kline_1s"],
  "id": 4
}
```

**推送数据:**
```json
{
  "stream": "came@0xff7d6a96ae471bbcd7713af9cb1feeb16cf56b41@56@kline_1s",
  "data": {
    "e": "kline",
    "ca": "0xff7d6a96ae471bbcd7713af9cb1feeb16cf56b41@56",
    "k": {
      "ot": 1752172979000,
      "ct": 1752172980000,
      "i": "1s",
      "o": 0.07156000,
      "c": 0.07156472358283535693430646555729,
      "h": 0.07162070848390285,
      "l": 0.07156000,
      "v": 4535.899309725156
    }
  }
}
```

### 订单推送订阅
```
WebSocket: wss://nbstream.binance.com/w3w/stream
```
**订阅消息:**
```json
{
  "method": "SUBSCRIBE",
  "params": ["alpha@82d94da7148b1877e8771415d35cdff1"],
  "id": 3
}
```

**推送数据:**
```json
{
  "stream": "alpha@82d94da7148b1877e8771415d35cdff1",
  "data": {
    "s": "ALPHA_118USDT",
    "c": "web_7e240ee64714421b9d45d0b78b9afdbc",
    "S": "BUY",
    "o": "LIMIT",
    "f": "GTC",
    "q": "7.73000000",
    "p": "0.12929528",
    "ap": "0.128003000",
    "P": "0",
    "x": "TRADE",
    "X": "FILLED",
    "i": "19933949",
    "l": "7.73000000",
    "z": "7.73000000",
    "L": "0.12800300",
    "n": "0.00077300",
    "N": "ALPHA_118",
    "t": "1152681",
    "m": false,
    "ot": "LIMIT",
    "st": 1,
    "O": 1751959949045,
    "Z": "0.98946319",
    "Y": "0.98946319",
    "Q": "0",
    "ba": "ALPHA_118",
    "qa": "USDT",
    "id": 1884441972,
    "e": "executionReport",
    "T": 1751959949922,
    "u": 1751959949922,
    "E": 1751959949925
  }
}
```

---

## 核心模块

### 获取Alpha代币信息
```
GET https://www.binance.com/bapi/defi/v1/public/wallet-direct/buw/wallet/cex/alpha/all/token/list
```
**返回数据:**
```json
{
  "success": true,
  "code": "000000",
  "data": [
    {
      "alphaId": "string",
      "chainId": "string",
      "chainName": "string",
      "contractAddress": "string",
      "symbol": "string",
      "tokenId": "string",
      "totalSupply": "string"
    }
  ]
}
```

---

## 重要说明

### 精度要求
- **价格精度**: 最多6位小数
- **数量精度**: 最多2位小数
- **金额精度**: 最多8位小数
- **所有数值都向下取整，不进行四舍五入**

### 支付类型
- **买单**: `paymentWalletType` 必须为 `"CARD"`
- **卖单**: `paymentWalletType` 必须为 `"ALPHA"`
- **金额计算**: `price * quantity` 必须等于 `paymentDetails[0].amount`

### 认证要求
- 大部分API需要有效的用户认证头
- 支持Headers和Cookies认证
- 需要定期更新用户会话以保持有效性

### 常见错误码
- `000000`: 成功
- `481001`: 参数格式错误
- `481002`: 价格或金额不正确
- `481003`: 余额不足 