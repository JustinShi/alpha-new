#!/usr/bin/env python3
"""
快速开始 - Alpha代币交易示例
简化版本，展示如何快速上手使用Alpha代币交易功能
"""

import asyncio
import logging
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent.parent.parent))

import aiohttp

from src.alpha_new.api_clients.alpha_token_client import AlphaTokenClient
from src.alpha_new.api_clients.mkt_order_client import MarketOrderClient, OrderSide

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def quick_start_example():
    """快速开始示例"""
    
    # 基本配置 - 请根据实际情况修改
    headers = {
        "authority": "www.binance.com",
        "accept": "*/*",
        "accept-language": "zh-CN,zh;q=0.9",
        "baggage": "sentry-environment=prod,sentry-release=20250708-e81d7e21-1942,sentry-public_key=9445af76b2ba747e7b574485f2c998f7,sentry-trace_id=3494a7f26d24498bbe4ba0161c0935cb,sentry-sample_rate=0.01,sentry-transaction=%2Falpha%2F%24chainSymbol%2F%24contractAddress,sentry-sampled=false",
        "bnc-uuid": "3614f377-ec1b-452e-882e-0450106fa73b",
        "clienttype": "web",
        "content-type": "application/json",
        "cookie": "bnc-uuid=3614f377-ec1b-452e-882e-0450106fa73b; se_gd=RZTDhDhISQFGVAKEAGwggZZHBBgwDBVV1UUVZVUZlhTUwBFNWVMN1; se_gsd=dyMkOzN8NSQmCSswJgwnMDkxDAEMDgMIVl1LU1ZTV1hVElNT1; sajssdk_2015_cross_new_user=1; BNC_FV_KEY=33d1940d67afa0baa5f7ba9e83f6829b98322c1c; BNC-Location=CN; changeBasisTimeZone=; theme=dark; se_sd=wZUUVVlhaQXUBAAwWAVZgZZFVEQIEEVV1YeVZVUZlhTUwDVNWVQN1; neo-theme=dark; futures-layout=pro; ref=CR7MOON; refstarttime=1750079874315; userPreferredCurrency=USD_USD; nft-init-compliance=true; _gcl_au=1.1.1817400148.1750165637; _gat_UA-162512367-1=1; _gat=1; lang=zh-CN; language=zh-CN; currentAccount=; _gid=GA1.2.2106874388.1750164961; OptanonAlertBoxClosed=2025-07-07T09:41:08.038Z; sensorsdata2015jssdkcross=%7B%22distinct_id%22%3A%22373396390%22%2C%22first_id%22%3A%2219762605cd38dc-0fe00b3cc0705f-26031d51-3686400-19762605cd4f53%22%2C%22props%22%3A%7B%22%24latest_traffic_source_type%22%3A%22%E7%9B%B4%E6%8E%A5%E6%B5%81%E9%87%8F%22%2C%22%24latest_search_keyword%22%3A%22%E6%9C%AA%E5%8F%96%E5%88%B0%E5%80%BC_%E7%9B%B4%E6%8E%A5%E6%89%93%E5%BC%80%22%2C%22%24latest_referrer%22%3A%22%22%2C%22%24latest_utm_source%22%3A%22ncpush%22%2C%22%24latest_utm_medium%22%3A%22web%22%2C%22%24latest_utm_campaign%22%3A%22CR7-Drop-6%22%7D%2C%22identities%22%3A%22eyIkaWRlbnRpdHlfY29va2llX2lkIjoiMTk3NjI2MDVjZDM4ZGMtMGZlMDBiM2NjMDcwNWYtMjYwMzFkNTEtMzY4NjQwMC0xOTc2MjYwNWNkNGY1MyIsIiRpZGVudGl0eV9sb2dpbl9pZCI6IjM3MzM5NjM5MCJ9%22%2C%22history_login_id%22%3A%7B%22name%22%3A%22%24identity_login_id%22%2C%22value%22%3A%22373396390%22%7D%2C%22%24device_id%22%3A%221976260d4e63c8-0b14163195aabc8-26031d51-3686400-1976260d4e7e23%22%7D; bu_m=web; bu_s=ncpush; aws-waf-token=6d7b0347-e710-48fa-9e34-92b2e2a04118:BgoAhbaAG/oUAAAA:hsY4zDcomPAx2DbtKoRh7f6y1oGqDdZ9ZRbcE76oKSKpufK67B8VYqfw0YC9FtRBN8F9+h2FTs6zVPNKt8l0+EnvEzmbMBiacmCra8iDcTTNxe1H4BHfhIUS5zUch/v5dkL+bI/Lml2DEQQryv05inoyEyu5Gp8+RzUI5JBNUbuuMRUh1umCKqEM69VFm1b5mEY=; _uetsid=ffd9c8e04b7b11f0896bcdd60e133214; _uetvid=ffd9ef804b7b11f090e5af2f27665957; BNC_FV_KEY_T=101-MqGXOKjwkfTDag9BipRUrGA4c%2Fn%2FNso5oc13wzjaMfF1I3%2BoXBFKo%2B3xNu36xpXhtAY9QI%2FQvGa4znaNvKDudQ%3D%3D-VG65fL%2FWt4ULl3rhTTprLA%3D%3D-60; BNC_FV_KEY_EXPIRE=1752541798575; r20t=web.80134366599C7DA60F6143D480565EB2; r30t=1; cr00=7C9C9C5FCDF557EB43D4FD7340C442F5; d1og=web.373396390.84A4476418A7D9F72CC53ACB6C4D8B0A; r2o1=web.373396390.9F0A32BF03B30304243414EAE99C1671; f30l=web.373396390.CC699BE2564F2FD13BD1FC39212D25C6; logined=y; _ga_3WP50LGEEC=GS2.1.s1752520195$o20$g1$t1752520241$j14$l0$h0; _ga=GA1.2.1302046031.1750164961; p20t=web.373396390.F85FCD36AA5F7184B2898680B76192B2; OptanonConsent=isGpcEnabled=0&datestamp=Tue+Jul+15+2025+13%3A08%3A37+GMT%2B0800+(%E4%B8%AD%E5%9B%BD%E6%A0%87%E5%87%86%E6%97%B6%E9%97%B4)&version=202506.1.0&browserGpcFlag=0&isIABGlobal=false&hosts=&consentId=c4eb939e-ba7d-4576-8ad4-f00583f291c4&interactionCount=3&isAnonUser=1&landingPath=NotLandingPage&groups=C0001%3A1%2CC0003%3A1%2CC0004%3A1%2CC0002%3A1&AwaitingReconsent=false&intType=6&geolocation=JP%3B13",
        "csrftoken": "0cd36474d1e788f7545cfd13ca1c92c6",
        "device-info": "eyJzY3JlZW5fcmVzb2x1dGlvbiI6IjI1NjAsMTQ0MCIsImF2YWlsYWJsZV9zY3JlZW5fcmVzb2x1dGlvbiI6IjI1NjAsMTQwMCIsInN5c3RlbV92ZXJzaW9uIjoiV2luZG93cyAxMCIsImJyYW5kX21vZGVsIjoidW5rbm93biIsInN5c3RlbV9sYW5nIjoiemgtQ04iLCJ0aW1lem9uZSI6IkdNVCswODowMCIsInRpbWV6b25lT2Zmc2V0IjotNDgwLCJ1c2VyX2FnZW50IjoiTW96aWxsYS81LjAgKFdpbmRvd3MgTlQgMTAuMDsgV2luNjQ7IHg2NCkgQXBwbGVXZWJLaXQvNTM3LjM2IChLSFRNTCwgbGlrZSBHZWNrbykgQ2hyb21lLzExNC4wLjAuMCBTYWZhcmkvNTM3LjM2IiwibGlzdF9wbHVnaW4iOiJQREYgVmlld2VyLENocm9tZSBQREYgVmlld2VyLENocm9taXVtIFBERiBWaWV3ZXIsTWljcm9zb2Z0IEVkZ2UgUERGIFZpZXdlcixXZWJLaXQgYnVpbHQtaW4gUERGIiwiY2FudmFzX2NvZGUiOiJmNzgxODZmYiIsIndlYmdsX3ZlbmRvciI6Ikdvb2dsZSBJbmMuIChOVklESUEpIiwid2ViZ2xfcmVuZGVyZXIiOiJBTkdMRSAoTlZJRElBLCBOVklESUEgR2VGb3JjZSBHVFggMTY1MCBTVVBFUiBEaXJlY3QzRDlFeCB2c18zXzAgcHNfM18wLCBudmxkdW1kLmRsbC0zMS4wLjE1LjM2MjMpIiwiYXVkaW8iOiIxMjMuNzI1NjQxMjEzODgxMzIiLCJwbGF0Zm9ybSI6IldpbjMyIiwid2ViX3RpbWV6b25lIjoiQXNpYS9TaGFuZ2hhaSIsImRldmljZV9uYW1lIjoiQ2hyb21lIFYxMTQuMC4wLjAgKFdpbmRvd3MpIiwiZmluZ2VycHJpbnQiOiI3Y2NkODg2ZGMzNmFjOWNkNGYzZWI5NGRjNmUzYTUwNCIsImRldmljZV9pZCI6IiIsInJlbGF0ZWRfZGV2aWNlX2lkcyI6IiJ9",
        "fvideo-id": "33d1940d67afa0baa5f7ba9e83f6829b98322c1c",
        "if-none-match": "W/\"024c69cba57d266de15c6dd7e974e9670\"",
        "lang": "zh-CN",
        "referer": "https://www.binance.com/zh-CN/alpha/bsc/0x5c8daeabc57e9249606d3bd6d1e097ef492ea3c5",
        "sec-ch-ua": "\"Not.A/Brand\";v=\"8\", \"Chromium\";v=\"114\", \"Google Chrome\";v=\"114\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Windows\"",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "sentry-trace": "3494a7f26d24498bbe4ba0161c0935cb-a1ca99f1677f36aa-0",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
        "x-passthrough-token": "",
        "x-trace-id": "3b07c388-75e5-46bb-a3c7-7e39a5f9c603",
        "x-ui-request-trace": "3b07c388-75e5-46bb-a3c7-7e39a5f9c603"
    }
    
    # 可选的cookies - 如果需要认证的话
    cookies = {
        "bnc-uuid": "3614f377-ec1b-452e-882e-0450106fa73b",
        "se_gd": "RZTDhDhISQFGVAKEAGwggZZHBBgwDBVV1UUVZVUZlhTUwBFNWVMN1",
        "se_gsd": "dyMkOzN8NSQmCSswJgwnMDkxDAEMDgMIVl1LU1ZTV1hVElNT1",
        "sajssdk_2015_cross_new_user": "1",
        "BNC_FV_KEY": "33d1940d67afa0baa5f7ba9e83f6829b98322c1c",
        "BNC-Location": "CN",
        "changeBasisTimeZone": "",
        "theme": "dark",
        "se_sd": "wZUUVVlhaQXUBAAwWAVZgZZFVEQIEEVV1YeVZVUZlhTUwDVNWVQN1",
        "neo-theme": "dark",
        "futures-layout": "pro",
        "ref": "CR7MOON",
        "refstarttime": "1750079874315",
        "userPreferredCurrency": "USD_USD",
        "nft-init-compliance": "true",
        "_gcl_au": "1.1.1817400148.1750165637",
        "_gat_UA-162512367-1": "1",
        "_gat": "1",
        "lang": "zh-CN",
        "language": "zh-CN",
        "currentAccount": "",
        "_gid": "GA1.2.2106874388.1750164961",
        "OptanonAlertBoxClosed": "2025-07-07T09:41:08.038Z",
        "sensorsdata2015jssdkcross": "%7B%22distinct_id%22%3A%22373396390%22%2C%22first_id%22%3A%2219762605cd38dc-0fe00b3cc0705f-26031d51-3686400-19762605cd4f53%22%2C%22props%22%3A%7B%22%24latest_traffic_source_type%22%3A%22%E7%9B%B4%E6%8E%A5%E6%B5%81%E9%87%8F%22%2C%22%24latest_search_keyword%22%3A%22%E6%9C%AA%E5%8F%96%E5%88%B0%E5%80%BC_%E7%9B%B4%E6%8E%A5%E6%89%93%E5%BC%80%22%2C%22%24latest_referrer%22%3A%22%22%2C%22%24latest_utm_source%22%3A%22ncpush%22%2C%22%24latest_utm_medium%22%3A%22web%22%2C%22%24latest_utm_campaign%22%3A%22CR7-Drop-6%22%7D%2C%22identities%22%3A%22eyIkaWRlbnRpdHlfY29va2llX2lkIjoiMTk3NjI2MDVjZDM4ZGMtMGZlMDBiM2NjMDcwNWYtMjYwMzFkNTEtMzY4NjQwMC0xOTc2MjYwNWNkNGY1MyIsIiRpZGVudGl0eV9sb2dpbl9pZCI6IjM3MzM5NjM5MCJ9%22%2C%22history_login_id%22%3A%7B%22name%22%3A%22%24identity_login_id%22%2C%22value%22%3A%22373396390%22%7D%2C%22%24device_id%22%3A%221976260d4e63c8-0b14163195aabc8-26031d51-3686400-1976260d4e7e23%22%7D",
        "bu_m": "web",
        "bu_s": "ncpush",
        "aws-waf-token": "6d7b0347-e710-48fa-9e34-92b2e2a04118:BgoAhbaAG/oUAAAA:hsY4zDcomPAx2DbtKoRh7f6y1oGqDdZ9ZRbcE76oKSKpufK67B8VYqfw0YC9FtRBN8F9+h2FTs6zVPNKt8l0+EnvEzmbMBiacmCra8iDcTTNxe1H4BHfhIUS5zUch/v5dkL+bI/Lml2DEQQryv05inoyEyu5Gp8+RzUI5JBNUbuuMRUh1umCKqEM69VFm1b5mEY=",
        "_uetsid": "ffd9c8e04b7b11f0896bcdd60e133214",
        "_uetvid": "ffd9ef804b7b11f090e5af2f27665957",
        "BNC_FV_KEY_T": "101-MqGXOKjwkfTDag9BipRUrGA4c%2Fn%2FNso5oc13wzjaMfF1I3%2BoXBFKo%2B3xNu36xpXhtAY9QI%2FQvGa4znaNvKDudQ%3D%3D-VG65fL%2FWt4ULl3rhTTprLA%3D%3D-60",
        "BNC_FV_KEY_EXPIRE": "1752541798575",
        "r20t": "web.80134366599C7DA60F6143D480565EB2",
        "r30t": "1",
        "cr00": "7C9C9C5FCDF557EB43D4FD7340C442F5",
        "d1og": "web.373396390.84A4476418A7D9F72CC53ACB6C4D8B0A",
        "r2o1": "web.373396390.9F0A32BF03B30304243414EAE99C1671",
        "f30l": "web.373396390.CC699BE2564F2FD13BD1FC39212D25C6",
        "logined": "y",
        "_ga_3WP50LGEEC": "GS2.1.s1752520195$o20$g1$t1752520241$j14$l0$h0",
        "_ga": "GA1.2.1302046031.1750164961",
        "p20t": "web.373396390.F85FCD36AA5F7184B2898680B76192B2",
        "OptanonConsent": "isGpcEnabled=0&datestamp=Tue+Jul+15+2025+13%3A08%3A37+GMT%2B0800+(%E4%B8%AD%E5%9B%BD%E6%A0%87%E5%87%86%E6%97%B6%E9%97%B4)&version=202506.1.0&browserGpcFlag=0&isIABGlobal=false&hosts=&consentId=c4eb939e-ba7d-4576-8ad4-f00583f291c4&interactionCount=3&isAnonUser=1&landingPath=NotLandingPage&groups=C0001%3A1%2CC0003%3A1%2CC0004%3A1%2CC0002%3A1&AwaitingReconsent=false&intType=6&geolocation=JP%3B13"
    }  # 请填入真实的cookies
    
    async with aiohttp.ClientSession() as session:
        # 初始化客户端
        token_client = AlphaTokenClient(session=session, headers=headers)
        order_client = MarketOrderClient(
            session=session, headers=headers, cookies=cookies
        )
        
        print("🚀 开始Alpha代币交易示例")
        print("=" * 50)
        
        # 步骤1: 查找代币信息
        print("📋 步骤1: 查找代币信息")
        token_symbol = "BR"  # 你想交易的代币符号
        
        try:
            token_info = await token_client.get_token_by_symbol(token_symbol)
            
            if token_info:
                print(f"✅ 找到代币: {token_info.symbol}")
                print(f"   Alpha ID: {token_info.alpha_id}")
                print(f"   链名称: {token_info.chain_name}")
                print(f"   合约地址: {token_info.contract_address}")
                
                # 步骤2: 构造交易对符号
                print(f"\n💱 步骤2: 构造交易对")
                trading_pair = f"ALPHA_{token_info.alpha_id}USDT"
                print(f"   交易对: {trading_pair}")
                
                # 步骤3: 获取市价报价
                print(f"\n💰 步骤3: 获取市价报价")
                quantity = 50.0  # 交易数量
                side = OrderSide.BUY  # 买入
                
                quote_result = await order_client.get_market_quote(
                    trading_pair, side, quantity
                )
                
                if quote_result.success:
                    print(f"✅ 报价成功:")
                    data = quote_result.data
                    if data:
                        print(f"   数量: {data.get('quantity', '未知')}")
                        print(f"   预估价格: {data.get('price', '未知')} USDT")
                        print(f"   预估金额: {data.get('amount', '未知')} USDT")
                        print(f"   预估手续费: {data.get('fee', '未知')} USDT")
                else:
                    print(f"❌ 获取报价失败: {quote_result.error}")
                
                # 步骤4: 模拟下单（注释掉以避免实际交易）
                print(f"\n📝 步骤4: 模拟下单")
                print("   ⚠️  实际下单已注释，如需真实交易请取消注释并谨慎操作")
                
                # 取消注释下面的代码以执行真实交易（风险自负）
                # print("   🔄 正在下单...")
                # order_result = await order_client.place_market_order(
                #     trading_pair, side, quantity
                # )
                # 
                # if order_result.success:
                #     print(f"✅ 下单成功: {order_result.data}")
                # else:
                #     print(f"❌ 下单失败: {order_result.error}")
                
            else:
                print(f"❌ 未找到代币: {token_symbol}")
                
        except Exception as e:
            print(f"❌ 执行过程中发生错误: {e}")
        
        # 显示统计信息
        print(f"\n📊 统计信息:")
        print(f"   Token客户端: {token_client.get_stats()}")
        print(f"   订单客户端: {order_client.get_stats()}")
        
        print("\n✨ 示例完成!")


