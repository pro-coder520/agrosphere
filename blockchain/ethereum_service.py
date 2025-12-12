"""
AgroMentor 360 - Ethereum Blockchain Service
Handles wallet creation, ERC-20 token transfers, and blockchain interactions
"""

from web3 import Web3
from web3.middleware import geth_poa_middleware
from eth_account import Account
from django.conf import settings
from cryptography.fernet import Fernet
import logging
from decimal import Decimal
import json

logger = logging.getLogger(__name__)


# ERC-20 ABI (Standard Interface)
ERC20_ABI = json.loads('''[
    {
        "constant": true,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function"
    },
    {
        "constant": false,
        "inputs": [
            {"name": "_to", "type": "address"},
            {"name": "_value", "type": "uint256"}
        ],
        "name": "transfer",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function"
    },
    {
        "constant": true,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "type": "function"
    },
    {
        "constant": true,
        "inputs": [],
        "name": "symbol",
        "outputs": [{"name": "", "type": "string"}],
        "type": "function"
    },
    {
        "constant": true,
        "inputs": [],
        "name": "totalSupply",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function"
    },
    {
        "constant": false,
        "inputs": [
            {"name": "_spender", "type": "address"},
            {"name": "_value", "type": "uint256"}
        ],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function"
    },
    {
        "constant": true,
        "inputs": [
            {"name": "_owner", "type": "address"},
            {"name": "_spender", "type": "address"}
        ],
        "name": "allowance",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function"
    },
    {
        "anonymous": false,
        "inputs": [
            {"indexed": true, "name": "from", "type": "address"},
            {"indexed": true, "name": "to", "type": "address"},
            {"indexed": false, "name": "value", "type": "uint256"}
        ],
        "name": "Transfer",
        "type": "event"
    }
]''')


