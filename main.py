from web3 import Web3
from eth_abi import encode
from contract_abi import (
    testnetbridge_abi,
    scrollio_abi,
    uniswap_abi,
    syncswap_abi,
    mes_abi,
    aave_deposit_abi,
    aave_borrow_abi,
)
import random
import time


# --CONFIG--#
# Insert Private keys in keys.txt; One key per line | Приватные ключи в созданный файл keys.txt. По 1 в строку, не должны начинаться с 0x
from_sec = 1  # |Wait from N seconds between transactions |"Спать от N sec" между каждым приватником
to_sec = 300  # |Wait from N seconds between transactions |"Спать до N sec" между каждым приватником
min_arb_to_spend = 0.0001  # |Min. ETH in Arbitrum to spend for GoerliETH |Мин. к-во ETH в сети Arbitrum на покупку GoerliETH
max_arb_to_spend = 0.001  # |Max. ETH in Arbitrum to spend for GoerliETH |Макс. к-во ETH в сети Arbitrum на покупку GoerliETH
min_goerli_to_bridge = 0.5  # |Min. GoerliETH to bridge to ScrollETH |Мин. к-во GoerliETH для бриджа в Scroll
max_goerli_to_bridge = 1  # |Max. GoerliETH to bridge to ScrollETH |Макс. к-во GoerliETH для бриджа в Scroll
min_goerli_to_spend = 0.05  # |Min. ScrollETH to spend in DApp txns |Мин. к-во ScrollETH в DApp транзакциях (Uniswap, AAVE...)
max_goerli_to_spend = 0.15  # |Max. ScrollETH to spend in DApp txns |Макс. к-во GoerliETH в DApp транзакциях
usdt_to_borrow = 100  # |USDT to borrow on AAVE |К-во USDT для borrow в AAVE

SCROLL_RPC = "https://alpha-rpc.scroll.io/l2"
ARBITRUM_RPC = "https://arb1.arbitrum.io/rpc"
GOERLI_RPC = "https://rpc.ankr.com/eth_goerli"
# ----------#

web3 = Web3(Web3.HTTPProvider(ARBITRUM_RPC))

private_keys = []
failed_keys = []

with open("keys.txt", "r") as f:
    for line in f:
        line = line.strip()
        private_keys.append(line)


class Dapp:
    def __init__(self, web3_provider, contract_address, abi):
        self.web3 = Web3(Web3.HTTPProvider(web3_provider))
        self.contract = self.web3.eth.contract(contract_address, abi=abi)

    def execute_transaction(
        self,
        private_key: str,
        function_name: str,
        args: tuple,
        value: int,
        gasPrice: int,
        chainId: int,
    ) -> hash:
        address = self.web3.eth.account.from_key(private_key).address
        transaction = getattr(self.contract.functions, function_name)(
            *args
        ).build_transaction(
            {
                "from": self.web3.to_checksum_address(address),
                "value": self.web3.to_wei(value, "ether"),
                "nonce": self.web3.eth.get_transaction_count(
                    self.web3.to_checksum_address(address)
                ),
                "chainId": chainId,
                "gasPrice": self.web3.to_wei(gasPrice, "gwei"),
            }
        )
        transaction["gas"] = int(self.web3.eth.estimate_gas(transaction))
        signed_txn = self.web3.eth.account.sign_transaction(transaction, private_key)
        transaction_hash = self.web3.eth.send_raw_transaction(
            signed_txn.rawTransaction
        ).hex()
        print(f"{function_name} | Hash: {transaction_hash}")
        random_sleep()

    def execute_eip1559_transaction(
        self,
        private_key: str,
        function_name: str,
        args,
        value: int,
        maxPriorityFeePerGas: int,
        maxFeePerGas: int,
        chainId: int,
    ) -> hash:
        address = self.web3.eth.account.from_key(private_key).address
        transaction = getattr(self.contract.functions, function_name)(
            *args
        ).build_transaction(
            {
                "from": self.web3.to_checksum_address(address),
                "value": self.web3.to_wei(value, "ether"),
                "nonce": self.web3.eth.get_transaction_count(
                    self.web3.to_checksum_address(address)
                ),
                "chainId": chainId,
                "maxPriorityFeePerGas": web3.to_wei(maxPriorityFeePerGas, "gwei"),
                "maxFeePerGas": web3.to_wei(maxFeePerGas, "gwei"),
            }
        )
        transaction["gas"] = int(self.web3.eth.estimate_gas(transaction))
        signed_txn = self.web3.eth.account.sign_transaction(transaction, private_key)
        transaction_hash = self.web3.eth.send_raw_transaction(
            signed_txn.rawTransaction
        ).hex()
        print(f"{function_name} | Hash: {transaction_hash}")
        random_sleep()


