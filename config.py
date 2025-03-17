from dataclasses import dataclass
from typing import Dict

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

class Config:
    CACHE_DIR = 'reports'
    FEES_CACHE_FILE = f'{CACHE_DIR}/fees_cache.json'
    CSV_OUTPUT = '{CACHE_DIR}/liquidity_data.csv'
    
    # Directory structure
    DATA_DIR = 'data'
    MERKLE_DIR = f'{DATA_DIR}/merkle'
    SOURCES_DIR = f'{DATA_DIR}/sources'
    CACHE_DIR = f'{DATA_DIR}/cache'
    
    # Source data files
    TEAM_SPLITS_FILE = f'{SOURCES_DIR}/team_splits.json'
    VICTIM_DATA_FILE = f'{SOURCES_DIR}/victim_data.json'
    PENALTY_DATA_FILE = f'{SOURCES_DIR}/penalty_data.json'
    
    # Output files
    MERKLE_FILE = 'merkle_data.json'
    MERKLE_FILE_ALLOC_TYPE = 'merkle_data_{alloc_type}.json'
    MERKLE_FILE_ALLOC_TYPE_PATTERN = MERKLE_FILE_ALLOC_TYPE.format(alloc_type='')

    # Constants
    INITIAL_SUPPLY = 60_000_000 * 10 ** 18
    TOTAL_SUPPLY = 100_000_000 * 10 ** 18
    BASIS_POINTS = 10_000
    DUST_THRESHOLD = 1e3
    LOCK_BREAK_START_BLOCK = 21_425_699  # Last block before December 18 00:00:00 UTC

    # Use AllocationRatios class
    ALLOCATION_RATIOS = AllocationRatios