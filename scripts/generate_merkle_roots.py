import json
from brownie import Contract, chain, web3
from utils.merkle import create_merkle

INITIAL_SUPPLY = 60_000_000 * 10 ** 18
TOTAL_SUPPLY = 100_000_000 * 10 ** 18
BASIS_POINTS = 10_000
ALLOCATION_RATIOS = {
    'CONVEX': 2000,      # 0.20 * 10000
    'YEARN': 1000,       # 0.10 * 10000
    'REDEMPTIONS': 1500, # 0.15 * 10000
    'TREASURY': 1050,    # 0.105 * 10000
    'TEAM': 200,         # 0.02 * 10000
    'VICTIMS': 200,      # 0.02 * 10000
    'LICENSING': 50,     # 0.005 * 10000
}
ALLOCATIONS = {}

# Compute allocations
# Allocation sub calcs 

def compute_allocations():
    global ALLOCATIONS
    total_pct = 0
    
    for k, v in ALLOCATION_RATIOS.items():
        total_pct += v
        # Use integer division for precise calculation
        ALLOCATIONS[k] = (TOTAL_SUPPLY * v) // BASIS_POINTS
    
    total_allocated = sum(ALLOCATIONS.values())
    assert total_allocated == INITIAL_SUPPLY, f"Allocation mismatch: {total_allocated} != {INITIAL_SUPPLY}"

def main():
    LOCKER = Contract('0x3f78544364c3eCcDCe4d9C89a630AEa26122829d')
    end_block = chain.height
    start_block = 21_425_699  # Last block before December 18 00:00:00 UTC
    print(f'Fetching all locks withdrawn between blocks {start_block:,} --> {end_block:,}')
    logs = LOCKER.events.LocksWithdrawn().get_logs(fromBlock=start_block, toBlock=end_block)
    print(f'{len(logs)} locks withdrawn')
    data = {}
    for log in logs:
        user = log.args['account']
        penalty = log.args['penalty'] / 1e18
        if penalty > 0:
            data[user] = data.get(user, 0) + penalty
    
    print(f'{len(data)} unique users with penalties')
    data = {
        web3.to_checksum_address(k): int(v) for k, v in data.items()
    }
    # Write to JSON file
    with open('./data/sample_user_data.json', 'w') as f:
        json.dump(data, f, indent=4)


def create_team_merkle():
    """
    Input data should be a JSON file containing wallet addresses mapped to their allocation
    percentages expressed in basis points (1/10000). The percentages should sum to 10000 (100%).
    """
    compute_allocations()
    split_data = json.load(open('./data/sources/team_splits.json'))
    assert sum(split_data.values()) == BASIS_POINTS, f"Team split total mismatch: {total} != {BASIS_POINTS}"
    # Convert percentages to actual token amounts
    data = {
        wallet: (pct * ALLOCATIONS['TEAM']) // BASIS_POINTS
        for wallet, pct in split_data.items()
    }
    # Verify the total matches the team allocation
    total = sum(data.values())
    assert total == ALLOCATIONS['TEAM'], f"Team allocation mismatch: {total} != {ALLOCATIONS['TEAM']}"
    return create_merkle(data, total, False)

def create_victims_merkle():
    user_amount_data = json.load(open('./data/merkle/victim_splits.json'))
    amount = 0
    addresses = []
    return 0

def create_penalty_merkle():
    user_amount_data = json.load(open('data/merkle/penalty_splits.json'))
    return create_merkle(user_amount_data, ALLOCATIONS['LOCK_BREAK'], False)

