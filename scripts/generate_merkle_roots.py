import json
from brownie import Contract, chain, web3
from utils.merkle import create_merkle
from config import Config, AllocationRatios, ContractAddresses
import time

ALLOCATIONS = {}

def main():
    compute_allocations()
    total_tokens = 0
    total_tokens += create_team_merkle()
    total_tokens += create_victims_merkle()
    total_tokens += create_penalty_merkle()
    print(f'\nTotal tokens allocated: {total_tokens}')


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
    Input data should be a JSON file containing team wallet addresses mapped to their assigned percentages.
    The percentages should sum to 10000 (100%).
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
    create_merkle(tokens_per_wallet, total, 'team')
    return sum(tokens_per_wallet.values())


def create_victims_merkle():
    """
    Input data should be a JSON file containing victim wallet addresses mapped to their losses.
    This function will assign amounts based on each victim's loss as a percentage of total losses.
    """
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
    create_merkle(tokens_per_wallet, total, 'victims')
    return sum(tokens_per_wallet.values())


def create_penalty_merkle():
    """
    Input data should be a JSON file containing wallet addresses mapped to their total penalties.
    Penalties are reimbursed at RSUP:PRISMA redemption rate.
    """
    redemption_rate = Contract(ContractAddresses.VEST_MANAGER).redemptionRatio()
    print(f'Redemption rate: {redemption_rate / 10**18:.18f}')
    
    user_amount_data = json.load(open(Config.PENALTY_DATA_FILE))
    last_run = user_amount_data['last_run']
    assert last_run > Config.LOCK_BREAK_ELIGIBILITY_END_TIME, f"Last run not after window closed"
    print(f'\n Penalty data last calculated: {time.strftime("%B %d %H:%M", time.gmtime(last_run))} ...')
    
    tokens_per_wallet = {
        wallet: (int(info['total_penalty']) * redemption_rate) // 10**18
        for wallet, info in user_amount_data['data'].items()
        if int(info['total_penalty']) > 0  # Ignore wallets that have no penalties
    }
    
    total = sum(tokens_per_wallet.values())
    assert redemption_rate > 0
    assert redemption_rate < 10**17 # 0.1 rate
    assert total < ALLOCATIONS['REDEMPTIONS'] * .10 # Sanity check
    print_allocation_results('PENALTIES', tokens_per_wallet, total)
    create_merkle(tokens_per_wallet, total, 'penalty')
    return sum(tokens_per_wallet.values())


def print_allocation_results(alloc_type, data, alloc_total):
    print(f'\n --- {alloc_type} allocations ---')
    for wallet, amount in sorted(data.items(), key=lambda x: x[1], reverse=True):
        print(f'{wallet}: {amount}')
    print(f'Total: {alloc_total}\n')


def get_circulating_supply() -> int:
    """Returns the current circulating supply from the supply data cache as an integer (in wei)"""
    try:
        with open(Config.SUPPLY_DATA_FILE, 'r') as f:
            supply_data = json.load(f)
        # Convert from float to integer (wei)
        return int(supply_data['metrics']['circulating_supply']['value'] * 10 ** 18)
    except (FileNotFoundError, KeyError, json.JSONDecodeError) as e:
        print(f"Error reading circulating supply: {e}")
        raise e