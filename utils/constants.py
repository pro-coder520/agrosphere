"""
AgroMentor 360 - Application Constants
Centralized constants used throughout the application
"""

# Nigerian States and Cities
NIGERIAN_STATES = [
    'Abia', 'Adamawa', 'Akwa Ibom', 'Anambra', 'Bauchi', 'Bayelsa',
    'Benue', 'Borno', 'Cross River', 'Delta', 'Ebonyi', 'Edo',
    'Ekiti', 'Enugu', 'Gombe', 'Imo', 'Jigawa', 'Kaduna', 'Kano',
    'Katsina', 'Kebbi', 'Kogi', 'Kwara', 'Lagos', 'Nasarawa', 'Niger',
    'Ogun', 'Ondo', 'Osun', 'Oyo', 'Plateau', 'Rivers', 'Sokoto',
    'Taraba', 'Yobe', 'Zamfara', 'FCT'
]

MAJOR_CITIES = [
    'Lagos', 'Abuja', 'Kano', 'Ibadan', 'Port Harcourt',
    'Benin City', 'Jos', 'Kaduna', 'Enugu', 'Aba',
    'Onitsha', 'Warri', 'Ilorin', 'Calabar', 'Akure',
    'Abeokuta', 'Maiduguri', 'Zaria', 'Owerri', 'Uyo'
]

# Farming Categories
CROP_CATEGORIES = [
    ('vegetables', 'Vegetables'),
    ('fruits', 'Fruits'),
    ('grains', 'Grains'),
    ('legumes', 'Legumes'),
    ('tubers', 'Tubers'),
    ('herbs', 'Herbs'),
    ('cash_crops', 'Cash Crops'),
]

COMMON_CROPS = {
    'vegetables': ['Tomatoes', 'Pepper', 'Onions', 'Cabbage', 'Lettuce', 'Cucumber'],
    'fruits': ['Oranges', 'Banana', 'Pineapple', 'Mango', 'Pawpaw', 'Watermelon'],
    'grains': ['Maize', 'Rice', 'Millet', 'Sorghum', 'Wheat'],
    'legumes': ['Beans', 'Groundnut', 'Soybean', 'Cowpea'],
    'tubers': ['Yam', 'Cassava', 'Sweet Potato', 'Cocoyam'],
    'herbs': ['Basil', 'Mint', 'Parsley', 'Scent Leaf'],
    'cash_crops': ['Cocoa', 'Palm Oil', 'Rubber', 'Cotton', 'Cashew'],
}

# Farm Types
FARM_TYPES = [
    ('traditional', 'Traditional Farm'),
    ('urban', 'Urban/Mini Farm'),
    ('hydroponic', 'Hydroponic'),
    ('greenhouse', 'Greenhouse'),
    ('rooftop', 'Rooftop Farm'),
    ('balcony', 'Balcony Garden'),
    ('container', 'Container Farm'),
]

# Soil Types
SOIL_TYPES = [
    ('loamy', 'Loamy'),
    ('sandy', 'Sandy'),
    ('clay', 'Clay'),
    ('silt', 'Silt'),
    ('peaty', 'Peaty'),
    ('chalky', 'Chalky'),
]

# Expert Specializations
EXPERT_SPECIALIZATIONS = [
    ('soil_science', 'Soil Science'),
    ('veterinary', 'Veterinary Medicine'),
    ('agronomy', 'Agronomy'),
    ('crop_science', 'Crop Science'),
    ('farm_management', 'Farm Management'),
    ('irrigation', 'Irrigation'),
    ('pest_control', 'Pest Control'),
    ('organic_farming', 'Organic Farming'),
]

# Experience Levels
EXPERIENCE_LEVELS = [
    ('beginner', 'Beginner (0-1 year)'),
    ('intermediate', 'Intermediate (1-3 years)'),
    ('advanced', 'Advanced (3-5 years)'),
    ('expert', 'Expert (5+ years)'),
]

# Seasons in Nigeria
SEASONS = [
    ('dry', 'Dry Season (November - March)'),
    ('rainy', 'Rainy Season (April - October)'),
    ('all_year', 'All Year Round'),
]

# Transaction Types
TRANSACTION_TYPES = [
    ('purchase', 'Token Purchase'),
    ('transfer', 'Transfer'),
    ('payment', 'Payment'),
    ('reward', 'Reward'),
    ('refund', 'Refund'),
    ('investment', 'Investment'),
    ('investment_return', 'Investment Return'),
    ('expert_payment', 'Expert Payment'),
    ('marketplace_purchase', 'Marketplace Purchase'),
]

# Payment Methods
PAYMENT_METHODS = [
    ('paystack', 'Paystack'),
    ('flutterwave', 'Flutterwave'),
    ('bank_transfer', 'Bank Transfer'),
    ('ussd', 'USSD Payment'),
    ('agrocoin', 'AgroCoin'),
]

# Order Statuses
ORDER_STATUSES = [
    ('pending', 'Pending Payment'),
    ('paid', 'Paid'),
    ('processing', 'Processing'),
    ('shipped', 'Shipped'),
    ('delivered', 'Delivered'),
    ('cancelled', 'Cancelled'),
    ('refunded', 'Refunded'),
]

