from django.urls import path
from . import views

app_name = 'blockchain'

urlpatterns = [
    # Wallet operations
    path('wallet/', views.get_wallet, name='get-wallet'),
    path('wallet/stats/', views.wallet_stats, name='wallet-stats'),
    
    # Token operations
    path('purchase-tokens/', views.purchase_tokens, name='purchase-tokens'),
    path('transfer/', views.transfer_tokens, name='transfer-tokens'),
    path('conversion-rate/', views.get_conversion_rate, name='conversion-rate'),
    
    # Transaction management
    path('transactions/', views.transaction_history, name='transaction-history'),
    path('verify/', views.verify_transaction, name='verify-transaction'),
    
    # Gas estimation
    path('estimate-gas/', views.estimate_gas_fee, name='estimate-gas'),
]