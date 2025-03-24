import asyncio
import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import List, Optional
from ecdsa import SigningKey, VerifyingKey, NIST256p

@dataclass
class Transaction:
    sender: str
    receiver: str
    amount: float
    input_gas: float
    output_gas: float
    self_consumption: float
    signature: Optional[str] = None

    def sign(self, private_key: SigningKey) -> None:
        tx_data = f"{self.sender}{self.receiver}{self.amount}".encode()
        self.signature = private_key.sign(tx_data).hex()

    def is_valid(self) -> bool:
        if self.sender == "Genesis":
            return True
        try:
            vk = VerifyingKey.from_string(bytes.fromhex(self.sender), curve=NIST256p)
            tx_data = f"{self.sender}{self.receiver}{self.amount}".encode()
            return vk.verify(bytes.fromhex(self.signature), tx_data)
        except Exception:
            return False

@dataclass
class Block:
    index: int
    previous_hash: str
    timestamp: float
    transactions: List[Transaction]
    nonce: int = 0
    hash: str = field(init=False)

    def __post_init__(self) -> None:
        self.hash = self.calculate_hash()

    def calculate_hash(self) -> str:
        block_data = json.dumps({
            "index": self.index,
            "previous_hash": self.previous_hash,
            "timestamp": self.timestamp,
            "nonce": self.nonce,
        }, sort_keys=True)
        return hashlib.sha256(block_data.encode()).hexdigest()

    async def mine(self, difficulty: int) -> None:
        while not self.hash.startswith("0" * difficulty):
            self.nonce += 1
            self.hash = self.calculate_hash()
            await asyncio.sleep(0)

class Blockchain:
    def __init__(self, difficulty: int = 4):
        self.chain = [self._create_genesis_block()]
        self.difficulty = difficulty
        self.pending_transactions: List[Transaction] = []

    def _create_genesis_block(self) -> Block:
        genesis_tx = Transaction(
            sender="Genesis",
            receiver="Genesis",
            amount=0,
            input_gas=0,
            output_gas=0,
            self_consumption=0
        )
        return Block(0, "0", time.time(), [genesis_tx])

    async def add_block(self) -> Block:
        if not self.pending_transactions:
            raise ValueError("Нет транзакций для добавления!")

        latest_block = self.chain[-1]
        new_block = Block(
            index=latest_block.index + 1,
            previous_hash=latest_block.hash,
            timestamp=time.time(),
            transactions=self.pending_transactions.copy(),
        )

        await new_block.mine(self.difficulty)
        self.chain.append(new_block)
        self.pending_transactions.clear()
        return new_block

    def is_valid(self) -> bool:
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i - 1]
            if current.hash != current.calculate_hash() or current.previous_hash != previous.hash:
                return False
        return True