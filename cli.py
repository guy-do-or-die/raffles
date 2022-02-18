#! .env/bin/python

import click
import itertools

from time import time
from functools import wraps
from pprint import pprint as pp

from web3 import Web3
from web3.middleware import geth_poa_middleware

from config import ENTRIES_LIMIT, CHAIN_RPC, CHAIN_ID, PUBLIC_KEY, PRIVATE_KEY, CONTRACT_ADDR, CONTRACT_ABI

w3 = Web3(Web3.HTTPProvider(CHAIN_RPC, request_kwargs={"timeout": 60}))
w3.middleware_onion.inject(geth_poa_middleware, layer=0)


Raffles = w3.eth.contract(address=w3.toChecksumAddress(CONTRACT_ADDR), abi=CONTRACT_ABI)


def timeit(fn):
    @wraps(fn)
    def timed(*args, **kwargs):
        print(f"{fn.__name__}ing {' '.join(args)}")
        ts = time()
        res = fn(*args, **kwargs)
        tf = time()
        print(f"took {'%2.4f sec' % (tf-ts)}\n\n")
        return res

    return timed


@timeit
def call(method, **params):
    res = getattr(Raffles.functions, method)(**params).call()
    print(f"returned value:\n{res}")
    return res


@timeit
def transact(
    method, value=0, gas=int(3 * 1e6), max_fee=w3.eth.gas_price, wait=True, verbose=False, **params
):
    nonce = w3.eth.get_transaction_count(PUBLIC_KEY)
    tx = getattr(Raffles.functions, method)(**params).buildTransaction(
        {
            "chainId": CHAIN_ID,
            "from": PUBLIC_KEY,
            "nonce": nonce + 1,
            "value": value,
            "gas": gas,
            "maxFeePerGas": max_fee * 2
        }
    )

    signed_tx = w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
    txsh = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
    res = dict(tx=txsh.hex())

    if wait:
        res["receipt"] = w3.eth.wait_for_transaction_receipt(txsh)
        verbose and pp(dict(res["receipt"]))
    else:
        verbose and print(f"tx created: {txsh.hex()}")

    return res


@click.group()
def cli():
    click.echo("raffling!")


@cli.command()
def create():
    transact("create")


@cli.command()
def list():
    call("list")


@cli.command()
@click.argument("index", type=int)
def state(index):
    call("state", index=index)


@cli.command()
@click.argument("index", type=int)
def entries(index):
    call("entries", index=index)


@cli.command()
@click.argument("index", type=int)
def winners(index):
    call("winners", index=index)


@cli.command()
@click.argument("index", type=int)
@click.argument("number", type=int)
@click.option("--verbose", "-v", type=bool, default=False, help="Show transactions details")
def select_winners(index, number, verbose):
    transact("selectWinners", index=index, number=number, verbose=verbose)


@cli.command()
@click.argument("index", type=int)
@click.option("--address", "-a", type=str, help="Single address")
@click.option("--addresses", "-l", type=str, help="List of address separated by commas")
@click.option("--path", "-f", type=click.Path(exists=True), help="Path to a file with addresses")
@click.option("--overwrite", "-o", type=bool, default=False, help="Reset entries")
@click.option("--verbose", "-v", type=bool, default=False, help="Show transactions details")
def add_entries(index, address, addresses, path, overwrite, verbose):
    def _add_entries(addresses, _overwrite=overwrite):
        transact(
            "addEntries",
            verbose=verbose,
            index=index,
            addresses=[w3.toChecksumAddress(l.strip()) for l in addresses],
            overwrite=_overwrite,
        )

    if address:
        _add_entries([address])
    elif addresses:
        _add_entries(addresses.split(","))
    elif path:

        def read(n, iterable):
            it = iter(iterable)
            while 1:
                chunk = tuple(itertools.islice(it, n))
                if not chunk:
                    return
                yield chunk

        with open(path, "r") as f:
            for addresses in read(ENTRIES_LIMIT, f):
                _add_entries(addresses, _overwrite=overwrite)
                overwrite = False
    else:
        raise click.UsageError("Provide address, list of addresses or path to its file")


if __name__ == "__main__":
    cli()
