from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
from eth_account import Account
from agrosphere import settings
from cryptography.fernet import Fernet
from decimal import Decimal
from django.core.cache import cache
import logging
import json

logger = logging.getLogger(__name__)

# Minified ERC-20 ABI to save memory/space
ERC20_ABI = json.loads('[{"constant":true,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"},{"constant":false,"inputs":[{"name":"_to","type":"address"},{"name":"_value","type":"uint256"}],"name":"transfer","outputs":[{"name":"","type":"bool"}],"type":"function"},{"constant":true,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"type":"function"},{"constant":true,"inputs":[],"name":"symbol","outputs":[{"name":"","type":"string"}],"type":"function"},{"constant":false,"inputs":[{"name":"_spender","type":"address"},{"name":"_value","type":"uint256"}],"name":"approve","outputs":[{"name":"","type":"bool"}],"type":"function"}]')

class EthereumService:
    """
    Optimized Service for Ethereum blockchain operations
    """
    
    def __init__(self):
        self.network = settings.ETHEREUM_CONFIG.get('NETWORK', 'sepolia')
        self.rpc_url = settings.ETHEREUM_CONFIG['RPC_URL']
        self.chain_id = settings.ETHEREUM_CONFIG.get('CHAIN_ID', {}).get(self.network, 11155111)
        
        # Initialize Web3 with increased timeout for slow nodes
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url, request_kwargs={'timeout': 10}))
        
        # Inject middleware for PoA networks (Sepolia, Goerli, BSC, Polygon)
        self.w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
        
        # Security: Cipher for private keys
        # Ensure SECRET_KEY is 32 bytes for Fernet
        key = settings.SECRET_KEY.encode()[:32].ljust(32, b'0') # type: ignore
        self.cipher = Fernet(base64.urlsafe_b64encode(key) if len(key) == 32 else key)

        # Smart Contract Setup
        self.agrocoin_address = settings.ETHEREUM_CONFIG.get('AGROCOIN_CONTRACT_ADDRESS')
        self.agrocoin_contract = None
        self._decimals_cache = None  # Cache for token decimals

        if self.agrocoin_address:
            try:
                self.agrocoin_contract = self.w3.eth.contract(
                    address=Web3.to_checksum_address(self.agrocoin_address),
                    abi=ERC20_ABI
                )
            except Exception as e:
                logger.error(f"Failed to load contract: {e}")

        # Gas Config
        self.gas_price_gwei = settings.ETHEREUM_CONFIG.get('GAS_PRICE_GWEI', 50)
        self.gas_limit = settings.ETHEREUM_CONFIG.get('GAS_LIMIT', 100000)
        
        # Check connection lazily (Warn instead of Crash)
        if not self.w3.is_connected():
            logger.warning(f"⚠️ Web3 failed to connect to {self.rpc_url}")

    @property
    def decimals(self):
        """
        Lazy-load and cache decimals to reduce RPC calls.
        """
        if self._decimals_cache is None and self.agrocoin_contract:
            # Try to get from Django cache first
            cached_val = cache.get('agrocoin_decimals')
            if cached_val:
                self._decimals_cache = cached_val
            else:
                try:
                    self._decimals_cache = self.agrocoin_contract.functions.decimals().call()
                    cache.set('agrocoin_decimals', self._decimals_cache, timeout=86400) # Cache for 1 day
                except Exception as e:
                    logger.error(f"Could not fetch decimals: {e}")
                    return 18 # Default to 18 if fails
        return self._decimals_cache or 18

    def create_wallet(self):
        """Create and encrypt a new wallet"""
        try:
            account = Account.create()
            # Encrypt key immediately
            encrypted_key = self.cipher.encrypt(account.key.hex().encode()).decode()
            
            return {
                'address': account.address,
                'encrypted_private_key': encrypted_key
            }
        except Exception as e:
            logger.error(f"Wallet creation error: {e}")
            raise

    def decrypt_private_key(self, encrypted_key):
        return self.cipher.decrypt(encrypted_key.encode()).decode()

    def get_balance(self, address):
        """Get ETH balance (Native Coin)"""
        try:
            balance_wei = self.w3.eth.get_balance(Web3.to_checksum_address(address))
            return Decimal(str(self.w3.from_wei(balance_wei, 'ether')))
        except Exception as e:
            logger.error(f"ETH Balance check failed: {e}")
            return Decimal('0')

    def get_token_balance(self, address):
        """Get AgroCoin balance (Optimized)"""
        if not self.agrocoin_contract: return Decimal('0')
        
        try:
            addr = Web3.to_checksum_address(address)
            balance_raw = self.agrocoin_contract.functions.balanceOf(addr).call()
            # Use cached decimals
            return Decimal(balance_raw) / Decimal(10 ** self.decimals)
        except Exception as e:
            logger.error(f"Token Balance check failed: {e}")
            return Decimal('0')

    def transfer_tokens(self, from_wallet, to_wallet, amount):
        """
        Non-blocking Token Transfer
        Returns tx_hash immediately. Does NOT wait for confirmation.
        """
        if not self.agrocoin_contract:
            raise ValueError("Contract not configured")

        try:
            # 1. Prepare Data
            from_pk = self.decrypt_private_key(from_wallet.encrypted_private_key)
            from_account = Account.from_key(from_pk)
            to_addr = Web3.to_checksum_address(to_wallet.public_key)
            
            # Convert amount using cached decimals
            amount_raw = int(Decimal(str(amount)) * (10 ** self.decimals))
            
            # 2. Build Transaction
            # Optimizing: Fetch nonce and gas price in parallel implies async, 
            # for sync we just fetch them.
            nonce = self.w3.eth.get_transaction_count(from_account.address)
            
            # Dynamic gas price is safer than fixed setting
            current_gas = self.w3.eth.gas_price 
            
            tx = self.agrocoin_contract.functions.transfer(
                to_addr, 
                amount_raw
            ).build_transaction({
                'chainId': self.chain_id,
                'gas': self.gas_limit,
                'gasPrice': current_gas,
                'nonce': nonce,
            })

            # 3. Sign & Send
            signed_tx = self.w3.eth.account.sign_transaction(tx, from_pk)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
            # 4. Return Hash Immediately (Non-blocking)
            return {
                'transaction_hash': self.w3.to_hex(tx_hash),
                'status': 'pending' # Status is pending until confirmed by Celery task
            }

        except Exception as e:
            logger.error(f"Transfer failed: {e}")
            raise

    def transfer_eth(self, from_private_key, to_address, amount_eth):
        """
        Non-blocking ETH Transfer
        """
        try:
            account = Account.from_key(from_private_key)
            to_addr = Web3.to_checksum_address(to_address)
            amount_wei = self.w3.to_wei(amount_eth, 'ether')
            
            nonce = self.w3.eth.get_transaction_count(account.address)
            current_gas = self.w3.eth.gas_price

            tx = {
                'nonce': nonce,
                'to': to_addr,
                'value': amount_wei,
                'gas': 21000,
                'gasPrice': current_gas,
                'chainId': self.chain_id
            }

            signed_tx = self.w3.eth.account.sign_transaction(tx, from_private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)

            return self.w3.to_hex(tx_hash)

        except Exception as e:
            logger.error(f"ETH Transfer failed: {e}")
            raise

    def verify_transaction(self, tx_hash):
        """Check transaction status"""
        try:
            receipt = self.w3.eth.get_transaction_receipt(tx_hash)
            status = 'confirmed' if receipt['status'] == 1 else 'failed'
            return {
                'confirmed': True,
                'status': status,
                'block_number': receipt['blockNumber'],
                'gas_used': receipt['gasUsed']
            }
        except Exception:
            # If get_transaction_receipt fails, tx is likely still pending or not found
            return {'confirmed': False, 'status': 'pending'}

import base64

# Singleton
ethereum_service = EthereumService()