async def list_available_tokens():
    """列出可用的代币"""
    
    headers = {
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }
    
    async with aiohttp.ClientSession() as session:
        client = AlphaTokenClient(session=session, headers=headers)
        
        print("📋 获取所有可用的Alpha代币...")
        
        try:
            token_list = await client.get_token_list()
            
            print(f"✅ 找到 {len(token_list.data)} 个代币:")
            print("-" * 80)
            print(f"{'序号':<4} {'符号':<12} {'Alpha ID':<15} {'链名称':<15} {'合约地址':<42}")
            print("-" * 80)
            
            for i, token in enumerate(token_list.data[:20], 1):  # 只显示前20个
                contract_addr = token.contract_address[:40] + "..." if len(token.contract_address) > 42 else token.contract_address
                print(f"{i:<4} {token.symbol:<12} {token.alpha_id:<15} {token.chain_name:<15} {contract_addr:<42}")
            
            if len(token_list.data) > 20:
                print(f"... 还有 {len(token_list.data) - 20} 个代币")
                
        except Exception as e:
            print(f"❌ 获取代币列表失败: {e}")


async def search_token_by_pattern():
    """按模式搜索代币"""
    
    headers = {
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }
    
    async with aiohttp.ClientSession() as session:
        client = AlphaTokenClient(session=session, headers=headers)
        
        # 搜索包含特定模式的代币
        search_pattern = "BTC"  # 搜索包含BTC的代币
        print(f"🔍 搜索包含'{search_pattern}'的代币...")
        
        try:
            token_list = await client.get_token_list()
            
            # 筛选匹配的代币
            matching_tokens = [
                token for token in token_list.data 
                if search_pattern.upper() in token.symbol.upper()
            ]
            
            print(f"✅ 找到 {len(matching_tokens)} 个匹配的代币:")
            
            for token in matching_tokens:
                print(f"   {token.symbol} (Alpha ID: {token.alpha_id})")
                
        except Exception as e:
            print(f"❌ 搜索失败: {e}")


def main_menu():
    """主菜单"""
    print("🎯 Alpha代币交易示例菜单")
    print("=" * 40)
    print("1. 快速交易示例")
    print("2. 列出所有可用代币")
    print("3. 搜索代币")
    print("0. 退出")
    print("=" * 40)
    
    choice = input("请选择操作 (0-3): ").strip()
    return choice


async def main():
    """主函数"""
    while True:
        choice = main_menu()
        
        if choice == "0":
            print("👋 再见!")
            break
        elif choice == "1":
            await quick_start_example()
        elif choice == "2":
            await list_available_tokens()
        elif choice == "3":
            await search_token_by_pattern()
        else:
            print("❌ 无效选择，请重试")
        
        if choice != "0":
            input("\n按回车键继续...")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 程序被用户中断，再见!") 