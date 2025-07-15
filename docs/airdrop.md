多用户空投自动领取整体框架 

## 用户配置 
--**全局配置**--
代币名称
数量
定时执行时间
--**用户自定义**--
用户名
是否启用
代币名称
数量
定时执行时间
## 定时启动模块
--**根据设置时间定时执行**--

## 空投信息查询模块 （airdrop query）
--**发送代币名称查询空投，返回空投详细信息字段**--

--**发送地址**--
''''
POST https://www.binance.com/bapi/defi/v1/friendly/wallet-direct/buw/growth/query-alpha-airdrop
''''

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
## 空投领取模块 （airdrop claim）
--**发送configId字段值领取空投，返回成功失败**--

--**发送地址**--
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

## alpha钱包余额查询模块 
--**查询用户钱包返回代币余额信息字段**--

## 市价单交易模块
--**发送市场报价获取价格**--
--**发送市价单交易**--