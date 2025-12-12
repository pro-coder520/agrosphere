"""
AgroMentor 360 - Investments URL Configuration
"""

from django.urls import path
from . import views

app_name = 'investments'

urlpatterns = [
    # Investment Opportunities
    path('opportunities/', views.opportunity_list, name='opportunity-list'),
    path('opportunities/<uuid:opportunity_id>/', views.opportunity_detail, name='opportunity-detail'),
    path('opportunities/create/', views.create_opportunity, name='create-opportunity'),
    path('opportunities/<uuid:opportunity_id>/invest/', views.invest, name='invest'),
    path('opportunities/<uuid:opportunity_id>/returns/', views.distribute_returns, name='distribute-returns'),
    
    # User Investments
    path('my-investments/', views.my_investments, name='my-investments'),
    path('my-investments/<uuid:investment_id>/', views.investment_detail, name='investment-detail'),
    path('my-investments/<uuid:investment_id>/returns/', views.investment_returns, name='investment-returns'),
    
    # Portfolio
    path('portfolio/', views.portfolio_summary, name='portfolio-summary'),
    
    # Farm Investments (for farm owners)
    path('farms/<uuid:farm_id>/investments/', views.farm_investments, name='farm-investments'),
    
    # Statistics
    path('stats/', views.investment_stats, name='investment-stats'),
]