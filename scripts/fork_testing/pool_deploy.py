from brownie import interface, accounts, web3, ZERO_ADDRESS
import json

dev = ZERO_ADDRESS

def main():
    dev = get_deployer()
    pool1 = interface.ICurvePool('0xdBb1d219d84eaCEFb850ee04caCf2f1830934580') # reUSD/scrvUSD
    pool2 = interface.ICurvePool('0x38De22a3175708D45E7c7c64CD78479C8B56f76E') # reUSD/sfrxETH

    reusd = interface.IERC20(pool1.coins(0))
    scrvusd = interface.IERC20(pool1.coins(1))
    sfrxeth = interface.IERC20(pool2.coins(1))

    print(reusd.balanceOf(dev)/1e18)
    print(scrvusd.balanceOf(dev)/1e18)
    print(sfrxeth.balanceOf(dev)/1e18)

    print(f'pool1.totalSupply(): {pool1.totalSupply()/1e18}')
    print(f'pool2.totalSupply(): {pool2.totalSupply()/1e18}')



def get_deployer():
    short_addr = "0xc4ad"
    # Remove 0x, pad to 40 chars (not 42), then add 0x back
    addr_without_prefix = short_addr[2:]  # remove '0x'
    padded_addr = addr_without_prefix.rjust(40, '0')  # pad to 40 chars
    full_addr = '0x' + padded_addr
    return web3.to_checksum_address(full_addr)