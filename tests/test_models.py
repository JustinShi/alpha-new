"""
Alpha代币模型测试
"""
import pytest
from src.alpha_new.models.alpha_token_model import AlphaTokenInfo, AlphaTokenListResponse


class TestAlphaTokenInfo:
    """AlphaTokenInfo模型测试"""
    
    def test_create_token_info(self):
        """测试创建代币信息"""
        token_data = {
            "alphaId": "ALPHA_118",
            "chainId": "56",
            "chainName": "BSC",
            "contractAddress": "0xff7d6a96ae471bbcd7713af9cb1feeb16cf56b41",
            "symbol": "BR",
            "tokenId": "063898D505CAF5E575D14DC5D5022B2B",
            "totalSupply": "1000000000"
        }
        
        token = AlphaTokenInfo(**token_data)
        
        assert token.alpha_id == "ALPHA_118"
        assert token.chain_id == "56"
        assert token.symbol == "BR"
        assert token.chain_name == "BSC"
    
    def test_token_string_representation(self):
        """测试代币字符串表示"""
        token_data = {
            "alphaId": "ALPHA_118",
            "chainId": "56",
            "chainName": "BSC",
            "contractAddress": "0xff7d6a96ae471bbcd7713af9cb1feeb16cf56b41",
            "symbol": "BR",
            "tokenId": "063898D505CAF5E575D14DC5D5022B2B",
            "totalSupply": "1000000000"
        }
        
        token = AlphaTokenInfo(**token_data)
        
        # 测试 __str__ 方法
        assert "BR" in str(token)
        assert "BSC" in str(token)
        assert "ALPHA_118" in str(token)
        
        # 测试 __repr__ 方法
        repr_str = repr(token)
        assert "AlphaTokenInfo" in repr_str
        assert "ALPHA_118" in repr_str


class TestAlphaTokenListResponse:
    """AlphaTokenListResponse模型测试"""
    
    def test_create_token_list_response(self):
        """测试创建代币列表响应"""
        response_data = {
            "success": True,
            "code": "000000",
            "data": [
                {
                    "alphaId": "ALPHA_118",
                    "chainId": "56",
                    "chainName": "BSC",
                    "contractAddress": "0xff7d6a96ae471bbcd7713af9cb1feeb16cf56b41",
                    "symbol": "BR",
                    "tokenId": "063898D505CAF5E575D14DC5D5022B2B",
                    "totalSupply": "1000000000"
                }
            ]
        }
        
        response = AlphaTokenListResponse(**response_data)
        
        assert response.success is True
        assert response.code == "000000"
        assert len(response.data) == 1
        assert response.data[0].symbol == "BR"
    
    def test_get_token_by_symbol(self):
        """测试根据符号获取代币"""
        response_data = {
            "success": True,
            "code": "000000",
            "data": [
                {
                    "alphaId": "ALPHA_118",
                    "chainId": "56",
                    "chainName": "BSC",
                    "contractAddress": "0xff7d6a96ae471bbcd7713af9cb1feeb16cf56b41",
                    "symbol": "BR",
                    "tokenId": "063898D505CAF5E575D14DC5D5022B2B",
                    "totalSupply": "1000000000"
                },
                {
                    "alphaId": "ALPHA_119",
                    "chainId": "1",
                    "chainName": "ETH",
                    "contractAddress": "0x1234567890abcdef",
                    "symbol": "BTC",
                    "tokenId": "BTC_TOKEN_ID",
                    "totalSupply": "21000000"
                }
            ]
        }
        
        response = AlphaTokenListResponse(**response_data)
        
        # 测试存在的代币
        br_token = response.get_token_by_symbol("BR")
        assert br_token is not None
        assert br_token.symbol == "BR"
        assert br_token.alpha_id == "ALPHA_118"
        
        # 测试大小写不敏感
        br_token_lower = response.get_token_by_symbol("br")
        assert br_token_lower is not None
        assert br_token_lower.symbol == "BR"
        
        # 测试不存在的代币
        non_existent = response.get_token_by_symbol("NONEXISTENT")
        assert non_existent is None
    
    def test_get_tokens_by_chain(self):
        """测试根据链ID获取代币列表"""
        response_data = {
            "success": True,
            "code": "000000",
            "data": [
                {
                    "alphaId": "ALPHA_118",
                    "chainId": "56",
                    "chainName": "BSC",
                    "contractAddress": "0xff7d6a96ae471bbcd7713af9cb1feeb16cf56b41",
                    "symbol": "BR",
                    "tokenId": "063898D505CAF5E575D14DC5D5022B2B",
                    "totalSupply": "1000000000"
                },
                {
                    "alphaId": "ALPHA_119",
                    "chainId": "1",
                    "chainName": "ETH",
                    "contractAddress": "0x1234567890abcdef",
                    "symbol": "BTC",
                    "tokenId": "BTC_TOKEN_ID",
                    "totalSupply": "21000000"
                }
            ]
        }
        
        response = AlphaTokenListResponse(**response_data)
        
        # 测试BSC链的代币
        bsc_tokens = response.get_tokens_by_chain("56")
        assert len(bsc_tokens) == 1
        assert bsc_tokens[0].symbol == "BR"
        
        # 测试ETH链的代币
        eth_tokens = response.get_tokens_by_chain("1")
        assert len(eth_tokens) == 1
        assert eth_tokens[0].symbol == "BTC"
        
        # 测试不存在的链
        non_existent_chain = response.get_tokens_by_chain("999")
        assert len(non_existent_chain) == 0
    
    def test_iterator_support(self):
        """测试迭代器支持"""
        response_data = {
            "success": True,
            "code": "000000",
            "data": [
                {
                    "alphaId": "ALPHA_118",
                    "chainId": "56",
                    "chainName": "BSC",
                    "contractAddress": "0xff7d6a96ae471bbcd7713af9cb1feeb16cf56b41",
                    "symbol": "BR",
                    "tokenId": "063898D505CAF5E575D14DC5D5022B2B",
                    "totalSupply": "1000000000"
                }
            ]
        }
        
        response = AlphaTokenListResponse(**response_data)
        
        # 测试长度
        assert len(response) == 1
        
        # 测试迭代
        symbols = [token.symbol for token in response]
        assert symbols == ["BR"] 