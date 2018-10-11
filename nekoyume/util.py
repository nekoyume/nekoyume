from coincurve import PublicKey
from keccak import sha3_256


def get_address(public_key: PublicKey) -> str:
    """Derive an Ethereum-style address from the given public key."""
    return '0x' + sha3_256(public_key.format(False)[1:]).hexdigest()[-40:]
