"""
空投数据结构
用于承载空投相关接口返回的数据。
"""

from pydantic import BaseModel


class ClaimInfo(BaseModel):
    can_claim: bool
    is_eligible: bool
    is_claimed: bool
    claim_status: str


class AirdropConfig(BaseModel):
    config_id: str
    name: str
    symbol: str
    alpha_id: str
    contract_address: str
    airdrop_amount: float
    status: str
    claim_info: ClaimInfo

    def is_claimable(self) -> bool:
        return (
            self.claim_info.can_claim
            and self.claim_info.is_eligible
            and not self.claim_info.is_claimed
        )
