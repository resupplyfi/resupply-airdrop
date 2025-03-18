import json
import os
from brownie import Contract, chain, ZERO_ADDRESS
import pandas as pd
from utils.utils import func_timer
from config import Config, CirculatingSupplyData, ContractAddresses

# Initialize contracts
PRISMA = Contract(ContractAddresses.PRISMA)
YPRISMA = Contract(ContractAddresses.YPRISMA)
CVXPRISMA = Contract(ContractAddresses.CVXPRISMA)
LOCKER = Contract(ContractAddresses.LOCKER)
VAULT = Contract(ContractAddresses.VAULT)
FEE_RECEIVER = Contract(ContractAddresses.FEE_RECEIVER)


@func_timer
def get_fees():
    if os.path.exists(Config.USERS_LOCKS_FILE):
        with open(Config.USERS_LOCKS_FILE, 'r') as f:
            cache = json.load(f)
        users = set(cache['users'])
        start_block = cache['last_block'] + 1
    else:
        os.makedirs(Config.CACHE_DIR, exist_ok=True)
        start_block = Config.DEPLOY_BLOCK
        users = set()
    
    current_block = chain.height
    
    # Only get new logs since last processed block
    logs = LOCKER.events.LockCreated.get_logs(fromBlock=start_block, toBlock=current_block)
    
    # Add new users to existing set
    for log in logs:
        users.add(log.args['account'])
    
    # Calculate total fees for all known users
    total = sum(VAULT.claimableBoostDelegationFees(u) / 1e18 for u in users)
    
    # Save updated cache
    cache = {
        'last_block': current_block,
        'users': list(users)  # Convert set to list for JSON serialization
    }
    with open(Config.USERS_LOCKS_FILE, 'w') as f:
        json.dump(cache, f)
    
    return total


@func_timer
def sum_vault_approvals():
    return sum([
        PRISMA.allowance(VAULT, addr) 
        for addr in [ContractAddresses.VESTING, ContractAddresses.TREASURY]
    ]) / 1e18


@func_timer
def sum_receiver_allocations():
    amount = 0
    for i in range(1000):
        receiver = VAULT.idToReceiver(i)
        addr = receiver['account']
        if addr == ZERO_ADDRESS:
            break
        amount += VAULT.allocated(addr)/1e18
    return amount


@func_timer
def vault_approvals():
    accounts = ['Vesting', 'Team Treasury', 'Receivers']
    amounts = [
        PRISMA.allowance(VAULT, ContractAddresses.VESTING)/1e18,
        PRISMA.allowance(VAULT, ContractAddresses.TREASURY)/1e18,
        0  # Will accumulate receiver amounts
    ]
    
    # Sum up all receiver allocations
    for i in range(1000):
        receiver = VAULT.idToReceiver(i)
        addr = receiver['account']
        if addr == ContractAddresses.ZERO_ADDRESS:
            break
        amounts[2] += VAULT.allocated(addr)/1e18
    
    # Create DataFrame
    df = pd.DataFrame({
        '': accounts,
        'Unclaimed Allocation': amounts
    })
    
    # Format numbers before adding total
    df['Unclaimed Allocation'] = df['Unclaimed Allocation'].apply(lambda x: f"{x:,.2f}")
    
    # Add total row with bold formatting
    total = sum(amounts)
    print(df.to_string(index=False))
    print("\033[1m{:<20} {:>14}\033[0m".format('TOTAL', f"{total:,.2f}"))
    
    vault_bal = PRISMA.balanceOf(VAULT) / 1e18
    max_total_supply = PRISMA.maxTotalSupply() / 1e18
    circulating_supply = max_total_supply - vault_bal + total
    print(f'Circulating Supply: {circulating_supply:,.2f}')
    return total


@func_timer
def main():
    fees = get_fees()
    circulating = get_circulating_prisma(fees)
    
    supply_data = {
        "timestamp": chain.time(),
        "block_number": chain.height,
        "metrics": {
            "circulating_supply": {
                "value": circulating,
                "description": Config.SUPPLY_METRICS['Circulating PRISMA']
            },
            "non_circulating_supply": {
                "value": get_non_circulating_prisma(circulating),
                "description": Config.SUPPLY_METRICS['Non circulating PRISMA']
            },
            "liquid_locker_supply": {
                "value": get_ll_supply(),
                "description": Config.SUPPLY_METRICS['Liquid Locker Supply']
            },
            "locked_supply": {
                "value": get_locked_prisma(),
                "description": Config.SUPPLY_METRICS['Locked Supply']
            },
            "boost_delegation_fees": {
                "value": fees,
                "description": Config.SUPPLY_METRICS['Boost Delegation Fees']
            }
        }
    }

    os.makedirs(os.path.dirname(Config.SUPPLY_DATA_FILE), exist_ok=True)
    with open(Config.SUPPLY_DATA_FILE, 'w') as f:
        json.dump(supply_data, f, indent=2)
    
    print(json.dumps(supply_data, indent=2))
    return supply_data


@func_timer
def get_circulating_prisma(fees):
    supply_data = CirculatingSupplyData(
        total_supply=PRISMA.totalSupply() / 1e18,
        vault_balance=PRISMA.balanceOf(VAULT) / 1e18,
        fee_receiver_balance=PRISMA.balanceOf(FEE_RECEIVER) / 1e18,
        claimable_fees=fees,
        unclaimed_vests=sum_vault_approvals(),
        receiver_allocations=sum_receiver_allocations(),
        burned=sum([PRISMA.balanceOf(x) for x in Config.BURN_ADDRESSES]) / 1e18,
        eligible_lock_breaks=get_eligible_lock_breaks() / 1e18
    )
    
    print(f"Total Supply: {supply_data.total_supply:,.2f}")
    print(f"Vault Balance: {supply_data.vault_balance:,.2f}")
    print(f"Burned: {supply_data.burned:,.2f}")
    print(f"Fee Receiver Balance: {supply_data.fee_receiver_balance:,.2f}")
    print(f"Claimable Fees: {supply_data.claimable_fees:,.2f}")
    print(f"Unclaimed Vests: {supply_data.unclaimed_vests:,.2f}")
    print(f"Receiver Allocations: {supply_data.receiver_allocations:,.2f}")
    print(f"Eligible Lock Breaks: {supply_data.eligible_lock_breaks:,.2f}")
    
    circulating = (
        supply_data.total_supply -
        supply_data.vault_balance -
        supply_data.burned -
        supply_data.fee_receiver_balance +
        supply_data.eligible_lock_breaks +
        supply_data.claimable_fees +
        supply_data.unclaimed_vests +
        supply_data.receiver_allocations
    )
    print(f"Circulating PRISMA: {circulating:,.2f}")
    return circulating

def get_eligible_lock_breaks():
    end_block = chain.height    # To be set 1 week after launch
    print(f'Fetching all locks withdrawn between blocks {Config.LOCK_BREAK_START_BLOCK:,} --> {end_block:,}')
    logs = LOCKER.events.LocksWithdrawn().get_logs(fromBlock=Config.LOCK_BREAK_START_BLOCK, toBlock=end_block)
    return sum([log.args['penalty'] for log in logs])

def get_non_circulating_prisma(circulating):
    return (
        PRISMA.totalSupply() / 1e18 -
        circulating
    )

def get_locked_prisma():
    return (
        PRISMA.balanceOf(LOCKER)
    ) / 1e18

def get_ll_supply():
    return (
        YPRISMA.totalSupply() +
        CVXPRISMA.totalSupply()
    ) / 1e18
