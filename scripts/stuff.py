import json
from brownie import web3, chain
from itertools import zip_longest
from eth_abi.packed import encode_packed
from eth_utils import encode_hex
import csv
    
def main():
    from brownie import Contract
    LOCKER = Contract('0x3f78544364c3eCcDCe4d9C89a630AEa26122829d')
    end_block = chain.height
    start_block = end_block - 1_000_000  # TODO: replace with new once gov vote passes
    start_block = 18029866 # Deploy block
    print(f'Fetching all locks withdrawn between blocks {start_block:,} --> {end_block:,}')

    logs = LOCKER.events.LockCreated().get_logs(fromBlock=start_block, toBlock=end_block)
    print(f'{len(logs)} locks withdrawn')
    users = set()
    for log in logs:
        users.add(log.args['account'])
    
    data = {}
    for user in users:
        locked = LOCKER.getAccountBalances(user)['locked']
        # if locked > 0:
        data[user] = {
            'amount': locked
        }

    print(data)
    # Write to CSV file
    with open('./data/cache/user_lock_data.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['user', 'amount'])  # Header row
        for user, user_data in data.items():
            writer.writerow([user, user_data['amount']])