class EthereumService:
    """
    Service class for Ethereum blockchain operations
    """
    
    def __init__(self):
        """
        Initialize Web3 client with configuration from settings
        """
        self.network = settings.ETHEREUM_CONFIG['NETWORK']
        self.rpc_url = settings.ETHEREUM_CONFIG['RPC_URL']
        
        # Initialize Web3
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        
        # Add PoA middleware for testnets like Sepolia
        if self.network in ['sepolia', 'goerli']:
            self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        
        # Verify connection
        if not self.w3.is_connected():
            logger.error(f"Failed to connect to Ethereum network: {self.network}")
            raise Exception(f"Cannot connect to Ethereum RPC: {self.rpc_url}")
        
        # Get chain ID
        chain_ids = settings.ETHEREUM_CONFIG['CHAIN_ID']
        self.chain_id = chain_ids.get(self.network, 1)
        
        # AgroCoin contract
        self.agrocoin_address = settings.ETHEREUM_CONFIG['AGROCOIN_CONTRACT_ADDRESS']
        if self.agrocoin_address:
            self.agrocoin_contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(self.agrocoin_address),
                abi=ERC20_ABI
            )
        else:
            self.agrocoin_contract = None
        
        # Gas settings
        self.gas_price_gwei = settings.ETHEREUM_CONFIG['GAS_PRICE_GWEI']
        self.gas_limit = settings.ETHEREUM_CONFIG['GAS_LIMIT']
        
        # Encryption for private keys
        self.cipher = Fernet(settings.SECRET_KEY.encode()[:32].ljust(32, b'0'))
        
        logger.info(f"Ethereum service initialized on {self.network} (Chain ID: {self.chain_id})")
    
    def create_wallet(self):
        """
        Create a new Ethereum wallet
        
        Returns:
            dict: Contains address and encrypted_private_key
        """
        try:
            # Create new account
            account = Account.create()
            
            # Get address
            address = account.address
            
            # Get private key
            private_key = account.key.hex()
            
            # Encrypt private key for secure storage
            encrypted_private_key = self.cipher.encrypt(private_key.encode()).decode()
            
            logger.info(f"Created new Ethereum wallet: {address}")
            
            return {
                'address': address,
                'encrypted_private_key': encrypted_private_key
            }
        
        except Exception as e:
            logger.error(f"Error creating wallet: {str(e)}")
            raise Exception(f"Wallet creation failed: {str(e)}")
    
    def decrypt_private_key(self, encrypted_private_key):
        """
        Decrypt stored private key
        
        Args:
            encrypted_private_key: Encrypted private key string
            
        Returns:
            str: Decrypted private key
        """
        try:
            decrypted = self.cipher.decrypt(encrypted_private_key.encode()).decode()
            return decrypted
        except Exception as e:
            logger.error(f"Error decrypting private key: {str(e)}")
            raise Exception("Failed to decrypt wallet key")
    
    def get_balance(self, address):
        """
        Get ETH balance for a wallet
        
        Args:
            address: Wallet address
            
        Returns:
            Decimal: ETH balance
        """
        try:
            checksum_address = Web3.to_checksum_address(address)
            balance_wei = self.w3.eth.get_balance(checksum_address)
            balance_eth = self.w3.from_wei(balance_wei, 'ether')
            
            return Decimal(str(balance_eth))
        
        except Exception as e:
            logger.error(f"Error getting ETH balance for {address}: {str(e)}")
            return Decimal('0')
    
    def get_token_balance(self, address):
        """
        Get AgroCoin (ERC-20) balance for a wallet
        
        Args:
            address: Wallet address
            
        Returns:
            Decimal: Token balance
        """
        try:
            if not self.agrocoin_contract:
                logger.warning("AgroCoin contract not configured")
                return Decimal('0')
            
            checksum_address = Web3.to_checksum_address(address)
            
            # Get token decimals
            decimals = self.agrocoin_contract.functions.decimals().call()
            
            # Get balance
            balance_raw = self.agrocoin_contract.functions.balanceOf(checksum_address).call()
            balance = Decimal(balance_raw) / Decimal(10 ** decimals)
            
            return balance
        
        except Exception as e:
            logger.error(f"Error getting token balance for {address}: {str(e)}")
            return Decimal('0')
    
    def transfer_eth(self, from_private_key, to_address, amount_eth):
        """
        Transfer ETH from one wallet to another
        
        Args:
            from_private_key: Sender's private key
            to_address: Recipient's address
            amount_eth: Amount in ETH
            
        Returns:
            str: Transaction hash
        """
        try:
            # Create account from private key
            account = Account.from_key(from_private_key)
            from_address = account.address
            
            # Convert amount to Wei
            amount_wei = self.w3.to_wei(amount_eth, 'ether')
            
            # Get nonce
            nonce = self.w3.eth.get_transaction_count(from_address)
            
            # Build transaction
            transaction = {
                'nonce': nonce,
                'to': Web3.to_checksum_address(to_address),
                'value': amount_wei,
                'gas': self.gas_limit,
                'gasPrice': self.w3.to_wei(self.gas_price_gwei, 'gwei'),
                'chainId': self.chain_id
            }
            
            # Sign transaction
            signed_txn = self.w3.eth.account.sign_transaction(transaction, from_private_key)
            
            # Send transaction
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            # Wait for receipt
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            if receipt['status'] == 1:
                logger.info(f"ETH transfer successful. Hash: {tx_hash.hex()}")
                return tx_hash.hex()
            else:
                raise Exception("Transaction failed")
        
        except Exception as e:
            logger.error(f"ETH transfer failed: {str(e)}")
            raise Exception(f"Transfer failed: {str(e)}")
    
    def transfer_tokens(self, from_wallet, to_wallet, amount, description="Token transfer"):
        """
        Transfer AgroCoin tokens between wallets
        
        Args:
            from_wallet: Sender's Wallet model instance
            to_wallet: Recipient's Wallet model instance
            amount: Amount of tokens to transfer
            description: Transaction description
            
        Returns:
            dict: Transaction details including hash
        """
        try:
            if not self.agrocoin_contract:
                raise Exception("AgroCoin contract not configured")
            
            amount_decimal = Decimal(str(amount))
            
            # Check sufficient balance
            if not from_wallet.has_sufficient_balance(amount_decimal):
                raise ValueError("Insufficient balance")
            
            # For demo mode, simulate transaction
            if settings.DEMO_MODE:
                import hashlib
                import time
                mock_data = f"{from_wallet.public_key}{to_wallet.public_key}{amount}{time.time()}"
                tx_hash = '0x' + hashlib.sha256(mock_data.encode()).hexdigest()
            else:
                # Execute real blockchain transaction
                from_private_key = self.decrypt_private_key(from_wallet.encrypted_private_key)
                tx_hash = self._execute_token_transfer(
                    from_private_key,
                    to_wallet.public_key,
                    amount_decimal
                )
            
            # Update wallet balances
            from_wallet.deduct_balance(amount_decimal)
            to_wallet.add_balance(amount_decimal)
            
            logger.info(f"Token transfer: {amount} AC from {from_wallet.user.phone_number} "
                       f"to {to_wallet.user.phone_number}")
            
            return {
                'transaction_hash': tx_hash,
                'from_address': from_wallet.public_key,
                'to_address': to_wallet.public_key,
                'amount': float(amount_decimal),
                'status': 'confirmed'
            }
        
        except Exception as e:
            logger.error(f"Token transfer failed: {str(e)}")
            raise Exception(f"Transfer failed: {str(e)}")
    
    def _execute_token_transfer(self, from_private_key, to_address, amount):
        """
        Execute actual ERC-20 token transfer on Ethereum
        
        Args:
            from_private_key: Sender's private key
            to_address: Recipient's address
            amount: Amount of tokens
            
        Returns:
            str: Transaction hash
        """
        try:
            if not self.agrocoin_contract:
                raise Exception("AgroCoin contract not configured")
            
            # Create account
            account = Account.from_key(from_private_key)
            from_address = account.address
            
            # Get token decimals
            decimals = self.agrocoin_contract.functions.decimals().call()
            
            # Convert amount to smallest unit
            amount_raw = int(amount * (10 ** decimals))
            
            # Get nonce
            nonce = self.w3.eth.get_transaction_count(from_address)
            
            # Build transaction
            transaction = self.agrocoin_contract.functions.transfer(
                Web3.to_checksum_address(to_address),
                amount_raw
            ).build_transaction({
                'nonce': nonce,
                'gas': self.gas_limit,
                'gasPrice': self.w3.to_wei(self.gas_price_gwei, 'gwei'),
                'chainId': self.chain_id
            })
            
            # Sign transaction
            signed_txn = self.w3.eth.account.sign_transaction(transaction, from_private_key)
            
            # Send transaction
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            # Wait for confirmation
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            if receipt['status'] == 1:
                logger.info(f"Token transfer successful. Hash: {tx_hash.hex()}")
                return tx_hash.hex()
            else:
                raise Exception("Transaction failed")
        
        except Exception as e:
            logger.error(f"Token transfer failed: {str(e)}")
            raise
    
    def verify_transaction(self, tx_hash):
        """
        Verify a transaction on the blockchain
        
        Args:
            tx_hash: Transaction hash to verify
            
        Returns:
            dict: Transaction details
        """
        try:
            # Get transaction receipt
            receipt = self.w3.eth.get_transaction_receipt(tx_hash)
            
            if receipt:
                return {
                    'confirmed': receipt['status'] == 1,
                    'block_number': receipt['blockNumber'],
                    'gas_used': receipt['gasUsed'],
                    'status': 'confirmed' if receipt['status'] == 1 else 'failed'
                }
            
            # Transaction exists but not yet mined
            try:
                tx = self.w3.eth.get_transaction(tx_hash)
                if tx:
                    return {
                        'confirmed': False,
                        'status': 'pending'
                    }
            except:
                pass
            
            return {
                'confirmed': False,
                'status': 'not_found'
            }
        
        except Exception as e:
            logger.error(f"Error verifying transaction {tx_hash}: {str(e)}")
            return {
                'confirmed': False,
                'status': 'error',
                'error': str(e)
            }
    
    def estimate_gas_fee(self, transaction_type='transfer'):
        """
        Estimate gas fees for a transaction
        
        Args:
            transaction_type: Type of transaction
            
        Returns:
            dict: Estimated gas fees in ETH and Gwei
        """
        try:
            # Get current gas price from network
            gas_price_wei = self.w3.eth.gas_price
            gas_price_gwei = self.w3.from_wei(gas_price_wei, 'gwei')
            
            # Estimate gas for transaction type
            gas_estimates = {
                'transfer': 21000,  # ETH transfer
                'token_transfer': 65000,  # ERC-20 transfer
                'contract_call': 100000,  # Contract interaction
            }
            
            estimated_gas = gas_estimates.get(transaction_type, self.gas_limit)
            
            # Calculate total fee
            fee_wei = gas_price_wei * estimated_gas
            fee_eth = self.w3.from_wei(fee_wei, 'ether')
            
            return {
                'gas_price_gwei': float(gas_price_gwei),
                'estimated_gas': estimated_gas,
                'estimated_fee_eth': float(fee_eth),
                'estimated_fee_wei': fee_wei
            }
        
        except Exception as e:
            logger.error(f"Error estimating gas: {str(e)}")
            return {
                'gas_price_gwei': self.gas_price_gwei,
                'estimated_gas': self.gas_limit,
                'estimated_fee_eth': 0.002,
                'error': str(e)
            }
    
    def get_transaction_details(self, tx_hash):
        """
        Get detailed information about a transaction
        
        Args:
            tx_hash: Transaction hash
            
        Returns:
            dict: Transaction details
        """
        try:
            # Get transaction
            tx = self.w3.eth.get_transaction(tx_hash)
            
            # Get receipt if available
            try:
                receipt = self.w3.eth.get_transaction_receipt(tx_hash)
            except:
                receipt = None
            
            details = {
                'hash': tx_hash,
                'from': tx['from'],
                'to': tx['to'],
                'value_wei': tx['value'],
                'value_eth': float(self.w3.from_wei(tx['value'], 'ether')),
                'gas_price_gwei': float(self.w3.from_wei(tx['gasPrice'], 'gwei')),
                'nonce': tx['nonce'],
                'block_number': tx.get('blockNumber'),
            }
            
            if receipt:
                details['status'] = 'confirmed' if receipt['status'] == 1 else 'failed'
                details['gas_used'] = receipt['gasUsed']
                details['block_hash'] = receipt['blockHash'].hex()
            else:
                details['status'] = 'pending'
            
            return details
        
        except Exception as e:
            logger.error(f"Error getting transaction details: {str(e)}")
            return {
                'hash': tx_hash,
                'status': 'error',
                'error': str(e)
            }
    
    def fund_wallet_testnet(self, address):
        """
        Fund wallet on testnet (faucet simulation)
        Note: Real testnets require using actual faucets
        
        Args:
            address: Wallet address to fund
            
        Returns:
            dict: Funding result
        """
        try:
            if self.network == 'mainnet':
                raise Exception("Cannot fund mainnet wallets via faucet")
            
            logger.info(f"Testnet wallet funding requested for {address}")
            
            # Provide faucet links for different testnets
            faucets = {
                'sepolia': [
                    'https://sepoliafaucet.com/',
                    'https://faucet.sepolia.dev/',
                    'https://www.alchemy.com/faucets/ethereum-sepolia'
                ],
                'goerli': [
                    'https://goerlifaucet.com/',
                    'https://faucet.goerli.mudit.blog/'
                ]
            }
            
            return {
                'success': False,
                'message': f'Please use a faucet to fund your {self.network} wallet',
                'faucets': faucets.get(self.network, []),
                'address': address
            }
        
        except Exception as e:
            logger.error(f"Faucet request error: {str(e)}")
            raise


# Singleton instance
ethereum_service = EthereumService()