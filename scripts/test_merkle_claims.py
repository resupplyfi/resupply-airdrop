from brownie import interface, accounts, web3
import json

airdrop_types = [4,5,6]
test_accounts = ['0x1dDBcf631B1410D42D49E59Ee234e6Ce509B584c', '0xa082CE06774Dd553A5CB3a75f22c99Ca929AE5C0', '0x2E41375F65b936f645Ed8aEfDf5406C6Cd43C4B3']
dev = accounts.at(web3.ens.address('vitalik.eth'), force=True)
vest_manager = interface.IVestManager('0xd6845EE4a827638908D120054eC79276476BA942', owner=dev)

def clear():
    for type in airdrop_types:
        for user in test_accounts:
            if vest_manager.hasClaimed(user, type):
                vest_manager.setHasClaimed(user, type, False)

def claim():
    """
    Claim a single claim for a user and type, to validate the merkle proofs work as expected
    """
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

def claim_all():
    """
    Claim all available claims for all users and types, to validate the merkle proofs work as expected
    """
    for type in airdrop_types:
        for user in test_accounts:
            proof, amount, index = get_claim_data(user)
            vest_manager.merkleClaim(
                user,
                user,
                amount,
                type,
                proof,
                index, 
                {'from': user}
            )

def get_claim_data(user):
    """
    Retrieve the `proof`, `amount`, and `index` for a particular user claim from local json file
    """
    data = json.load(open(f'./data/merkle_data_dev.json'))['claims']
    proof = data[user]['proof']
    amount = data[user]['amount']
    index = data[user]['index']
    return proof, amount, index