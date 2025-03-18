from brownie import Contract, chain, web3
from config import Config, ContractAddresses
from utils.utils import func_timer
import json
import os
import time

LOCKER = Contract(ContractAddresses.LOCKER)

@func_timer
def fetch_lock_break_data():
    """
    Fetches all lock break penalties between a specified block width and saves them to cache.
    Only includes penalties > 0 and aggregates multiple penalties for the same user.
    """
    end_block = chain.height
    timestamp = chain[end_block].timestamp
    
    # Fetch logs
    print(f'Fetching locks withdrawn between blocks {Config.LOCK_BREAK_START_BLOCK:,} --> {end_block:,}')
    from_time = chain[Config.LOCK_BREAK_START_BLOCK].timestamp
    to_time = chain[end_block].timestamp
    print(f'From {time.strftime("%m/%d %H:%M", time.gmtime(from_time))} to {time.strftime("%m/%d %H:%M", time.gmtime(to_time))}')
    logs = LOCKER.events.LocksWithdrawn().get_logs(
        fromBlock=Config.LOCK_BREAK_START_BLOCK, 
        toBlock=end_block
    )
    print(f'Found {len(logs)} withdrawn locks')

    # Aggregate penalties by user
    penalty_data = {}
    for log in logs:
        user = web3.to_checksum_address(log.args['account'])  # Normalize address format
        penalty = log.args['penalty']
        txn_hashes = [log.transactionHash.hex()]
        if penalty > 0:
            if user in penalty_data:
                penalty += int(penalty_data[user]['total_penalty'])
                txn_hashes.append(log.transactionHash.hex())
            penalty_data[user] = {
                'total_penalty': str(penalty),
                'timestamp': chain[log.blockNumber].timestamp,
                'txn_hashes': txn_hashes
            }
    
    # Ensure cache directory exists
    os.makedirs(os.path.dirname(Config.PENALTY_DATA_FILE), exist_ok=True)
    
    # Write to cache file
    with open(Config.PENALTY_DATA_FILE, 'w') as f:
        json.dump({
            'last_run': timestamp,
            'data': penalty_data
        }, f, indent=2, sort_keys=True)
    
    return penalty_data

def main():
    """Entry point for Brownie script"""
    return fetch_lock_break_data()

if __name__ == '__main__':
    main()