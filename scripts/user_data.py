from brownie import Contract, chain

PRISMA = Contract('0xdA47862a83dac0c112BA89c6abC2159b95afd71C')
YPRISMA = Contract('0xe3668873D944E4A949DA05fc8bDE419eFF543882')
CVXPRISMA = Contract('0x34635280737b5BFe6c7DC2FC3065D60d66e78185')
LOCKER = Contract('0x3f78544364c3eCcDCe4d9C89a630AEa26122829d')
VAULT = Contract('0x06bDF212C290473dCACea9793890C5024c7Eb02c')
FEE_RECEIVER = Contract('0xfdCE0267803C6a0D209D3721d2f01Fd618e9CBF8')

def main():
    start_block = chain.height - 1_000_000 # TODO: replace with new once gov vote passes
    end_block = chain.height # TODO: replace with new once gov vote passes
    print(f'Fetching all locks withdrawn between blocks {start_block:,} --> {end_block:,}')
    logs = LOCKER.events.LocksWithdrawn().get_logs(fromBlock=start_block, toBlock=end_block)
    print(f'{len(logs)} locks withdrawn')
    data = {}
    for log in logs:
        user = log.args['account']
        penalty = log.args['penalty']
        if penalty > 0:
            data[user] = data.get(user, 0) + (penalty / 1e18)
    
    print(f'{len(data)} unique users with penalties > 0')
    for user, penalty in data.items():
        print(f'{user} | {penalty:,.2f} PRISMA')
