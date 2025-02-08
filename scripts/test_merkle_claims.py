from brownie import interface
import json
airdrop_types = [4,5,6]
test_accounts = ['0x1dDBcf631B1410D42D49E59Ee234e6Ce509B584c', '0xa082CE06774Dd553A5CB3a75f22c99Ca929AE5C0', '0x2E41375F65b936f645Ed8aEfDf5406C6Cd43C4B3']
vest_manager = interface.IVestManager('0xd6845EE4a827638908D120054eC79276476BA942')

def clear():
    for type in airdrop_types:
        for user in test_accounts:
            vest_manager.setHasClaimed(user, type, False)

def claim_all():
    for type in airdrop_types:
        for user in test_accounts:
            vest_manager.setHasClaimed(user, type, False)

def get_claim_data(user):
    data = json.load(open(f'./data/lock_break_airdrop_dev.json'))['claims']
    proof = data[user]['proof']
    amount = data[user]['amount']
    index = data[user]['index']
    return proof, amount, index

def claim():
    user = test_accounts[0] # Can replace with any user
    claim_type = 4          # Can replace with any valid claim type
    proof, amount, index = get_claim_data(user, claim_type)
    vest_manager.merkleClaim(
        user,
        user,
        amount,
        claim_type,
        proof,
        index,
        {'from': user}
    )