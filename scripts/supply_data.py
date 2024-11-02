from brownie import Contract
import pandas as pd

PRISMA = Contract('0xdA47862a83dac0c112BA89c6abC2159b95afd71C')
YPRISMA = Contract('0xe3668873D944E4A949DA05fc8bDE419eFF543882')
CVXPRISMA = Contract('0x34635280737b5BFe6c7DC2FC3065D60d66e78185')
LOCKER = Contract('0x3f78544364c3eCcDCe4d9C89a630AEa26122829d')
VAULT = Contract('0x06bDF212C290473dCACea9793890C5024c7Eb02c')
FEE_RECEIVER = Contract('0xfdCE0267803C6a0D209D3721d2f01Fd618e9CBF8')

def main():
    data = {
        'Metric': [
            'Circulating PRISMA', 
            'Non circulating PRISMA', 
            'Liquid Locker Supply', 
            'Locked Supply'
        ],
        'Value': [
            get_circulating_prisma(),
            get_non_circulating_prisma(),
            get_ll_supply(),
            get_locked_prisma()
        ],
        'Note': [
            'amount of PRISMA + derivatives in circulation', 
            'amount of PRISMA not currently in circulation', 
            'Sum total of Liquid Locker supply', 
            'total locked PRISMA'
        ]  # Empty notes column for user input
    }
    
    df = pd.DataFrame(data)
    # Format the 'Value' column
    df['Value'] = df['Value'].apply(lambda x: f"{x:,.2f}")
    df.to_csv('prisma_data.csv', index=False)
    print(df)


def get_circulating_prisma():
    return (
        PRISMA.totalSupply() -
        PRISMA.balanceOf(VAULT) -
        PRISMA.balanceOf(FEE_RECEIVER)
    ) / 1e18

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
