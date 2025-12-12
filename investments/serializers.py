from rest_framework import serializers
from decimal import Decimal
from django.utils import timezone
from .models import FarmInvestment, InvestmentOpportunity, InvestmentReturn

# ----------------------------------------------------------------
# Return Serializer (Required for distribute_returns view)
# ----------------------------------------------------------------

class InvestmentReturnSerializer(serializers.ModelSerializer):
    """
    Serializer for returns distributed to investors
    """
    class Meta: #type:ignore
        model = InvestmentReturn
        fields = ['id', 'amount', 'distribution_date', 'created_at']


# ----------------------------------------------------------------
# Opportunity Serializers
# ----------------------------------------------------------------

class InvestmentOpportunitySerializer(serializers.ModelSerializer):
    """
    Serializer for listing and creating investment opportunities.
    Includes calculated fields for funding progress.
    """
    farm_name = serializers.CharField(source='farm.name', read_only=True)
    farm_location = serializers.CharField(source='farm.location_city', read_only=True)
    funding_progress = serializers.SerializerMethodField()
    is_open = serializers.SerializerMethodField()
    
    class Meta: #type:ignore
        model = InvestmentOpportunity
        fields = [
            'id', 'farm', 'farm_name', 'farm_location',
            'title', 'description', 'image',
            'minimum_investment', 'funding_goal', 'current_funding',
            'expected_return_rate', 'duration_months',
            'start_date', 'end_date', 'closed_at',
            'status', 'funding_progress', 'is_open',
            'created_at'
        ]
        read_only_fields = ['id', 'current_funding', 'status', 'closed_at', 'created_at']

    def get_funding_progress(self, obj):
        """Calculate percentage of funding goal reached"""
        if obj.funding_goal > 0:
            return round((obj.current_funding / obj.funding_goal) * 100, 2)
        return 0.0

    def get_is_open(self, obj):
        """Check if opportunity is currently accepting investments"""
        now = timezone.now().date()
        return (
            obj.status == 'active' and 
            obj.end_date >= now and 
            obj.current_funding < obj.funding_goal
        )

    def validate(self, attrs):
        """Ensure end date is after start date"""
        if 'start_date' in attrs and 'end_date' in attrs:
            if attrs['end_date'] <= attrs['start_date']:
                raise serializers.ValidationError("End date must be after start date.")
        return attrs


# ----------------------------------------------------------------
# Investment Serializers
# ----------------------------------------------------------------

class FarmInvestmentSerializer(serializers.ModelSerializer):
    """
    Serializer for user investments (FarmInvestment model).
    Used in 'my_investments' and 'invest' views.
    """
    opportunity_title = serializers.CharField(source='opportunity.title', read_only=True)
    opportunity_status = serializers.CharField(source='opportunity.status', read_only=True)
    expected_return_amount = serializers.SerializerMethodField()
    total_returns_received = serializers.SerializerMethodField()
    
    # Nested returns for detailed view
    returns = InvestmentReturnSerializer(many=True, read_only=True)

    class Meta: #type:ignore
        model = FarmInvestment
        fields = [
            'id', 'opportunity', 'opportunity_title', 'opportunity_status',
            'amount', 'status', 'created_at',
            'expected_return_amount', 'total_returns_received',
            'returns'
        ]
        read_only_fields = ['id', 'investor', 'status', 'created_at']

    def get_expected_return_amount(self, obj):
        """Calculate projected return based on opportunity rate"""
        rate = obj.opportunity.expected_return_rate
        return obj.amount * (1 + (rate / 100))

    def get_total_returns_received(self, obj):
        """Sum of all returns distributed to this investment"""
        return sum(ret.amount for ret in obj.returns.all())


class InvestmentSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for the generic Investment model.
    (If your project uses a separate base Investment model distinct from FarmInvestment)
    """
    class Meta: #type:ignore
        model = FarmInvestment # Mapping to FarmInvestment based on view usage
        fields = [
            'id', 'amount', 'status', 'created_at'
        ]