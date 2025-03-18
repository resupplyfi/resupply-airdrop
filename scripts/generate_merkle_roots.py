import json
from brownie import Contract, chain, web3
from utils.merkle import create_merkle
from config import Config, AllocationRatios
import time

ALLOCATIONS = {}

def main():
    compute_allocations()
    create_team_merkle()
    create_victims_merkle()
    create_penalty_merkle()


def compute_allocations():
    global ALLOCATIONS
    # Validate allocation ratios sum to 60%
    AllocationRatios.validate()
    for name, ratio in AllocationRatios.get_all().items():
        ALLOCATIONS[name] = (Config.TOTAL_SUPPLY * ratio) // Config.BASIS_POINTS
    total_allocated = sum(ALLOCATIONS.values())
    assert total_allocated == Config.INITIAL_SUPPLY, f"Allocation mismatch: {total_allocated} != {Config.INITIAL_SUPPLY}"


def create_team_merkle():
    """
    Input data should be a JSON file containing wallet addresses mapped to their allocation
    percentages expressed in basis points (1/10000). The percentages should sum to 10000 (100%).
    """
    split_data = json.load(open(Config.TEAM_SPLITS_FILE))
    assert sum(split_data.values()) == Config.BASIS_POINTS, f"Team split total mismatch: {total} != {Config.BASIS_POINTS}"
    # Convert percentages to actual token amounts
    tokens_per_wallet = {
        wallet: (pct * ALLOCATIONS['TEAM']) // Config.BASIS_POINTS
        for wallet, pct in split_data.items()
    }
    # Verify the total matches the team allocation
    total = sum(tokens_per_wallet.values())
    assert total == ALLOCATIONS['TEAM'], f"Team allocation mismatch: {total} != {ALLOCATIONS['TEAM']}"
    print_allocation_results('TEAM', tokens_per_wallet, total)
    return create_merkle(tokens_per_wallet, total, 'team')


def create_victims_merkle():
    victim_data = json.load(open(Config.VICTIM_DATA_FILE))
    total_losses = sum(int(v['final_loss']) for v in victim_data.values())
    tokens_per_wallet = {
        k: int(v['final_loss']) * ALLOCATIONS['VICTIMS'] // total_losses # Assign amounts based on pct of total losses
        for k, v in victim_data.items()
        if int(v['final_loss']) > 0 # Ignore wallets that have already been made whole
    }
    # Verify the total matches the team allocation
    total = sum(tokens_per_wallet.values())
    if total < ALLOCATIONS['VICTIMS']:
        diff = ALLOCATIONS['VICTIMS'] - total
        assert diff < Config.DUST_THRESHOLD, f"Difference is greater than dust threshold: {diff}"
        # Sort wallets by value and add diff to the smallest one
        sorted_wallets = sorted(tokens_per_wallet.keys(), key=lambda x: tokens_per_wallet[x], reverse=True) # Sort wallets by value high to low
        tokens_per_wallet[sorted_wallets[-1]] += diff
        total = sum(tokens_per_wallet.values()) # Recalculate total
    assert total == ALLOCATIONS['VICTIMS'], f"Victim allocation mismatch: {total} != {ALLOCATIONS['VICTIMS']}"
    print_allocation_results('VICTIMS', tokens_per_wallet, total)
    return create_merkle(tokens_per_wallet, total, 'victims')


def create_penalty_merkle():
    user_amount_data = json.load(open(Config.PENALTY_DATA_FILE))
    last_run = user_amount_data['last_run']
    print(f'\n Penalty data last calculated: {time.strftime("%B %d %H:%M", time.gmtime(last_run))} ...')
    wallet_amount_data = {
        web3.to_checksum_address(k): int(v['total_penalty'])
        for k, v in user_amount_data['data'].items()
        if int(v['total_penalty']) > 0 # Ignore wallets that have no penalties
    }
    total = sum(wallet_amount_data.values())
    print_allocation_results('PENALTIES', wallet_amount_data, total)
    return create_merkle(wallet_amount_data, total, 'penalty')


def print_allocation_results(alloc_type, data, alloc_total):
    print(f'\n --- {alloc_type} allocations ---')
    for k, v in sorted(data.items(), key=lambda x: x[1], reverse=True):
        print(f'{k}: {v}')
    print(f'Total: {alloc_total}\n')