def bridge_scrollio(private_key):
    value_eth = "{:.8f}".format(
        random.uniform(min_goerli_to_bridge, max_goerli_to_bridge)
    )
    value_wei = web3.to_wei(value_eth, "ether")
    dapp = Dapp(GOERLI_RPC, "0xe5E30E7c24e4dFcb281A682562E53154C15D3332", scrollio_abi)
    dapp.execute_eip1559_transaction(
        private_key,
        "depositETH",
        [dapp.web3.to_wei(value_eth, "ether"), 40000],
        web3.from_wei(value_wei * 1.03, "ether"),
        2,
        2,
        5,
    )


def buy_goerli(private_key):
    dapp = Dapp(
        ARBITRUM_RPC, "0x0A9f824C05A74F577A536A8A0c673183a872Dff4", testnetbridge_abi
    )
    address = dapp.web3.eth.account.from_key(private_key).address
    value_eth = "{:.8f}".format(random.uniform(min_arb_to_spend, max_arb_to_spend))
    value_wei = dapp.web3.to_wei(value_eth, "ether")
    dapp.execute_eip1559_transaction(
        private_key,
        "swapAndBridge",
        [
            value_wei,
            0,
            154,
            address,
            address,
            "0x0000000000000000000000000000000000000000",
            b"",
        ],
        web3.from_wei(value_wei * 1.6, "ether"),  # |ArbETH leftovers will be refunded
        0,
        0.1,
        42161,
    )


def uniswap(private_key):
    dapp = Dapp(SCROLL_RPC, "0xD9880690bd717189cC3Fbe7B9020F27fae7Ac76F", uniswap_abi)
    address = dapp.web3.eth.account.from_key(private_key).address
    value_eth = "{:.8f}".format(
        random.uniform(min_goerli_to_spend, max_goerli_to_spend)
    )
    amount_in = web3.to_wei(value_eth, "ether")
    amount_out_min = 0
    token_in = "0xa1EA0B2354F5A344110af2b6AD68e75545009a03"
    token_out = "0x67aE69Fd63b4fc8809ADc224A9b82Be976039509"
    recipient = address
    fee = 3000
    sqrt_price_limit_x96 = 0
    gas_price = 0.001
    transaction = dapp.contract.functions.exactInputSingle(
        (
            token_in,
            token_out,
            fee,
            recipient,
            amount_in,
            amount_out_min,
            sqrt_price_limit_x96,
        )
    ).build_transaction(
        {
            "from": web3.to_checksum_address(address),
            "value": web3.to_wei(value_eth, "ether"),
            "nonce": web3.eth.get_transaction_count(web3.to_checksum_address(address)),
            "chainId": 534353,
            "gasPrice": web3.to_wei(gas_price, "gwei"),
        }
    )
    input_data = bytes.fromhex(transaction["data"][2:])
    deadline = web3.eth.get_block("latest").timestamp + 3600
    dapp.execute_transaction(
        private_key, "multicall", [deadline, [input_data]], value_eth, gas_price, 534353
    )


def mesprotocol(private_key):
    dapp = Dapp(SCROLL_RPC, "0x8f3Ddd0FBf3e78CA1D6cd17379eD88E261249B52", mes_abi)
    value_eth = "{:.8f}".format(
        random.uniform(min_goerli_to_spend, max_goerli_to_spend)
    )
    dapp.execute_transaction(
        private_key,
        "deposit",
        ["0x0000000000000000000000000000000000000000", web3.to_wei(value_eth, "ether")],
        value_eth,
        0.001,
        534353,
    )


