import json
from brownie import web3
from itertools import zip_longest
from eth_abi.packed import encode_packed
from eth_utils import encode_hex

class MerkleTree:
    def __init__(self, elements):
        self.elements = sorted(set(web3.keccak(hexstr=el) for el in elements))
        self.layers = MerkleTree.get_layers(self.elements)

    @property
    def root(self):
        return self.layers[-1][0]

    def get_proof(self, el):
        el = web3.keccak(hexstr=el)
        idx = self.elements.index(el)
        proof = []
        for layer in self.layers:
            pair_idx = idx + 1 if idx % 2 == 0 else idx - 1
            if pair_idx < len(layer):
                proof.append(encode_hex(layer[pair_idx]))
            idx //= 2
        return proof

    @staticmethod
    def get_layers(elements):
        layers = [elements]
        while len(layers[-1]) > 1:
            layers.append(MerkleTree.get_next_layer(layers[-1]))
        return layers

    @staticmethod
    def get_next_layer(elements):
        return [
            MerkleTree.combined_hash(a, b) for a, b in zip_longest(elements[::2], elements[1::2])
        ]

    @staticmethod
    def combined_hash(a, b):
        if a is None:
            return b
        if b is None:
            return a
        return web3.keccak(b"".join(sorted([a, b])))
    
def main():
    from brownie import Contract
    LOCKER = Contract('0x3f78544364c3eCcDCe4d9C89a630AEa26122829d')
    end_block = 21_100_000
    start_block = end_block - 1_000_000  # TODO: replace with new once gov vote passes
    print(f'Fetching all locks withdrawn between blocks {start_block:,} --> {end_block:,}')
    logs = LOCKER.events.LocksWithdrawn().get_logs(fromBlock=start_block, toBlock=end_block)
    print(f'{len(logs)} locks withdrawn')
    data = {}
    for log in logs:
        user = log.args['account']
        penalty = log.args['penalty']
        if penalty > 0:
            data[user] = data.get(user, 0) + penalty
    
    print(f'{len(data)} unique users with penalties > 0')
    data = {
        web3.to_checksum_address(k): int(v) for k, v in data.items()
    }
    # Write to JSON file
    with open('./data/sample_user_data.json', 'w') as f:
        json.dump(data, f, indent=4)


def create_merkle():
    total_distribution = 10_000_000 * 10 ** 18
    user_amount_data = json.load(open('./data/sample_user_data.json'))
    total_amounts = sum(user_amount_data.values())
    ratio = total_distribution / total_amounts

    user_amount_data = {
        k.lower(): int(v * ratio) for k, v in user_amount_data.items()
    }
    addresses = sorted(user_amount_data, key=lambda k: user_amount_data[k], reverse=True)
    while sum(user_amount_data.values()) < total_distribution:
        diff = total_distribution - sum(user_amount_data.values())
        user_amount_data[addresses[len(addresses) - 1]] += diff
    assert sum(user_amount_data.values()) == total_distribution
    
    elements = [
        (account, index, user_amount_data[account]) for index, account in enumerate(addresses)
    ]
    print(elements)
    nodes = [encode_hex(encode_packed(["address", "uint", "uint"], el)) for el in elements]
    tree = MerkleTree(nodes)

    distribution = {
        "merkleRootBase": encode_hex(tree.root),
        "tokenTotal": hex(sum(user_amount_data.values())),
        "claims": {
            web3.to_checksum_address(user): {
                "index": index,
                # "amount_hex": hex(amount),
                "amount": amount,
                "proof": [
                    tree.get_proof(nodes[index]),
                ],
            }
            for user, index, amount in elements
        },
    }

    # Write the distribution data to a JSON file
    with open('./data/lock_break_airdrop.json', 'w') as json_file:
        json.dump(distribution, json_file, indent=4)
    print(f'Distribution successfully written for {len(distribution["claims"])} users')
    print(f"base merkle root: {encode_hex(tree.root)}")
    return distribution