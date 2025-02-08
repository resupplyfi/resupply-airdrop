from brownie import Contract, ZERO_ADDRESS, chain
import pandas as pd
import json
import os

PRISMA = Contract('0xdA47862a83dac0c112BA89c6abC2159b95afd71C')
YPRISMA = Contract('0xe3668873D944E4A949DA05fc8bDE419eFF543882')
CVXPRISMA = Contract('0x34635280737b5BFe6c7DC2FC3065D60d66e78185')
LOCKER = Contract('0x3f78544364c3eCcDCe4d9C89a630AEa26122829d')
VAULT = Contract('0x06bDF212C290473dCACea9793890C5024c7Eb02c')
FEE_RECEIVER = Contract('0xfdCE0267803C6a0D209D3721d2f01Fd618e9CBF8')
TREASURY = '0xD0eFDF01DD8d650bBA8992E2c42D0bC6d441a673'
# Init Param txn: https://etherscan.io/tx/0x51945be1c2cc08f7809d4f15f9484384c736cdaa4aa783a7e51d27e592aafd1c#eventlog

DEPLOY_BLOCK = 18029884

def fees():
    cache_file = 'reports/fees_cache.json'
    
    # Load cache if it exists
    if os.path.exists(cache_file):
        with open(cache_file, 'r') as f:
            cache = json.load(f)
        last_block = cache['last_block']
        users = set(cache['users'])  # Convert cached list back to set
        start_block = last_block + 1
    else:
        start_block = DEPLOY_BLOCK
        users = set()
    
    current_block = 21_000_000
    
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
    with open(cache_file, 'w') as f:
        json.dump(cache, f)
    
    return total


def sum_vault_approvals():
    return sum([PRISMA.allowance(VAULT, addr) for addr in ['0xC72bc1a8cf9b1A218386df641d8bE99B40436A0f', TREASURY]]) / 1e18

def sum_receiver_allocations():
    amount = 0
    for i in range(1000):
        receiver = VAULT.idToReceiver(i)
        addr = receiver['account']
        if addr == ZERO_ADDRESS:
            break
        amount += VAULT.allocated(addr)/1e18
    return amount

def vault_approvals():
    # Initialize with vesting and treasury
    accounts = ['Vesting', 'Team Treasury', 'Receivers']
    amounts = [
        PRISMA.allowance(VAULT, '0xC72bc1a8cf9b1A218386df641d8bE99B40436A0f')/1e18,
        PRISMA.allowance(VAULT, TREASURY)/1e18,
        0  # Will accumulate receiver amounts
    ]
    
    # Sum up all receiver allocations
    for i in range(1000):
        receiver = VAULT.idToReceiver(i)
        addr = receiver['account']
        if addr == ZERO_ADDRESS:
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



def main():
    data = {
        'Metric': [
            'Circulating PRISMA', 
            'Non circulating PRISMA', 
            'Liquid Locker Supply', 
            'Locked Supply',
            'Boost Delegation Fees'
        ],
        'Value': [
            get_circulating_prisma(),
            get_non_circulating_prisma(),
            get_ll_supply(),
            get_locked_prisma(),
            fees()
        ],
        'Note': [
            'amount of PRISMA + derivatives in circulation', 
            'amount of PRISMA not currently in circulation', 
            'Sum total of Liquid Locker supply', 
            'total locked PRISMA',
            'Boost Delegation Fees'
        ]  # Empty notes column for user input
    }
    
    df = pd.DataFrame(data)
    # Format the 'Value' column
    df['Value'] = df['Value'].apply(lambda x: f"{x:,.2f}")
    df.to_csv('prisma_data.csv', index=False)
    print(df)


def get_circulating_prisma():
    total_supply = PRISMA.totalSupply() / 1e18
    vault_balance = PRISMA.balanceOf(VAULT) / 1e18
    fee_receiver_balance = PRISMA.balanceOf(FEE_RECEIVER) / 1e18
    claimable_fees = fees()
    unclaimed_vests = sum_vault_approvals()
    receiver_allocations = sum_receiver_allocations()
    total_burned = sum([PRISMA.balanceOf(x) for x in [
        '0x000000000000000000000000000000000000dEaD',
        ZERO_ADDRESS,
        PRISMA.address,
        CVXPRISMA.address,
        YPRISMA.address,
    ]]) / 1e18
    eligible_lock_breaks = get_eligible_lock_breaks() / 1e18
    
    print(f"Total Supply: {total_supply:,.2f}")
    print(f"Vault Balance: {vault_balance:,.2f}")
    print(f"Burned: {total_burned:,.2f}")
    print(f"Fee Receiver Balance: {fee_receiver_balance:,.2f}")
    print(f"Claimable Fees: {claimable_fees:,.2f}")
    print(f"Unclaimed Vests: {unclaimed_vests:,.2f}")
    print(f"Receiver Allocations: {receiver_allocations:,.2f}")
    print(f"Eligible Lock Breaks: {eligible_lock_breaks:,.2f}")
    
    circulating = (
        total_supply -          # 300M
        vault_balance -         # prisma.balanceOf(vault)
        total_burned -          # sum in burn addresses
        fee_receiver_balance +  # prisma.balanceOf(fee_receiver)
        eligible_lock_breaks +  # eligible lock breaks
        claimable_fees +        # claimable boost fees
        unclaimed_vests +       # unclaimed vests
        receiver_allocations    # receiver allocations: to be sealed in phase 3
    )
    
    return circulating

def get_eligible_lock_breaks():
    LOCKER = Contract('0x3f78544364c3eCcDCe4d9C89a630AEa26122829d')
    end_block = chain.height
    start_block = 21_425_699  # Last block before December 18 00:00:00 UTC
    print(f'Fetching all locks withdrawn between blocks {start_block:,} --> {end_block:,}')
    logs = LOCKER.events.LocksWithdrawn().get_logs(fromBlock=start_block, toBlock=end_block)
    return sum([log.args['penalty'] for log in logs])

def get_non_circulating_prisma():
    return (
        PRISMA.totalSupply() / 1e18 -
        get_circulating_prisma()
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