def aave_deposit(private_key):
    dapp = Dapp(
        SCROLL_RPC, "0x57ce905CfD7f986A929A26b006f797d181dB706e", aave_deposit_abi
    )
    address = web3.eth.account.from_key(private_key).address
    value_eth = "{:.8f}".format(
        random.uniform(min_goerli_to_spend, max_goerli_to_spend)
    )
    dapp.execute_transaction(
        private_key,
        "depositETH",
        ["0x48914C788295b5db23aF2b5F0B3BE775C4eA9440", address, 0],
        value_eth,
        0.001,
        534353,
    )


def aave_borrow(private_key):
    dapp = Dapp(
        SCROLL_RPC, "0x48914C788295b5db23aF2b5F0B3BE775C4eA9440", aave_borrow_abi
    )
    address = web3.eth.account.from_key(private_key).address
    dapp.execute_transaction(
        private_key,
        "borrow",
        [
            "0x186C0C26c45A8DA1Da34339ee513624a9609156d",
            int(usdt_to_borrow) * 10**6,
            1,
            0,
            address,
        ],
        0,
        0.001,
        534353,
    )


def syncswap(private_key):
    amount_in = "{:.8f}".format(
        random.uniform(min_goerli_to_spend, max_goerli_to_spend)
    )
    dapp = Dapp(SCROLL_RPC, "0xC458eED598eAb247ffc19d15F19cf06ae729432c", syncswap_abi)
    address = web3.eth.account.from_key(private_key).address
    first_data = encode(
        ["address", "address", "uint8"],
        [
            web3.to_checksum_address("0x7160570bb153edd0ea1775ec2b2ac9b65f1ab61b"),
            web3.to_checksum_address("0xcff605daeaaf1b0d91993d193808475ddc285547"),
            0,
        ],
    )
    second_data = encode(
        ["address", "address", "uint8"],
        [
            web3.to_checksum_address("0x9b4e2c47e57d1331e6398cf605cbe895b4f93a87"),
            web3.to_checksum_address(address),
            2,
        ],
    )
    paths = [
        {
            "steps": [
                {
                    "pool": "0xb490AA41915cE1f7c1aC2f55dB66cc2e1D85A53a",
                    "data": first_data,
                    "callback": "0x0000000000000000000000000000000000000000",
                    "callbackData": b"",
                },
                {
                    "pool": "0xcFf605dAEaAF1b0D91993D193808475dDc285547",
                    "data": second_data,
                    "callback": "0x0000000000000000000000000000000000000000",
                    "callbackData": b"",
                },
            ],
            "tokenIn": "0x0000000000000000000000000000000000000000",
            "amountIn": web3.to_wei(amount_in, "ether"),
        }
    ]
    deadline = web3.eth.get_block("latest").timestamp + 3600
    dapp.execute_transaction(
        private_key,
        "swap",
        [paths, 0, deadline],
        amount_in,
        0.001,
        534353,
    )


def random_sleep():
    sleep_duration = random.randint(from_sec, to_sec)
    print(f"Sleeping for {sleep_duration} seconds")
    time.sleep(sleep_duration)


if __name__ == "__main__":
    choice = int(
        input(
            "\n----------------------\n1: Buy GoerliETH (using ETH in Arbitrum, testnetbridge)\n2: Bridge GoerliETH -> ScrollETH (scroll.io/bridge)\n3: Uniswap ScrollETH -> USDC\n4: Syncswap ScrollETH -> USDC\n5: MES protocol deposit\n6: AAVE deposit\n7: AAVE borrow USDT (AAVE deposit needed)\nChoice: "
        )
    )
    for key in private_keys:
        try:
            if choice == 1:
                buy_goerli(key)
            elif choice == 2:
                bridge_scrollio(key)
            elif choice == 3:
                uniswap(key)
            elif choice == 4:
                syncswap(key)
            elif choice == 5:
                mesprotocol(key)
            elif choice == 6:
                aave_deposit(key)
            elif choice == 7:
                aave_borrow(key)
            else:
                print(f"Wrong choice number. 1 | 2 | 3 ...")
        except Exception as e:
            print(f"Transaction failed for private key: {key} | Error: {e}")
            failed_keys.append(key)
