from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.contrib.auth import authenticate
from accounts.models import User
from farming.models import Farm, Crop, FarmTask
from blockchain.models import Wallet
from marketplace.models import Product
from agrosphere import settings
import logging
logger = logging.getLogger(__name__)


class USSDSessionManager:
    """
    Manages USSD session state using Redis cache
    """
    
    def __init__(self):
        from django.core.cache import cache
        self.cache = cache
        self.session_timeout = 300  # 5 minutes
    
    def get_session(self, session_id):
        """Get session data from cache"""
        return self.cache.get(f'ussd_session_{session_id}', {})
    
    def set_session(self, session_id, data):
        """Store session data in cache"""
        self.cache.set(f'ussd_session_{session_id}', data, self.session_timeout)
    
    def clear_session(self, session_id):
        """Clear session data"""
        self.cache.delete(f'ussd_session_{session_id}')


session_manager = USSDSessionManager()


@csrf_exempt
@require_http_methods(["POST"])
def ussd_callback(request):
    """
    Main USSD callback handler for Africa's Talking
    
    Receives USSD requests and returns appropriate menu responses
    """
    
    # Get USSD parameters from Africa's Talking
    session_id = request.POST.get('sessionId', '')
    service_code = request.POST.get('serviceCode', '')
    phone_number = request.POST.get('phoneNumber', '')
    text = request.POST.get('text', '')
    
    logger.info(f"USSD Request - Session: {session_id}, Phone: {phone_number}, Text: {text}")
    
    # Get or initialize session data
    session_data = session_manager.get_session(session_id)
    
    # Parse user input
    user_input = text.split('*')
    current_level = len(user_input)
    
    # Check if user exists
    try:
        user = User.objects.get(phone_number=phone_number)
        session_data['user_id'] = str(user.id)
        session_data['authenticated'] = True
    except User.DoesNotExist:
        user = None
        session_data['authenticated'] = False
    
    # Save session
    session_manager.set_session(session_id, session_data)
    
    # Route to appropriate menu handler
    if current_level == 1 and not text:
        response = show_main_menu(user)
    elif not session_data.get('authenticated'):
        response = handle_registration(phone_number, user_input, session_data)
    else:
        response = handle_menu_navigation(user, user_input, session_data, session_id)
    
    return HttpResponse(response, content_type='text/plain')


def show_main_menu(user):
    """
    Display main USSD menu
    """
    if user:
        menu = f"CON Welcome {user.first_name}!\n"
        menu += "1. My Farm\n"
        menu += "2. Marketplace\n"
        menu += "3. AgroCoin Wallet\n"
        menu += "4. Farming Tips\n"
        menu += "5. Weather Alert\n"
        menu += "6. Expert Consultation\n"
        menu += "7. Account Settings"
    else:
        menu = "CON Welcome to Agrosphere\n"
        menu += "1. Register\n"
        menu += "2. Login\n"
        menu += "3. About Agrosphere"
    
    return menu


def handle_registration(phone_number, user_input, session_data):
    """
    Handle new user registration via USSD
    """
    level = len(user_input)
    
    if level == 1:
        if user_input[0] == '1':  # Register
            return "CON Enter your first name:"
        elif user_input[0] == '2':  # Login
            return "CON Enter your 4-digit PIN:"
        elif user_input[0] == '3':  # About
            return "END Agrosphere: Your AI farming companion. We provide crop guidance, expert access, and marketplace for Nigerian farmers."
    
    elif level == 2:
        if session_data.get('action') == 'register':
            session_data['first_name'] = user_input[1]
            return "CON Enter your last name:"
    
    elif level == 3:
        if session_data.get('action') == 'register':
            session_data['last_name'] = user_input[2]
            return "CON Enter your city:"
    
    elif level == 4:
        if session_data.get('action') == 'register':
            session_data['city'] = user_input[3]
            return "CON Create a 4-digit PIN:"
    
    elif level == 5:
        if session_data.get('action') == 'register':
            # Create user account
            try:
                user = User.objects.create(
                    phone_number=phone_number,
                    first_name=session_data.get('first_name'),
                    last_name=session_data.get('last_name'),
                    password=user_input[4]
                )
                user.ussd_pin = user_input[4]
                user.save()
                
                # Create user profile
                from accounts.models import UserProfile
                UserProfile.objects.create(
                    user=user,
                    city=session_data.get('city'),
                    state='Nigeria'
                )
                
                # Create wallet
                from blockchain.ethereum_service import ethereum_service
                wallet_data = ethereum_service.create_wallet()
                Wallet.objects.create(
                    user=user,
                    public_key=wallet_data['public_key'],
                    encrypted_private_key=wallet_data['encrypted_private_key']
                )
                
                session_manager.clear_session(session_data.get('session_id'))
                return f"END Registration successful! Welcome {user.first_name}. Dial {settings.AFRICAS_TALKING_CONFIG['USSD_SHORT_CODE']} to start farming."
            
            except Exception as e:
                logger.error(f"Registration error: {str(e)}")
                return "END Registration failed. Please try again."
    
    return "END Invalid input. Please try again."


