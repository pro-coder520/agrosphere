from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Sum
from django.utils import timezone
from decimal import Decimal

from .models import FarmInvestment, InvestmentOpportunity, InvestmentReturn
from .serializers import (
    FarmInvestmentSerializer,
    InvestmentOpportunitySerializer,
    InvestmentReturnSerializer
)
from blockchain.ethereum_service import EthereumService


@api_view(['GET'])
@permission_classes([AllowAny])
def opportunity_list(request):
    """List all investment opportunities"""
    opportunities = InvestmentOpportunity.objects.filter(
        status='active',
        end_date__gte=timezone.now().date()
    )
    
    # Filter by minimum investment
    min_amount = request.query_params.get('min_amount')
    if min_amount:
        opportunities = opportunities.filter(minimum_investment__gte=Decimal(min_amount))
    
    # Filter by expected return
    min_return = request.query_params.get('min_return')
    if min_return:
        opportunities = opportunities.filter(expected_return_rate__gte=Decimal(min_return))
    
    opportunities = opportunities.order_by('-created_at')
    serializer = InvestmentOpportunitySerializer(opportunities, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def opportunity_detail(request, opportunity_id):
    """Get investment opportunity details"""
    opportunity = get_object_or_404(InvestmentOpportunity, id=opportunity_id)
    serializer = InvestmentOpportunitySerializer(opportunity)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_opportunity(request):
    """Create an investment opportunity (for farm owners)"""
    serializer = InvestmentOpportunitySerializer(data=request.data)
    
    if serializer.is_valid():
        # Verify user owns the farm
        farm_id = request.data.get('farm')
        # Use explicit filter to avoid potential attribute errors
        if not request.user.farms.filter(id=farm_id).exists(): # type: ignore
            return Response(
                {'error': 'You can only create opportunities for your own farms'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def invest(request, opportunity_id):
    """Invest in an opportunity"""
    opportunity = get_object_or_404(InvestmentOpportunity, id=opportunity_id)
    
    if opportunity.status != 'active':
        return Response(
            {'error': 'Investment opportunity is not active'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # FIX: Safety check for closed_at
    if opportunity.closed_at and opportunity.closed_at < timezone.now().date():
        return Response(
            {'error': 'Investment opportunity has ended'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    amount = request.data.get('amount')
    if not amount:
        return Response(
            {'error': 'Investment amount required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    amount = Decimal(amount)
    
    # Check minimum investment
    if amount < opportunity.minimum_investment_ac: # Using standard field name
        return Response(
            {'error': f'Minimum investment is {opportunity.minimum_investment_ac}'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Check if funding target exceeded
    current_funding = opportunity.current_amount_ac + amount
    if current_funding > opportunity.target_amount_ac:
        return Response(
            {'error': 'Investment would exceed funding goal'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Check user's wallet balance
    # FIX: Handle potential None balance
    eth_service = EthereumService()
    if hasattr(request.user, 'wallet'):
        wallet_addr = request.user.wallet.public_key # type: ignore
        balance = eth_service.get_token_balance(wallet_addr) or 0.0
        
        if float(balance) < float(amount):
            return Response(
                {'error': 'Insufficient wallet balance'},
                status=status.HTTP_400_BAD_REQUEST
            )
    else:
        return Response({'error': 'No wallet found'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Create investment
    investment = FarmInvestment.objects.create(
        investor=request.user,
        opportunity=opportunity,
        amount=amount,
        status='active'
    )
    
    # Update opportunity funding
    opportunity.current_amount_ac = current_funding
    if current_funding >= opportunity.target_amount_ac:
        opportunity.status = 'funded'
    opportunity.save()
    
    # Process blockchain transaction (simplified)
    # In production, this would lock tokens in smart contract
    
    serializer = FarmInvestmentSerializer(investment)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_investments(request):
    """Get user's investments"""
    investments = FarmInvestment.objects.filter(
        investor=request.user
    ).order_by('-created_at')
    
    # Filter by status
    investment_status = request.query_params.get('status')
    if investment_status:
        investments = investments.filter(status=investment_status)
    
    serializer = FarmInvestmentSerializer(investments, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def investment_detail(request, investment_id):
    """Get investment details"""
    investment = get_object_or_404(
        FarmInvestment,
        id=investment_id,
        investor=request.user
    )
    serializer = FarmInvestmentSerializer(investment)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def investment_returns(request, investment_id):
    """Get returns for an investment"""
    investment = get_object_or_404(
        FarmInvestment,
        id=investment_id,
        investor=request.user
    )
    
    # FIX: Use 'returns' (the related_name from InvestmentReturn model), NOT 'projected_returns'
    returns = investment.returns.order_by('-distribution_date') # type: ignore
    
    serializer = InvestmentReturnSerializer(returns, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def portfolio_summary(request):
    """Get investment portfolio summary"""
    investments = FarmInvestment.objects.filter(investor=request.user)
    
    total_invested = investments.aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0')
    
    # Using the reverse relationship 'returns' for calculation
    total_returns = InvestmentReturn.objects.filter(
        investment__investor=request.user
    ).aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0')
    
    active_investments = investments.filter(status='active').count()
    matured_investments = investments.filter(status='matured').count()
    
    summary = {
        'total_invested': float(total_invested),
        'total_returns': float(total_returns),
        'net_profit': float(total_returns - total_invested),
        'roi_percentage': float((total_returns / total_invested * 100) if total_invested > 0 else 0),
        'active_investments': active_investments,
        'matured_investments': matured_investments,
        'total_investments': investments.count()
    }
    
    return Response(summary)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def farm_investments(request, farm_id):
    """Get investments for a farm (for farm owners)"""
    # Verify user owns the farm
    # Use type ignore to suppress linter on reverse relationship
    if not request.user.farms.filter(id=farm_id).exists(): # type: ignore
        return Response(
            {'error': 'Unauthorized'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    opportunities = InvestmentOpportunity.objects.filter(farm_id=farm_id)
    investments = FarmInvestment.objects.filter(
        opportunity__in=opportunities
    ).order_by('-created_at')
    
    serializer = FarmInvestmentSerializer(investments, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def distribute_returns(request, opportunity_id):
    """Distribute returns to investors (for farm owners)"""
    opportunity = get_object_or_404(InvestmentOpportunity, id=opportunity_id)
    
    # Verify user owns the farm
    if opportunity.farm.owner != request.user:
        return Response(
            {'error': 'Unauthorized'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    return_amount = request.data.get('amount')
    if not return_amount:
        return Response(
            {'error': 'Return amount required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    return_amount = Decimal(return_amount)
    
    # Get active investments using related name 'investments'
    # Assuming related_name='investments' in FarmInvestment model for opportunity FK
    investments = FarmInvestment.objects.filter(opportunity=opportunity, status='active')
    
    if not investments.exists():
        return Response(
            {'error': 'No active investments found'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Calculate proportional returns
    total_invested = investments.aggregate(Sum('amount'))['amount__sum'] or Decimal('1')
    
    returns_created = []
    for investment in investments:
        proportion = investment.amount / total_invested
        investor_return = return_amount * proportion
        
        return_obj = InvestmentReturn.objects.create(
            investment=investment,
            amount=investor_return,
            distribution_date=timezone.now().date()
        )
        returns_created.append(return_obj)
    
    return Response({
        'message': f'Returns distributed to {len(returns_created)} investors',
        'total_amount': float(return_amount),
        'returns': InvestmentReturnSerializer(returns_created, many=True).data
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def investment_stats(request):
    """Get platform investment statistics"""
    stats = {
        'total_opportunities': InvestmentOpportunity.objects.filter(status='active').count(),
        'total_invested': float(FarmInvestment.objects.aggregate(
            total=Sum('amount')
        )['total'] or 0),
        'total_investors': FarmInvestment.objects.values('investor').distinct().count(),
        'avg_roi': float(InvestmentOpportunity.objects.aggregate(
            avg=Sum('expected_return_rate')
        )['avg'] or 0),
        'top_opportunities': InvestmentOpportunitySerializer(
            InvestmentOpportunity.objects.filter(status='active').order_by('-expected_return_rate')[:5],
            many=True
        ).data
    }
    
    return Response(stats)