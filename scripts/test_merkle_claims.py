from brownie import interface, accounts, web3
import json
import time
from config import AirdropType, ContractAddresses

airdrop_types = [AirdropType.TEAM, AirdropType.VICTIMS, AirdropType.PENALTY]
vest_manager = interface.IVestManager(ContractAddresses.VEST_MANAGER)


def claim_one_team():
    return claim_one(AirdropType.TEAM)


def claim_one_victims():
    claim_one(AirdropType.VICTIMS)


def claim_one_penalty():
    return claim_one(AirdropType.PENALTY)


def claim_one(airdrop_type: AirdropType) -> None:
    """Generic function to process one claim for any airdrop type"""
    user_data = get_next_user_data(airdrop_type)
    if user_data is None:
        print('All claims have been processed')
        return

    user = user_data['address']
    amount = user_data['amount']
    print(f'Claiming {airdrop_type.name} vest for {user} with amount {amount} ...')

    vest_data_before = vest_manager.getAggregateVestData(user)
    
    tx = vest_manager.merkleClaim(
        user,
        user,
        amount,
        airdrop_type,
        user_data['proof'],
        user_data['index'],
        {'from': user, 'allow_revert': True, 'gas_limit': 5_000_000}
    )
    
    time.sleep(2)
    vest_data_after = vest_manager.getAggregateVestData(user)
    assert vest_data_after['_totalAmount'] == vest_data_before['_totalAmount'] + amount


def get_next_user_data(type: AirdropType):
    merkle_file = AirdropType.get_merkle_file(type)
    with open(merkle_file, 'r') as f:
        data = json.load(f)

    allocations = []
    for address, info in data['claims'].items():
        allocations.append({
            'address': address,
            'amount': int(info['amount']),
            'index': info['index'],
            'proof': info['proof']  # Keep merkle proof in case needed
        })
    
    # Sort by allocation amount in descending order
    sorted_allocations = sorted(allocations, key=lambda x: x['amount'], reverse=True)
    for i in range(len(sorted_allocations)):
        if not vest_manager.hasClaimed(sorted_allocations[i]['address'], type):
            return sorted_allocations[i]
    return None

def commit_penalty_merkle_root():
    merkle_file = AirdropType.get_merkle_file(AirdropType.PENALTY)
    with open(merkle_file, 'r') as f:
        data = json.load(f)
    merkle_root = data['merkle_root']
    owner = vest_manager.owner()
    allocation = web3.to_int(hexstr=data['token_total'])
    print(f'Setting lock penalty merkle root to {merkle_root} for {allocation} ...')
    vest_manager.setLockPenaltyMerkleRoot(data['merkle_root'], allocation, {'from': owner})