# Investment Categories
INVESTMENT_CATEGORIES = [
    ('poultry', 'Poultry Farming'),
    ('fishery', 'Fish Farming'),
    ('crops', 'Crop Farming'),
    ('livestock', 'Livestock'),
    ('mixed', 'Mixed Farming'),
]

# Notification Types
NOTIFICATION_TYPES = [
    ('sms', 'SMS'),
    ('email', 'Email'),
    ('push', 'Push Notification'),
    ('in_app', 'In-App Notification'),
]

# Weather Alert Types
WEATHER_ALERT_TYPES = [
    ('rain', 'Heavy Rain'),
    ('drought', 'Drought Warning'),
    ('heat', 'Extreme Heat'),
    ('cold', 'Cold Weather'),
    ('storm', 'Storm Warning'),
    ('frost', 'Frost Warning'),
]

# Alert Severity Levels
ALERT_SEVERITY = [
    ('info', 'Information'),
    ('warning', 'Warning'),
    ('alert', 'Alert'),
    ('emergency', 'Emergency'),
]

# User Roles
USER_ROLES = [
    ('farmer', 'Farmer'),
    ('expert', 'Expert'),
    ('investor', 'Investor'),
    ('admin', 'Administrator'),
]

# Languages Supported
LANGUAGES = [
    ('en', 'English'),
    ('yo', 'Yoruba'),
    ('ig', 'Igbo'),
    ('ha', 'Hausa'),
    ('pid', 'Pidgin'),
]

# Gamification Badges
ACHIEVEMENT_BADGES = [
    'Urban Farmer',
    'Farm Investor',
    'AgroChampion',
    'Early Adopter',
    'Green Thumb',
    'Harvest Master',
    'Expert Learner',
    'Community Builder',
    'Sustainability Hero',
]

# SDG Alignment
SDG_GOALS = {
    2: 'Zero Hunger',
    8: 'Decent Work & Economic Growth',
    9: 'Industry, Innovation & Infrastructure',
    11: 'Sustainable Cities & Communities',
    12: 'Responsible Consumption & Production',
    13: 'Climate Action',
}

# Platform Limits
MAX_FILE_SIZE_MB = 5
MAX_UPLOAD_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
MIN_INVESTMENT_AMOUNT_NGN = 5000
MIN_INVESTMENT_AMOUNT_AC = 50
PLATFORM_COMMISSION_RATE = 0.05  # 5%
MAX_TRANSFER_AMOUNT_AC = 10000

# Ethereum Networks
ETHEREUM_NETWORKS = {
    'mainnet': {
        'name': 'Ethereum Mainnet',
        'chain_id': 1,
        'explorer': 'https://etherscan.io'
    },
    'sepolia': {
        'name': 'Sepolia Testnet',
        'chain_id': 11155111,
        'explorer': 'https://sepolia.etherscan.io'
    },
    'goerli': {
        'name': 'Goerli Testnet',
        'chain_id': 5,
        'explorer': 'https://goerli.etherscan.io'
    },
    'ganache': {
        'name': 'Ganache Local',
        'chain_id': 1337,
        'explorer': None
    },
}

# Gas Limits (in gas units)
GAS_LIMITS = {
    'eth_transfer': 21000,
    'token_transfer': 65000,
    'token_approve': 45000,
    'contract_call': 100000,
}

# Cache Timeouts (in seconds)
CACHE_TIMEOUTS = {
    'short': 300,        # 5 minutes
    'medium': 1800,      # 30 minutes
    'long': 3600,        # 1 hour
    'day': 86400,        # 24 hours
    'week': 604800,      # 7 days
}

# API Rate Limits
RATE_LIMITS = {
    'anonymous': '100/hour',
    'authenticated': '1000/hour',
    'ai_endpoint': '50/hour',
    'blockchain': '200/hour',
}

# Pagination
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# Date Formats
DATE_FORMAT = '%Y-%m-%d'
DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'
TIME_FORMAT = '%H:%M:%S'

# Error Messages
ERROR_MESSAGES = {
    'insufficient_balance': 'Insufficient balance to complete this transaction',
    'invalid_amount': 'Invalid amount specified',
    'wallet_not_found': 'Wallet not found',
    'transaction_failed': 'Transaction failed. Please try again',
    'network_error': 'Network error. Please check your connection',
    'unauthorized': 'You are not authorized to perform this action',
    'not_found': 'Resource not found',
    'invalid_input': 'Invalid input provided',
}

# Success Messages
SUCCESS_MESSAGES = {
    'transaction_complete': 'Transaction completed successfully',
    'wallet_created': 'Wallet created successfully',
    'profile_updated': 'Profile updated successfully',
    'order_placed': 'Order placed successfully',
    'investment_complete': 'Investment completed successfully',
}

# File Upload Settings
ALLOWED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif']
ALLOWED_DOCUMENT_EXTENSIONS = ['.pdf', '.doc', '.docx']
ALLOWED_VIDEO_EXTENSIONS = ['.mp4', '.mov', '.avi']

# Regex Patterns
REGEX_PATTERNS = {
    'phone': r'^\+?234?[789]\d{9}$',
    'email': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
    'ethereum_address': r'^0x[a-fA-F0-9]{40}$',
    'transaction_hash': r'^0x[a-fA-F0-9]{64}$',
}