def handle_menu_navigation(user, user_input, session_data, session_id):
    """
    Handle navigation through USSD menus for authenticated users
    """
    level = len(user_input)
    
    # Main menu selection
    if level == 1:
        choice = user_input[0]
        
        if choice == '1':  # My Farm
            return show_farm_menu(user)
        elif choice == '2':  # Marketplace
            return show_marketplace_menu(user)
        elif choice == '3':  # AgroCoin Wallet
            return show_wallet_menu(user)
        elif choice == '4':  # Farming Tips
            return show_farming_tips(user)
        elif choice == '5':  # Weather Alert
            return show_weather_alert(user)
        elif choice == '6':  # Expert Consultation
            return show_expert_menu(user)
        elif choice == '7':  # Account Settings
            return show_account_menu(user)
    
    # Sub-menu handling
    elif level == 2:
        main_choice = user_input[0]
        sub_choice = user_input[1]
        
        if main_choice == '1':  # Farm operations
            return handle_farm_operations(user, sub_choice, session_data)
        elif main_choice == '2':  # Marketplace
            return handle_marketplace_operations(user, sub_choice, session_data)
        elif main_choice == '3':  # Wallet
            return handle_wallet_operations(user, sub_choice, session_data)
    
    return "END Invalid selection. Please try again."


def show_farm_menu(user):
    """Show farm management menu"""
    farms = Farm.objects.filter(owner=user).count()
    
    menu = f"CON My Farm ({farms} farms)\n"
    menu += "1. View Farms\n"
    menu += "2. Add New Farm\n"
    menu += "3. View Tasks\n"
    menu += "4. Add Crop\n"
    menu += "5. Harvest Report\n"
    menu += "0. Back"
    
    return menu


def show_marketplace_menu(user):
    """Show marketplace menu"""
    menu = "CON Marketplace\n"
    menu += "1. Browse Products\n"
    menu += "2. My Orders\n"
    menu += "3. Sell Produce\n"
    menu += "4. Search by Category\n"
    menu += "0. Back"
    
    return menu


def show_wallet_menu(user):
    """Show AgroCoin wallet menu"""
    try:
        wallet = user.wallet
        balance_ac = wallet.agrocoin_balance
        balance_ngn = wallet.naira_equivalent
        
        menu = f"CON AgroCoin Wallet\n"
        menu += f"Balance: {balance_ac} AC (₦{balance_ngn})\n\n"
        menu += "1. Buy AgroCoin\n"
        menu += "2. Send AgroCoin\n"
        menu += "3. Transaction History\n"
        menu += "4. View Wallet Address\n"
        menu += "0. Back"
        
        return menu
    except:
        return "END Wallet not found. Please contact support."


def show_farming_tips(user):
    """Show AI-generated farming tips"""
    menu = "CON Farming Tips\n"
    menu += "1. Seasonal Tips\n"
    menu += "2. Crop Care Guide\n"
    menu += "3. Pest Control\n"
    menu += "4. Soil Management\n"
    menu += "5. Ask a Question\n"
    menu += "0. Back"
    
    return menu


def show_weather_alert(user):
    """Show weather alerts for user's farms"""
    try:
        farms = Farm.objects.filter(owner=user)
        if not farms:
            return "END No farms registered. Add a farm first."
        
        # Get latest weather alert
        from farming.models import WeatherAlert
        alerts = WeatherAlert.objects.filter(
            farm__in=farms,
            is_active=True
        ).order_by('-created_at')[:3]
        
        if alerts:
            response = "END Weather Alerts:\n"
            for alert in alerts:
                response += f"\n{alert.title}\n"
                response += f"{alert.description[:50]}...\n"
            return response
        else:
            return "END No active weather alerts. Conditions are favorable."
    
    except Exception as e:
        logger.error(f"Weather alert error: {str(e)}")
        return "END Unable to fetch weather alerts."


def show_expert_menu(user):
    """Show expert consultation menu"""
    menu = "CON Expert Consultation\n"
    menu += "1. Find an Expert\n"
    menu += "2. My Consultations\n"
    menu += "3. Book Consultation\n"
    menu += "0. Back"
    
    return menu


