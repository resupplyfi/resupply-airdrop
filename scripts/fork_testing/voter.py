from brownie import interface, accounts, web3, ZERO_ADDRESS
import json

def main():
    voter = interface.IVoter('0x04Ad8CA9b3e0c3636FD41552BCeeA8b69d4b0c0d')
    staker = interface.IStaker('0x5071F9fEeAF2cb95C2fd1E7049c09A134c4e8064')