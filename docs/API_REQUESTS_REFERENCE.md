# Alpha交易系统 API请求参考文档

## 📋 目录
- [用户信息API](#用户信息api)
- [Alpha积分API](#alpha积分api)
- [Alpha代币API](#alpha代币api)
- [空投服务API](#空投服务api)
- [市价订单API](#市价订单api)
- [限价订单API](#限价订单api)
- [订单历史API](#订单历史api)
- [WebSocket连接](#websocket连接)

---

## 🔐 认证说明

所有API请求都需要以下认证信息：
- **Headers**: 包含用户认证信息的HTTP请求头
- **Cookies**: 用户会话Cookie（可选，部分API需要）
- **设备类型**: PC端或Mobile端（影响Headers格式）

---

## 👤 用户信息API

### 获取用户基础信息
**端点**: `POST https://www.binance.com/bapi/accounts/v1/private/account/user/base-detail`

**请求方法**: `POST`

**请求头**: 
```json
{
  "Content-Type": "application/json",
  "User-Agent": "Mozilla/5.0...",
  "X-Trace-Id": "uuid",
  "Cookie": "session_cookies..."
}
```

**请求体**:
```json
{}
```

**响应数据**:
```json
{
  "code": "000000",
  "message": null,
  "messageDetail": null,
  "data": {
    "userId": "123456789",
    "email": "user@example.com",
    "firstName": "用户名",
    "lastName": "",
    "mobile": "+86138****1234",
    "registerTime": 1640995200000,
    "isVip": false,
    "vipLevel": 0,
    "kycStatus": "VERIFIED",
    "accountStatus": "NORMAL"
  },
  "success": true
}
```

---

## 🏆 Alpha积分API

### 查询用户Alpha积分
**端点**: `GET https://www.binance.com/bapi/defi/v1/private/wallet-direct/buw/tge/common/user-score`

**请求方法**: `GET`

**请求头**: 
```json
{
  "Content-Type": "application/json",
  "User-Agent": "Mozilla/5.0...",
  "X-Trace-Id": "uuid",
  "Cookie": "session_cookies..."
}
```

**响应数据**:
```json
{
    "code": "000000",
    "message": null,
    "messageDetail": null,
    "data": {
        "isPass": null,
        "sumScore": "182",
        "startDatetime": 1751414400000,
        "endDatetime": 1752624000000,
        "list": [
            {
                "date": "2025-07-16",
                "scoreTime": null,
                "totalScore": "19",
                "balanceScore": "2",
                "alphaVolumeScore": "17",
                "balanceSnapshot": "2439.5358330403837744",
                "alphaVolume": "131874.25961200"
            },
            {
                "date": "2025-07-15",
                "scoreTime": null,
                "totalScore": "19",
                "balanceScore": "2",
                "alphaVolumeScore": "17",
                "balanceSnapshot": "2426.7318459078539505",
                "alphaVolume": "131344.91743000"
            },
            {
                "date": "2025-07-14",
                "scoreTime": null,
                "totalScore": "19",
                "balanceScore": "2",
                "alphaVolumeScore": "17",
                "balanceSnapshot": "2443.9590195885972848",
                "alphaVolume": "131356.55491400"
            },
            {
                "date": "2025-07-13",
                "scoreTime": null,
                "totalScore": "19",
                "balanceScore": "2",
                "alphaVolumeScore": "17",
                "balanceSnapshot": "2131.8279966752756989",
                "alphaVolume": "131625.42442800"
            },
            {
                "date": "2025-07-12",
                "scoreTime": null,
                "totalScore": "19",
                "balanceScore": "2",
                "alphaVolumeScore": "17",
                "balanceSnapshot": "2283.6967379043688498",
                "alphaVolume": "133870.14264400"
            },
            {
                "date": "2025-07-11",
                "scoreTime": null,
                "totalScore": "19",
                "balanceScore": "2",
                "alphaVolumeScore": "17",
                "balanceSnapshot": "2140.3326734895559535",
                "alphaVolume": "131782.38882600"
            },
            {
                "date": "2025-07-10",
                "scoreTime": null,
                "totalScore": "19",
                "balanceScore": "2",
                "alphaVolumeScore": "17",
                "balanceSnapshot": "2116.2524814553369146",
                "alphaVolume": "132287.71009200"
            },
            {
                "date": "2025-07-09",
                "scoreTime": null,
                "totalScore": "19",
                "balanceScore": "2",
                "alphaVolumeScore": "17",
                "balanceSnapshot": "2235.1466280287564565",
                "alphaVolume": "131736.64582800"
            },
            {
                "date": "2025-07-08",
                "scoreTime": null,
                "totalScore": "19",
                "balanceScore": "2",
                "alphaVolumeScore": "17",
                "balanceSnapshot": "2252.8633343010650694",
                "alphaVolume": "131782.59605200"
            },
            {
                "date": "2025-07-07",
                "scoreTime": null,
                "totalScore": "20",
                "balanceScore": "2",
                "alphaVolumeScore": "18",
                "balanceSnapshot": "2152.4639548850400811",
                "alphaVolume": "262929.46640200"
            },
            {
                "date": "2025-07-06",
                "scoreTime": null,
                "totalScore": "20",
                "balanceScore": "2",
                "alphaVolumeScore": "18",
                "balanceSnapshot": "3214.7605144907785377",
                "alphaVolume": "266911.92442600"
            },
            {
                "date": "2025-07-05",
                "scoreTime": null,
                "totalScore": "19",
                "balanceScore": "2",
                "alphaVolumeScore": "17",
                "balanceSnapshot": "3157.4463095562587231",
                "alphaVolume": "131623.99931800"
            },
            {
                "date": "2025-07-04",
                "scoreTime": null,
                "totalScore": "19",
                "balanceScore": "2",
                "alphaVolumeScore": "17",
                "balanceSnapshot": "3116.1430511946111277",
                "alphaVolume": "136996.55029200"
            },
            {
                "date": "2025-07-03",
                "scoreTime": null,
                "totalScore": "19",
                "balanceScore": "2",
                "alphaVolumeScore": "17",
                "balanceSnapshot": "3104.6675454655302069",
                "alphaVolume": "137089.68145000"
            },
            {
                "date": "2025-07-02",
                "scoreTime": null,
                "totalScore": "19",
                "balanceScore": "2",
                "alphaVolumeScore": "17",
                "balanceSnapshot": "2937.4858089896022466",
                "alphaVolume": "131520.30414600"
            }
        ],
        "userSpendList": [
            {
                "id": 2299876,
                "spendTime": 1752494408000,
                "spendScore": "15.000000000000000000",
                "bizType": "AIRDROP",
                "bizId": "7d60e69a607c11f0ab54067961fb7a23"
            },
            {
                "id": 2007149,
                "spendTime": 1751806879000,
                "spendScore": "15.000000000000000000",
                "bizType": "AIRDROP",
                "bizId": "5500d26a5a2d11f0974e06e301540dd7"
            },
            {
                "id": 1988517,
                "spendTime": 1751706020000,
                "spendScore": "15.000000000000000000",
                "bizType": "AIRDROP",
                "bizId": "e38b2ed6596511f0974e06e301540dd7"
            },
            {
                "id": 1960615,
                "spendTime": 1751616021000,
                "spendScore": "15.000000000000000000",
                "bizType": "AIRDROP",
                "bizId": "6fb2666d58a311f0974e06e301540dd7"
            },
            {
                "id": 1831818,
                "spendTime": 1751537047000,
                "spendScore": "15.000000000000000000",
                "bizType": "AIRDROP",
                "bizId": "c7003f4e57ef11f0974e06e301540dd7"
            },
            {
                "id": 1801602,
                "spendTime": 1751530125000,
                "spendScore": "15.000000000000000000",
                "bizType": "AIRDROP",
                "bizId": "0cc6255157d711f0974e06e301540dd7"
            },
            {
                "id": 1786319,
                "spendTime": 1751450434000,
                "spendScore": "15.000000000000000000",
                "bizType": "AIRDROP",
                "bizId": "8d25f403572011f0974e06e301540dd7"
            }
        ]
    },
    "success": true
}
```

---


### 获取Alpha代币列表
**端点**: `GET https://www.binance.com/bapi/defi/v1/public/wallet-direct/buw/wallet/cex/alpha/all/token/list`

**请求方法**: `GET`

**请求头**: 
```json
{
  "Content-Type": "application/json",
  "User-Agent": "Mozilla/5.0..."
}
```

**响应数据**:
```json
{
  "code": "000000",
  "message": null,
  "data": [
    {
      "tokenId": "D2CBD14EC0F59E15DE4CD960582A2464",
      "chainId": "56",
      "chainIconUrl": "https://bin.bnbstatic.com/image/admin_mgs_image_upload/20250228/d0216ce4-a3e9-4bda-8937-4a6aa943ccf2.png",
      "chainName": "BSC",
      "contractAddress": "0xf39e4b21c84e737df08e2c3b32541d856f508e48",
      "name": "Yooldo Games",
      "symbol": "ESPORTS",
      "iconUrl": "https://bin.bnbstatic.com/images/web3-data/public/token/logos/3261fe7717574f9ab8...png",
      "price": "0.07988133663780544223",
      "percentChange24h": "6.20",
      "volume24h": "15392227.453426329082801080973",
      "marketCap": "12924800.26799692055281400000",
      "fdv": "71893202.97402489800700000000",
      "liquidity": "1193154.8708987476",
      "totalSupply": "900000000",
      "circulatingSupply": "161800000",
      "holders": "938",
      "decimals": 18,
      "listingCex": false,
      "hotTag": true,
      "cexCoinName": "",
      "canTransfer": false,
      "denomination": 1,
      "offline": false,
      "tradeDecimal": 8,
      "alphaId": "ALPHA_283",
      "offsell": false,
      "priceHigh24h": "0.09627645162770056931",
      "priceLow24h": "0.0484430693174859344",
      "onlineTge": false,
      "onlineAirdrop": true,
      "score": 4411,
      "cexOffDisplay": false
    }
  ],
  "success": true
}
```

---

## 🎁 空投服务API

### 查询空投列表
**端点**: `POST https://www.binance.com/bapi/defi/v1/friendly/wallet-direct/buw/growth/query-alpha-airdrop`

**请求方法**: `POST`

**请求头**: 
```json
{
  "Content-Type": "application/json",
  "User-Agent": "Mozilla/5.0...",
  "X-Trace-Id": "uuid",
  "Cookie": "session_cookies..."
}
```

**请求体**:
```json
{
  "page": 1,
  "rows": 50
}
```

**响应数据**:
```json
{
  "code": "000000",
  "message": null,
    "messageDetail": null,
  "data": {
        "configs": [
      {
                "configId": "d31b3759cf90450f812eb7dc9c92b8a0",
                "configName": "Giants Protocol",
                "configDescription": "Giants Protocol",
                "configSequence": 66,
                "pointsThreshold": 165.000000000000000000,
                "deductPoints": 15.000000000000000000,
                "binanceChainId": "CT_501",
                "chainIconUrl": "https://bin.bnbstatic.com/image/admin_mgs_image_upload/20250303/42065e0a-3808-400e-b589-61c2dbfc0eac.png",
                "contractAddress": "GpEKud3JpJDc5D3Gek8UVCb6vAiahGmDUZMQFnf5btai",
                "tokenSymbol": "G",
                "tokenLogo": "static/buw/icons/g.png",
                "alphaId": "ALPHA_282",
                "airdropAmount": 88000.000000000000000000,
                "displayStartTime": 1752842700000,
                "claimStartTime": 1752843600000,
                "claimEndTime": 1752843605000,
                "twoStageFlag": true,
                "stageMinutes": 0,
                "secondPointsThreshold": 165.000000000000000000,
                "claimedRatio": "100",
                "status": "ended",
                "claimInfo": {
                    "canClaim": false,
                    "claimLocation": "alpha",
                    "address": "",
                    "isEligible": true,
                    "isSecondEligible": true,
                    "isClaimed": true,
                    "claimStatus": "success",
                    "isClaimedInFirstStage": false,
                    "isClaimedInSecondStage": true
                },
                "claimPreCheckInfo": {
                    "beforeDisplayMinutes": 15,
                    "isDisplayPreCheck": false,
                    "isUserPreCheckPass": false
                }
            },
            {
                "configId": "fca16136c67847dc8dfb91d2e78a9992",
                "configName": "Taker Protocol",
                "configDescription": "Taker Protocol",
                "configSequence": 65,
                "pointsThreshold": 165.000000000000000000,
                "deductPoints": 15.000000000000000000,
          "binanceChainId": "56",
                "chainIconUrl": "https://bin.bnbstatic.com/image/admin_mgs_image_upload/20250228/d0216ce4-a3e9-4bda-8937-4a6aa943ccf2.png",
                "contractAddress": "0xc19539eb93444523ec8f1432624924d2e6226546",
                "tokenSymbol": "TAKER",
                "tokenLogo": "static/buw/icons/taker.png",
                "alphaId": "ALPHA_281",
                "airdropAmount": 1000.000000000000000000,
                "displayStartTime": 1752831900000,
                "claimStartTime": 1752832800000,
                "claimEndTime": 1752832806000,
                "twoStageFlag": true,
                "stageMinutes": 0,
                "secondPointsThreshold": 165.000000000000000000,
                "claimedRatio": "100",
                "status": "ended",
                "claimInfo": {
                    "canClaim": false,
                    "claimLocation": "",
                    "address": "",
                    "isEligible": true,
                    "isSecondEligible": true,
                    "isClaimed": false,
                    "claimStatus": "none",
                    "isClaimedInFirstStage": false,
                    "isClaimedInSecondStage": false
                },
                "claimPreCheckInfo": {
                    "beforeDisplayMinutes": 15,
                    "isDisplayPreCheck": false,
                    "isUserPreCheckPass": false
                }
            },
            {
                "configId": "712e563114f1493f99cefe0d3f270f6a",
                "configName": "Caldera",
                "configDescription": "Caldera",
                "configSequence": 64,
                "pointsThreshold": 224.000000000000000000,
                "deductPoints": 15.000000000000000000,
                "binanceChainId": "56",
                "chainIconUrl": "https://bin.bnbstatic.com/image/admin_mgs_image_upload/20250228/d0216ce4-a3e9-4bda-8937-4a6aa943ccf2.png",
                "contractAddress": "0x00312400303d02c323295f6e8b7309bc30fb6bce",
                "tokenSymbol": "ERA",
                "tokenLogo": "static/buw/icons/caldera.png",
                "alphaId": "ALPHA_280",
                "airdropAmount": 150.000000000000000000,
                "displayStartTime": 1752758100000,
                "claimStartTime": 1752759000000,
                "claimEndTime": 1752823805000,
                "twoStageFlag": true,
                "stageMinutes": 1080,
                "secondPointsThreshold": 140.000000000000000000,
                "claimedRatio": "",
                "status": "ended",
        "claimInfo": {
                    "canClaim": false,
                    "claimLocation": "",
                    "address": "",
                    "isEligible": false,
                    "isSecondEligible": false,
          "isClaimed": false,
                    "claimStatus": "none",
                    "isClaimedInFirstStage": false,
                    "isClaimedInSecondStage": false
                },
                "claimPreCheckInfo": {
                    "beforeDisplayMinutes": 15,
                    "isDisplayPreCheck": false,
                    "isUserPreCheckPass": false
                }
            },
            {
                "configId": "3749156a0c1e4ddfa69c606d9b5aec97",
                "configName": "TAC",
                "configDescription": "TAC",
                "configSequence": 63,
                "pointsThreshold": 224.000000000000000000,
                "deductPoints": 15.000000000000000000,
                "binanceChainId": "56",
                "chainIconUrl": "https://bin.bnbstatic.com/image/admin_mgs_image_upload/20250228/d0216ce4-a3e9-4bda-8937-4a6aa943ccf2.png",
                "contractAddress": "0x1219c409fabe2c27bd0d1a565daeed9bd9f271de",
                "tokenSymbol": "TAC",
                "tokenLogo": "static/buw/icons/tac.png",
                "alphaId": "ALPHA_277",
                "airdropAmount": 1875.000000000000000000,
                "displayStartTime": 1752572700000,
                "claimStartTime": 1752573600000,
                "claimEndTime": 1752638410000,
                "twoStageFlag": true,
                "stageMinutes": 1080,
                "secondPointsThreshold": 140.000000000000000000,
                "claimedRatio": "",
                "status": "ended",
                "claimInfo": {
                    "canClaim": false,
                    "claimLocation": "",
                    "address": "",
          "isEligible": true,
                    "isSecondEligible": true,
                    "isClaimed": true,
                    "claimStatus": "success",
                    "isClaimedInFirstStage": true,
                    "isClaimedInSecondStage": false
                },
                "claimPreCheckInfo": {
                    "beforeDisplayMinutes": 15,
                    "isDisplayPreCheck": false,
                    "isUserPreCheckPass": false
                }
            },
            {
                "configId": "7d60e69a607c11f0ab54067961fb7a23",
                "configName": "Chainbase",
                "configDescription": "Chainbase",
                "configSequence": 62,
                "pointsThreshold": 160.000000000000000000,
                "deductPoints": 15.000000000000000000,
                "binanceChainId": "56",
                "chainIconUrl": "https://bin.bnbstatic.com/image/admin_mgs_image_upload/20250228/d0216ce4-a3e9-4bda-8937-4a6aa943ccf2.png",
                "contractAddress": "0xc32cc70741c3a8433dcbcb5ade071c299b55ffc8",
                "tokenSymbol": "C",
                "tokenLogo": "static/buw/icons/chainbase.png",
                "alphaId": "ALPHA_275",
                "airdropAmount": 750.000000000000000000,
                "displayStartTime": 1752493500000,
                "claimStartTime": 1752494400000,
                "claimEndTime": 1752494407000,
                "twoStageFlag": true,
                "stageMinutes": 0,
                "secondPointsThreshold": 160.000000000000000000,
                "claimedRatio": "",
                "status": "ended",
                "claimInfo": {
                    "canClaim": false,
                    "claimLocation": "",
                    "address": "",
                    "isEligible": false,
                    "isSecondEligible": false,
                    "isClaimed": false,
                    "claimStatus": "none",
                    "isClaimedInFirstStage": false,
                    "isClaimedInSecondStage": false
                },
                "claimPreCheckInfo": {
                    "beforeDisplayMinutes": 15,
                    "isDisplayPreCheck": false,
                    "isUserPreCheckPass": false
        }
      }
    ],
        "userInfo": {
            "isRiskHit": false,
            "isCompliancePass": true,
            "hasWeb3Wallet": null
        },
        "pageInfo": {
            "curPage": 1,
            "total": 65
        }
  },
  "success": true
}
```

### 领取空投
**端点**: `POST https://www.binance.com/bapi/defi/v1/private/wallet-direct/buw/growth/claim-alpha-airdrop`

**请求方法**: `POST`

**请求头**: 
```json
{
  "Content-Type": "application/json",
  "User-Agent": "Mozilla/5.0...",
  "X-Trace-Id": "uuid",
  "Cookie": "session_cookies..."
}
```

**请求体**:
```json
{
  "configId": "airdrop_001"
}
```

**响应数据**:
```json
{
    "code": "000000",
    "message": "领取成功",
    "data": {
        "claimStatus": "success"
    },
    "success": true
}
```

---

## 💱 市价订单API

### 获取市价报价
**端点**: `POST https://www.binance.com/bapi/defi/v1/private/wallet-direct/swap/cex/get-quote`

**请求方法**: `POST`

**请求头**: 
```json
{
  "Content-Type": "application/json",
  "User-Agent": "Mozilla/5.0...",
  "X-Trace-Id": "uuid",
  "Cookie": "session_cookies..."
}
```

**请求体**:
```json
{
  "fromAsset": "USDT",
  "toAsset": "ALPHA_261",
  "fromAmount": "100.0",
  "slippage": "0.5"
}
```

**响应数据**:
```json
{
  "code": "000000",
  "message": null,
  "data": {
    "quoteId": "quote_123456",
    "fromAsset": "USDT",
    "toAsset": "ALPHA_261",
    "fromAmount": "100.0",
    "toAmount": "4000.0",
    "price": "0.025",
    "slippage": "0.5",
    "fee": "0.1",
    "feeAsset": "USDT",
    "validTime": 30,
    "expireTime": 1641081630000
  },
  "success": true
}
```

### 执行市价买入订单
**端点**: `POST https://www.binance.com/bapi/defi/v2/private/wallet-direct/swap/cex/buy/pre/payment`

**请求方法**: `POST`

**请求头**: 
```json
{
  "Content-Type": "application/json",
  "User-Agent": "Mozilla/5.0...",
  "X-Trace-Id": "uuid",
  "Cookie": "session_cookies..."
}
```

**请求体**:
```json
{
  "quoteId": "quote_123456",
  "fromAsset": "USDT",
  "toAsset": "ALPHA_261",
  "fromAmount": "100.0",
  "slippage": "0.5"
}
```

**响应数据**:
```json
{
  "code": "000000",
  "message": "订单提交成功",
  "data": {
    "orderId": "order_789012",
    "status": "PENDING",
    "fromAsset": "USDT",
    "toAsset": "ALPHA_261",
    "fromAmount": "100.0",
    "toAmount": "4000.0",
    "executedAmount": "0.0",
    "fee": "0.1",
    "createTime": 1641081600000
  },
  "success": true
}
```

### 执行市价卖出订单
**端点**: `POST https://www.binance.com/bapi/defi/v2/private/wallet-direct/swap/cex/sell/pre/payment`

**请求方法**: `POST`

**请求头**: 同买入订单

**请求体**:
```json
{
  "quoteId": "quote_123456",
  "fromAsset": "ALPHA_261",
  "toAsset": "USDT",
  "fromAmount": "4000.0",
  "slippage": "0.5"
}
```

**响应数据**: 同买入订单格式

---

## 📊 限价订单API

### 下限价订单
**端点**: `POST https://www.binance.com/bapi/asset/v1/private/alpha-trade/order/place`

**请求方法**: `POST`

**请求头**: 
```json
{
  "Content-Type": "application/json",
  "User-Agent": "Mozilla/5.0...",
  "X-Trace-Id": "uuid",
  "Cookie": "session_cookies..."
}
```

**请求体**:
```json
{
  "baseAsset": "ALPHA_261",
  "quoteAsset": "USDT",
  "side": "BUY",
  "type": "LIMIT",
  "price": "0.025",
  "quantity": "4000.0",
  "timeInForce": "GTC"
}
```

**响应数据**:
```json
{
  "code": "000000",
  "message": "订单提交成功",
  "data": {
    "orderId": "limit_order_345678",
    "status": "NEW",
    "baseAsset": "ALPHA_261",
    "quoteAsset": "USDT",
    "side": "BUY",
    "type": "LIMIT",
    "price": "0.025",
    "quantity": "4000.0",
    "executedQty": "0.0",
    "cumQuote": "0.0",
    "timeInForce": "GTC",
    "createTime": 1641081600000
  },
  "success": true
}
```

### 撤销指定订单
**端点**: `POST https://www.binance.com/bapi/asset/v1/private/alpha-trade/order/cancel`

**请求方法**: `POST`

**请求头**:
```json
{
  "Content-Type": "application/json",
  "User-Agent": "Mozilla/5.0...",
  "X-Trace-Id": "uuid",
  "Cookie": "session_cookies..."
}
```

**请求体**:
```json
{
  "orderId": "22306445",
  "baseAsset": "ALPHA_118",
  "quoteAsset": "USDT"
}
```

**响应数据**:
```json
{
  "code": "000000",
  "message": "订单撤销成功",
  "data": {
    "orderId": "22306445",
    "status": "CANCELED"
  },
  "success": true
}
```

---

### 查询订单历史
```
GET /bapi/defi/v1/private/alpha-trade/order/get-order-history-merge
```
**请求参数:**
```
baseAsset=ALPHA_22&endTime=1752854399999&orderStatus=FILLED&page=1&rows=500&startTime=1737129600000 
```
不包含baseAsset=ALPHA_22可查所有代币
'''
**返回数据:**
```json
{
  "code": "000000",
  "data": [
    {
      "kind": "LIMIT",
      "orderId": "22522520",
      "symbol": "ALPHA_261USDT",
      "status": "FILLED",
      "price": "0.18670189",
      "avgPrice": "0.1875",
      "origQty": "1362.93",
      "executedQty": "1362.93",
      "type": "LIMIT",
      "side": "SELL",
      "time": 1752848863114,
      "updateTime": 1752848863158,
      "baseAsset": "ALPHA_261",
      "quoteAsset": "USDT",
      "fromToken": null,
      "fromTokenAmount": null,
      "fromBinanceChainId": null,
      "fromContractAddress": null,
      "toToken": null,
      "toTokenAmount": null,
      "toBinanceChainId": null,
      "toContractAddress": null,
      "alphaId": "ALPHA_261"
    }
  ],
  "total": 18,
  "success": true
}
```

---
---

## 🔌 WebSocket连接

### 获取ListenKey
**端点**: `POST https://www.binance.com/bapi/defi/v1/private/alpha-trade/get-listen-key`

**请求方法**: `POST`

**请求头**:
```json
{
  "Content-Type": "application/json",
  "User-Agent": "Mozilla/5.0...",
  "X-Trace-Id": "uuid",
  "Cookie": "session_cookies..."
}
```

**请求体**:
```json
{}
```

**响应数据**:
```json
{
  "code": "000000",
  "message": null,
  "data": "pqia91ma19a5s61cv6a81va65sdf19v8a65a1a5s61cv6a81va65sdf19v8a65a1",
  "success": true
}
```
或者
```json
{
  "listenKey": "pqia91ma19a5s61cv6a81va65sdf19v8a65a1a5s61cv6a81va65sdf19v8a65a1"
}
```

### WebSocket连接端点
**订单推送**: `wss://nbstream.binance.com/w3w/stream`

**价格推送**: `wss://nbstream.binance.com/w3w/wsa/stream`

### WebSocket订阅和消息格式

#### 订单推送订阅
**连接**: `wss://nbstream.binance.com/w3w/stream`

**订阅消息**:
```json
{
  "method": "SUBSCRIBE",
  "params": ["alpha@{listenKey}"],
  "id": 3
}
```

**订单更新消息**:
```json
{
  "stream": "alpha@82d94da7148b1877e8771415d35cdff1",
  "data": {
    "s": "ALPHA_261USDT",
    "c": "client_order_123",
    "S": "BUY",
    "o": "LIMIT",
    "f": "GTC",
    "q": "4000.0",
    "p": "0.025",
    "ap": "0.025",
    "P": "0.00",
    "x": "TRADE",
    "X": "FILLED",
    "i": "123456",
    "z": "4000.0",
    "last_executed_price": "0.025",
    "n": "0.1",
    "N": "USDT",
    "t": "789012",
    "m": false,
    "ot": "LIMIT",
    "st": 2,
    "order_creation_time": 1641081550000,
    "Z": "100.0",
    "Y": "100.0",
    "Q": "4000.0",
    "ba": "ALPHA_261",
    "qa": "USDT",
    "id": 123456,
    "e": "executionReport",
    "T": 1641081600000,
    "u": 1641081600000,
    "E": 1641081600000
  }
}
```

#### 价格推送订阅
**连接**: `wss://nbstream.binance.com/w3w/wsa/stream`

**订阅消息**:
```json
{
  "method": "SUBSCRIBE",
  "params": ["came@0xff7d6a96ae471bbcd7713af9cb1feeb16cf56b41@56@kline_1s"],
  "id": 4
}
```

**价格推送消息**:
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

---


### 钱包余额查询
**端点**: `GET /bapi/asset/v2/private/asset-service/wallet/asset?needAlphaAsset=1&quoteAsset=USDT`

**返回数据**: 
```
{
	"code": "000000",
	"message": null,
	"messageDetail": null,
	"data": [{
		"asset": "USDT",
		"assetName": "TetherUS",
		"amount": "1742.31735804",
		"logoUrl": "https://bin.bnbstatic.com/image/admin_mgs_image_upload/20240508/6180cdb6-8480-4a3c-a8a9-8a193a89fc5e.png",
		"valuationAmount": "1742.31735804",
		"profit": null,
		"profitRatio": null,
		"avgCost": null,
		"avgBuyCost": null,
		"isCexAsset": true,
		"coinBusinessType": null,
		"chainId": null,
		"contractAddress": null
	}, {
		"asset": "SUI",
		"assetName": "Sui",
		"amount": "10.00247395",
		"logoUrl": "https://bin.bnbstatic.com/image/admin_mgs_image_upload/20250426/29b2a289-c671-4a28-ba59-4b57bb748900.jpg",
		"valuationAmount": "40.02589977",
		"profit": null,
		"profitRatio": null,
		"avgCost": null,
		"avgBuyCost": null,
		"isCexAsset": true,
		"coinBusinessType": null,
		"chainId": null,
		"contractAddress": null
	}, {
		"asset": "RIF",
		"assetName": "Rootstock Infrastructure Framework",
		"amount": "12.31781698",
		"logoUrl": "https://bin.bnbstatic.com/image/admin_mgs_image_upload/20240812/f3256fa0-72ca-49c8-8e7f-8d384e43f5c3.png",
		"valuationAmount": "0.76616821",
		"profit": null,
		"profitRatio": null,
		"avgCost": null,
		"avgBuyCost": null,
		"isCexAsset": true,
		"coinBusinessType": null,
		"chainId": null,
		"contractAddress": null
	}, {
		"asset": "BGSC",
		"assetName": null,
		"amount": "8.385",
		"logoUrl": null,
		"valuationAmount": "0.05948356622071221",
		"profit": null,
		"profitRatio": null,
		"avgCost": null,
		"avgBuyCost": null,
		"isCexAsset": false,
		"coinBusinessType": "ALPHA",
		"chainId": "56",
		"contractAddress": "0xa4b68d48d7bc6f04420e8077e6f74bdef809dea3"
	}, {
		"asset": "A",
		"assetName": "Vaulta",
		"amount": "0.07260693",
		"logoUrl": "https://bin.bnbstatic.com/image/admin_mgs_image_upload/20250526/096003f9-3b66-4add-b0c7-2ec27e14948b.png",
		"valuationAmount": "0.04137869",
		"profit": null,
		"profitRatio": null,
		"avgCost": null,
		"avgBuyCost": null,
		"isCexAsset": true,
		"coinBusinessType": null,
		"chainId": null,
		"contractAddress": null
	}, {
		"asset": "BROCCOLI714",
		"assetName": "CZ'S Dog (broccoli.ngo)",
		"amount": "0.14545969",
		"logoUrl": "https://bin.bnbstatic.com/image/admin_mgs_image_upload/20250327/19199629-9ee8-41fd-82a9-551d5b5690af.png",
		"valuationAmount": "0.00735298",
		"profit": null,
		"profitRatio": null,
		"avgCost": null,
		"avgBuyCost": null,
		"isCexAsset": true,
		"coinBusinessType": null,
		"chainId": null,
		"contractAddress": null
	}, {
		"asset": "HUMA",
		"assetName": "Huma Finance",
		"amount": "0.11824722",
		"logoUrl": "https://bin.bnbstatic.com/image/admin_mgs_image_upload/20250522/4e324a81-0373-4d96-ad65-a2d1cec2cf46.png",
		"valuationAmount": "0.00408071",
		"profit": null,
		"profitRatio": null,
		"avgCost": null,
		"avgBuyCost": null,
		"isCexAsset": true,
		"coinBusinessType": null,
		"chainId": null,
		"contractAddress": null
	}],
	"success": true
}
'''

---

### 查询资产详情
```
GET /bapi/asset/v3/private/asset-service/wallet/asset-detail?asset=ERA&quoteAsset=USDT
```
**请求参数:**
- asset: 资产币种（如 ERA）
- quoteAsset: 计价币种（如 USDT）

**返回数据:**
```json
{
    "code": "000000",
    "message": null,
    "messageDetail": null,
    "data": {
        "asset": "ERA",
        "assetName": "Caldera",
        "logoUrl": "https://bin.bnbstatic.com/image/admin_mgs_image_upload/20250716/63cbc507-41ad-41a4-907d-b6ba909dc636.png",
        "assetDetails": [
            {
                "accountType": "SAVING",
                "uniAccountType": "PM_2",
                "walletName": "理财账户",
                "amount": "0.09557061",
                "valuationAmount": "0.11431201"
            }
        ]
    },
    "success": true
}
```

---

## 📊 API汇总表

| 功能分类 | API端点 | 方法 | 认证 | 描述 |
|---------|---------|------|------|------|
| 用户信息 | `/bapi/accounts/v1/private/account/user/base-detail` | POST | ✅ | 获取用户基础信息 |
| Alpha积分 | `/bapi/defi/v1/private/wallet-direct/buw/tge/common/user-score` | GET | ✅ | 查询Alpha积分 |
| 钱包余额 | `/bapi/asset/v2/private/asset-service/wallet/asset?needAlphaAsset=1&quoteAsset=USDT` | GET | ✅ | 查询Alpha钱包余额 |
| Alpha代币 | `/bapi/defi/v1/public/wallet-direct/buw/wallet/cex/alpha/all/token/list` | GET | ❌ | 获取代币列表 |
| 空投查询 | `/bapi/defi/v1/friendly/wallet-direct/buw/growth/query-alpha-airdrop` | POST | ✅ | 查询空投列表 |
| 空投领取 | `/bapi/defi/v1/private/wallet-direct/buw/growth/claim-alpha-airdrop` | POST | ✅ | 领取空投 |
| 市价报价 | `/bapi/defi/v1/private/wallet-direct/swap/cex/get-quote` | POST | ✅ | 获取市价报价 |
| 市价买入 | `/bapi/defi/v2/private/wallet-direct/swap/cex/buy/pre/payment` | POST | ✅ | 执行买入订单 |
| 市价卖出 | `/bapi/defi/v2/private/wallet-direct/swap/cex/sell/pre/payment` | POST | ✅ | 执行卖出订单 |
| 限价订单 | `/bapi/asset/v1/private/alpha-trade/order/place` | POST | ✅ | 下限价订单 |
| 撤销订单 | `/bapi/asset/v1/private/alpha-trade/order/cancel` | POST | ✅ | 撤销指定订单 |
| 订单历史 | `/bapi/defi/v1/private/alpha-trade/order/get-order-history-merge` | POST | ✅ | 查询订单历史 |
| ListenKey | `/bapi/defi/v1/private/alpha-trade/get-listen-key` | POST | ✅ | 获取WebSocket密钥 |

---

