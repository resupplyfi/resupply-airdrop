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
DUST_THRESHOLD = 1e6
# Compute allocations
# Allocation sub calcs 

def main():
    compute_allocations()
    create_team_merkle()
    create_victims_merkle()

    # TODO: Uncomment when ready to generate penalty merkle
    # fetch_lock_break_data()
    # create_penalty_merkle()


def compute_allocations():
    global ALLOCATIONS
    total_pct = 0
    
    for k, v in ALLOCATION_RATIOS.items():
        total_pct += v
        # Use integer division for precise calculation
        ALLOCATIONS[k] = (TOTAL_SUPPLY * v) // BASIS_POINTS
    
    total_allocated = sum(ALLOCATIONS.values())
    assert total_allocated == INITIAL_SUPPLY, f"Allocation mismatch: {total_allocated} != {INITIAL_SUPPLY}"


def create_team_merkle():
    """
    Input data should be a JSON file containing wallet addresses mapped to their allocation
    percentages expressed in basis points (1/10000). The percentages should sum to 10000 (100%).
    """
    split_data = json.load(open('./data/sources/team_splits.json'))
    assert sum(split_data.values()) == BASIS_POINTS, f"Team split total mismatch: {total} != {BASIS_POINTS}"
    # Convert percentages to actual token amounts
    tokens_per_wallet = {
        wallet: (pct * ALLOCATIONS['TEAM']) // BASIS_POINTS
        for wallet, pct in split_data.items()
    }
    # Verify the total matches the team allocation
    total = sum(tokens_per_wallet.values())
    assert total == ALLOCATIONS['TEAM'], f"Team allocation mismatch: {total} != {ALLOCATIONS['TEAM']}"
    print_allocation_results('TEAM', tokens_per_wallet, total)
    return create_merkle(tokens_per_wallet, total, False)


def create_victims_merkle():
    victim_data = json.load(open('./data/sources/victim_data.json'))
    total_losses = sum(int(v['final_loss']) for v in victim_data.values())
    tokens_per_wallet = {
        k: int(v['final_loss']) * ALLOCATIONS['VICTIMS'] // total_losses
        for k, v in victim_data.items()
        if int(v['final_loss']) > 0 # Ignore wallets that have been fully repaid
    }
    # Verify the total matches the team allocation
    total = sum(tokens_per_wallet.values())
    if total < ALLOCATIONS['VICTIMS']:
        diff = ALLOCATIONS['VICTIMS'] - total
        assert diff < DUST_THRESHOLD, f"Difference is greater than dust threshold: {diff}"
        # Sort wallets by value and add diff to the last one
        sorted_wallets = sorted(tokens_per_wallet.keys(), key=lambda x: tokens_per_wallet[x], reverse=True) # Sort wallets by value high to low
        tokens_per_wallet[sorted_wallets[-1]] += diff
    total = sum(tokens_per_wallet.values())
    assert total == ALLOCATIONS['VICTIMS'], f"Victim allocation mismatch: {total} != {ALLOCATIONS['VICTIMS']}"
    print_allocation_results('VICTIMS', tokens_per_wallet, total)
    return create_merkle(tokens_per_wallet, total, False)


def create_penalty_merkle():
    user_amount_data = json.load(open('data/merkle/penalty_splits.json'))
    return create_merkle(user_amount_data, ALLOCATIONS['LOCK_BREAK'], False)


def fetch_lock_break_data():
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
    with open('./data/cache/lock_break_data.json', 'w') as f:
        json.dump(data, f, indent=4)


def print_allocation_results(alloc_type, data, alloc_total):
    print(f'\n --- {alloc_type} allocations ---')
    for k, v in sorted(data.items(), key=lambda x: x[1], reverse=True):
        print(f'{k}: {v}')
    print(f'Total: {alloc_total}\n')