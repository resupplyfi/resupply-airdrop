import json
import os
from brownie import Contract, chain
import pandas as pd
from functools import wraps
from utils.utils import func_timer
from config import Config, CirculatingSupplyData, ContractAddresses

# Initialize contracts
PRISMA = Contract(ContractAddresses.PRISMA)
YPRISMA = Contract(ContractAddresses.YPRISMA)
CVXPRISMA = Contract(ContractAddresses.CVXPRISMA)
LOCKER = Contract(ContractAddresses.LOCKER)
VAULT = Contract(ContractAddresses.VAULT)
FEE_RECEIVER = Contract(ContractAddresses.FEE_RECEIVER)

# Addresses
TREASURY = ContractAddresses.TREASURY
BURN_ADDRESSES = Config.BURN_ADDRESSES

# Block Numbers
DEPLOY_BLOCK = Config.DEPLOY_BLOCK
LOCK_BREAK_START_BLOCK = Config.LOCK_BREAK_START_BLOCK


@func_timer
def fees():
    if os.path.exists(Config.FEES_CACHE_FILE):
        with open(Config.FEES_CACHE_FILE, 'r') as f:
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
    with open(Config.FEES_CACHE_FILE, 'w') as f:
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
        if addr == ContractAddresses.ZERO_ADDRESS:
            break
        amount += VAULT.allocated(addr)/1e18
    return amount


@func_timer
def vault_approvals():
    # Initialize with vesting and treasury
    accounts = ['Vesting', 'Team Treasury', 'Receivers']
    amounts = [
        PRISMA.allowance(VAULT, ContractAddresses.VESTING)/1e18,
        PRISMA.allowance(VAULT, TREASURY)/1e18,
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
    data = {
        'Metric': list(Config.SUPPLY_METRICS.keys()),
        'Value': [
            get_circulating_prisma(),
            get_non_circulating_prisma(),
            get_ll_supply(),
            get_locked_prisma(),
            fees()
        ],
        'Note': list(Config.SUPPLY_METRICS.values())
    }
    
    df = pd.DataFrame(data)
    df['Value'] = df['Value'].apply(lambda x: f"{x:,.2f}")
    df.to_csv(Config.CSV_OUTPUT, index=False)
    print(df)


@func_timer
def get_circulating_prisma():
    # Use dataclass to store and return data
    supply_data = CirculatingSupplyData(
        total_supply=PRISMA.totalSupply() / 1e18,
        vault_balance=PRISMA.balanceOf(VAULT) / 1e18,
        fee_receiver_balance=PRISMA.balanceOf(FEE_RECEIVER) / 1e18,
        claimable_fees=fees(),
        unclaimed_vests=sum_vault_approvals(),
        receiver_allocations=sum_receiver_allocations(),
        burned=sum([PRISMA.balanceOf(x) for x in BURN_ADDRESSES]) / 1e18,
        eligible_lock_breaks=get_eligible_lock_breaks() / 1e18
    )
    
    # Print formatted data
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

@func_timer
def get_eligible_lock_breaks():
    end_block = chain.height    # To be set 1 week after launch
    print(f'Fetching all locks withdrawn between blocks {LOCK_BREAK_START_BLOCK:,} --> {end_block:,}')
    logs = LOCKER.events.LocksWithdrawn().get_logs(fromBlock=LOCK_BREAK_START_BLOCK, toBlock=end_block)
    return sum([log.args['penalty'] for log in logs])

@func_timer
def get_non_circulating_prisma():
    return (
        PRISMA.totalSupply() / 1e18 -
        get_circulating_prisma()
    )

@func_timer
def get_locked_prisma():
    return (
        PRISMA.balanceOf(LOCKER)
    ) / 1e18

@func_timer
def get_ll_supply():
    return (
        YPRISMA.totalSupply() +
        CVXPRISMA.totalSupply()
    ) / 1e18
