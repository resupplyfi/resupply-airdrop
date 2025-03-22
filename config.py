from dataclasses import dataclass
from typing import Dict, List
from enum import IntEnum

@dataclass
class CirculatingSupplyData:
    total_supply: float
    vault_balance: float
    burned: float
    fee_receiver_balance: float
    claimable_fees: float
    unclaimed_vests: float
    receiver_allocations: float
    eligible_lock_breaks: float

class AllocationRatios:
    # Basis points for each allocation (sum should be 6000 = 60%)
    CONVEX = 2000      # 0.20 * 10000
    YEARN = 1000       # 0.10 * 10000
    REDEMPTIONS = 1500 # 0.15 * 10000
    TREASURY = 1050    # 0.105 * 10000
    TEAM = 200         # 0.02 * 10000
    VICTIMS = 200      # 0.02 * 10000
    LICENSING = 50     # 0.005 * 10000

    @classmethod
    def get_all(cls) -> Dict[str, int]:
        """Returns all allocation ratios as a dictionary"""
        return {
            name: value 
            for name, value in vars(cls).items() 
            if not name.startswith('_') and isinstance(value, int)
        }

    @classmethod
    def validate(cls) -> bool:
        """Validates that allocation ratios sum to expected total"""
        total = sum(cls.get_all().values())
        expected = 6000  # 60% of basis points
        assert total == expected, f"Allocation ratios sum to {total}, expected {expected}"
        return True

class ContractAddresses:
    """Centralized contract addresses"""
    PRISMA = '0xdA47862a83dac0c112BA89c6abC2159b95afd71C'
    YPRISMA = '0xe3668873D944E4A949DA05fc8bDE419eFF543882'
    CVXPRISMA = '0x34635280737b5BFe6c7DC2FC3065D60d66e78185'
    LOCKER = '0x3f78544364c3eCcDCe4d9C89a630AEa26122829d'
    VAULT = '0x06bDF212C290473dCACea9793890C5024c7Eb02c'
    FEE_RECEIVER = '0xfdCE0267803C6a0D209D3721d2f01Fd618e9CBF8'
    TREASURY = '0xD0eFDF01DD8d650bBA8992E2c42D0bC6d441a673'
    VESTING = '0xC72bc1a8cf9b1A218386df641d8bE99B40436A0f'
    LOCKER = '0x3f78544364c3eCcDCe4d9C89a630AEa26122829d'
    VEST_MANAGER = '0x6666666677B06CB55EbF802BB12f8876360f919c'

class Config:
    # Directory structure
    DATA_DIR = 'data'
    MERKLE_DIR = f'{DATA_DIR}/merkle'
    SOURCES_DIR = f'{DATA_DIR}/sources'
    CACHE_DIR = f'{DATA_DIR}/cache'
    
    # Cache data files
    USERS_LOCKS_FILE = f'{CACHE_DIR}/user_lock_data.json'
    SUPPLY_DATA_FILE = f'{CACHE_DIR}/supply_data.json'
    
    # Source data files
    TEAM_SPLITS_FILE = f'{SOURCES_DIR}/team_splits.json'
    VICTIM_DATA_FILE = f'{SOURCES_DIR}/victim_data.json'
    PENALTY_DATA_FILE = f'{SOURCES_DIR}/penalty_data.json'

    # Constants
    INITIAL_SUPPLY = 60_000_000 * 10 ** 18
    TOTAL_SUPPLY = 100_000_000 * 10 ** 18
    BASIS_POINTS = 10_000
    DUST_THRESHOLD = 1e3
    LOCK_BREAK_START_BLOCK = 21_425_699  # Last block before December 18 00:00:00 UTC
    LOCK_BREAK_ELIGIBILITY_END_TIME = 1743033600  # 2025-03-27 00:00:00 UTC

    # Use AllocationRatios class
    ALLOCATION_RATIOS = AllocationRatios

    # Block Numbers
    DEPLOY_BLOCK = 18029884
    LOCK_BREAK_START_BLOCK = 21_425_699

    # Supply Metrics
    SUPPLY_METRICS = {
        'Circulating PRISMA': 'amount of PRISMA + derivatives in circulation',
        'Non circulating PRISMA': 'amount of PRISMA not currently in circulation',
        'Liquid Locker Supply': 'Sum total of Liquid Locker supply',
        'Locked Supply': 'total locked PRISMA',
        'Boost Delegation Fees': 'Boost Delegation Fees'
    }

    # Burn addresses
    BURN_ADDRESSES = [
        '0x000000000000000000000000000000000000dEaD',
        '0x0000000000000000000000000000000000000000',  # ZERO_ADDRESS
        ContractAddresses.PRISMA,
        ContractAddresses.CVXPRISMA,
        ContractAddresses.YPRISMA,
    ]

    @classmethod
    def get_merkle_file(cls, alloc_type: str) -> str:
        """Returns the path to a merkle data file for a given allocation type"""
        return f'{cls.MERKLE_DIR}/merkle_data_{alloc_type}.json'

class AirdropType(IntEnum):
    TEAM = 4
    VICTIMS = 5
    PENALTY = 6

    @classmethod
    def get_merkle_file(cls, airdrop_type: 'AirdropType') -> str:
        """Get merkle file path for a given airdrop type"""
        type_names = {
            cls.TEAM: 'team',
            cls.VICTIMS: 'victims',
            cls.PENALTY: 'penalty'
        }
        return f'{Config.MERKLE_DIR}/merkle_data_{type_names[airdrop_type]}.json'