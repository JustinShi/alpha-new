"""
Alpha代币信息数据模型
用于Alpha代币信息API的数据结构定义
"""

from pydantic import BaseModel, Field, ConfigDict


class AlphaTokenInfo(BaseModel):
    """Alpha代币基本信息模型"""

    alpha_id: str = Field(..., alias="alphaId", description="Alpha代币ID")
    chain_id: str = Field(..., alias="chainId", description="链ID")
    chain_name: str = Field(..., alias="chainName", description="链名称")
    contract_address: str = Field(..., alias="contractAddress", description="合约地址")
    symbol: str = Field(..., description="代币符号")
    token_id: str = Field(..., alias="tokenId", description="代币ID")
    total_supply: str = Field(..., alias="totalSupply", description="总供应量")

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={
            # 可以在这里添加自定义的JSON编码器
        }
    )

    def __str__(self) -> str:
        """字符串表示"""
        return f"AlphaToken({self.symbol}, {self.chain_name}, {self.alpha_id})"

    def __repr__(self) -> str:
        """开发者表示"""
        return (
            f"AlphaTokenInfo(alpha_id='{self.alpha_id}', "
            f"symbol='{self.symbol}', chain_name='{self.chain_name}')"
        )


class AlphaTokenListResponse(BaseModel):
    """Alpha代币列表响应模型"""

    success: bool = Field(..., description="请求是否成功")
    code: str = Field(..., description="响应代码")
    data: list[AlphaTokenInfo] = Field(..., description="代币信息列表")
    message: str | None = Field(None, description="响应消息")

    model_config = ConfigDict(populate_by_name=True)

    def get_token_by_symbol(self, symbol: str) -> AlphaTokenInfo | None:
        """根据符号获取代币信息"""
        for token in self.data:
            if token.symbol.upper() == symbol.upper():
                return token
        return None

    def get_tokens_by_chain(self, chain_id: str) -> list[AlphaTokenInfo]:
        """根据链ID获取代币列表"""
        return [token for token in self.data if token.chain_id == chain_id]

    def get_token_symbols(self) -> list[str]:
        """获取所有代币符号列表"""
        return [token.symbol for token in self.data]

    def __len__(self) -> int:
        """返回代币数量"""
        return len(self.data)

    def __iter__(self):
        """支持迭代"""
        return iter(self.data)


class AlphaTokenFilter(BaseModel):
    """Alpha代币过滤器"""

    chain_id: str | None = Field(None, description="按链ID过滤")
    symbol_pattern: str | None = Field(None, description="按符号模式过滤")
    min_supply: float | None = Field(None, description="最小供应量")
    max_supply: float | None = Field(None, description="最大供应量")

    def matches(self, token: AlphaTokenInfo) -> bool:
        """检查代币是否匹配过滤条件"""
        # 链ID过滤
        if self.chain_id and token.chain_id != self.chain_id:
            return False

        # 符号模式过滤
        if (
            self.symbol_pattern
            and self.symbol_pattern.upper() not in token.symbol.upper()
        ):
            return False

        # 供应量过滤
        try:
            supply = float(token.total_supply)
            if self.min_supply and supply < self.min_supply:
                return False
            if self.max_supply and supply > self.max_supply:
                return False
        except (ValueError, TypeError):
            # 如果供应量无法转换为数字，跳过供应量过滤
            pass

        return True