def show_account_menu(user):
    """Show account settings menu"""
    menu = f"CON Account: {user.get_full_name()}\n"
    menu += "1. View Profile\n"
    menu += "2. Change PIN\n"
    menu += "3. Language Settings\n"
    menu += "4. Notification Settings\n"
    menu += "0. Back"
    
    return menu


def handle_farm_operations(user, choice, session_data):
    """Handle farm-related operations"""
    if choice == '1':  # View Farms
        farms = Farm.objects.filter(owner=user)[:5]
        if farms:
            response = "CON My Farms:\n"
            for i, farm in enumerate(farms, 1):
                response += f"{i}. {farm.name} ({farm.city})\n"
            response += "0. Back"
            return response
        else:
            return "END No farms registered yet."
    
    elif choice == '3':  # View Tasks
        tasks = FarmTask.objects.filter(
            farm__owner=user,
            status='pending'
        ).order_by('due_date')[:5]
        
        if tasks:
            response = "END Pending Tasks:\n"
            for task in tasks:
                due = task.due_date.strftime('%d/%m')
                response += f"\n{task.title}\n"
                response += f"Due: {due}\n"
            return response
        else:
            return "END No pending tasks."
    
    elif choice == '5':  # Harvest Report
        crops = Crop.objects.filter(
            farm__owner=user,
            status='harvested'
        ).order_by('-actual_harvest_date')[:3]
        
        if crops:
            response = "END Recent Harvests:\n"
            for crop in crops:
                response += f"\n{crop.name}: {crop.actual_yield}kg\n"
            return response
        else:
            return "END No harvest records yet."
    
    return "END Feature coming soon."


def handle_marketplace_operations(user, choice, session_data):
    """Handle marketplace operations"""
    if choice == '1':  # Browse Products
        products = Product.objects.filter(
            status='available'
        ).order_by('-created_at')[:5]
        
        if products:
            response = "CON Available Products:\n"
            for i, product in enumerate(products, 1):
                price_ngn = product.price_naira
                response += f"{i}. {product.name} - ₦{price_ngn}\n"
            response += "0. Back"
            return response
        else:
            return "END No products available now."
    
    elif choice == '3':  # Sell Produce
        return "CON Sell Produce:\nEnter product name:"
    
    return "END Feature coming soon."


def handle_wallet_operations(user, choice, session_data):
    """Handle wallet operations"""
    if choice == '1':  # Buy AgroCoin
        return "CON Buy AgroCoin:\nEnter amount in Naira:\n(Min: ₦100)"
    
    elif choice == '3':  # Transaction History
        from blockchain.models import Transaction
        txns = Transaction.objects.filter(
            from_wallet=user.wallet
        ).order_by('-created_at')[:5]
        
        if txns:
            response = "END Recent Transactions:\n"
            for txn in txns:
                date = txn.created_at.strftime('%d/%m')
                response += f"\n{date}: {txn.transaction_type}\n"
                response += f"{txn.amount} AC - {txn.status}\n"
            return response
        else:
            return "END No transactions yet."
    
    elif choice == '4':  # View Wallet Address
        address = user.wallet.public_key
        return f"END Your Wallet:\n{address[:20]}...\n\nShare this address to receive AgroCoin."
    
    return "END Feature coming soon."


@api_view(['POST'])
@permission_classes([AllowAny])
def ussd_payment_callback(request):
    """
    Handle payment callbacks from USSD purchases
    """
    try:
        data = request.data
        phone_number = data.get('phoneNumber')
        amount = data.get('amount')
        reference = data.get('transactionId')
        
        # Find user
        user = User.objects.get(phone_number=phone_number)
        
        # Process AgroCoin purchase
        from blockchain.models import TokenPurchase
        conversion_rate = settings.ETHEREUM_CONFIG['AGROCOIN_TO_NAIRA_RATE']
        ac_amount = float(amount) / conversion_rate
        
        purchase = TokenPurchase.objects.create(
            user=user,
            naira_amount=amount,
            agrocoin_amount=ac_amount,
            conversion_rate=conversion_rate,
            payment_method='ussd',
            payment_reference=reference,
            status='completed'
        )
        
        # Credit wallet
        wallet = Wallet.objects.get(user=user)
        wallet.add_balance(ac_amount)
        
        logger.info(f"USSD purchase completed: {amount} NGN -> {ac_amount} AC for {phone_number}")
        
        return Response({'status': 'success'})
    
    except Exception as e:
        logger.error(f"USSD payment error: {str(e)}")
        return Response({'status': 'error', 'message': str(e)}, status=400)