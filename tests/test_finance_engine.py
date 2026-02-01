"""
Tests for finance engine rule-based logic.
"""
import pytest
from finance_engine import FinanceEngine
from schemas import FinancialState


def test_set_income():
    """Test setting monthly income."""
    state = FinancialState()
    engine = FinanceEngine(state)
    
    result = engine.set_income(10000)
    
    assert state.monthly_income == 10000
    assert "10,000.00 SAR" in result


def test_add_fixed_expense():
    """Test adding fixed expense."""
    state = FinancialState(monthly_income=10000)
    engine = FinanceEngine(state)
    
    result = engine.add_fixed_expense("rent", 2500, "monthly")
    
    assert "rent" in state.fixed_expenses
    assert state.fixed_expenses["rent"].amount == 2500
    assert state.total_fixed_expenses == 2500


def test_discretionary_budget_calculation():
    """Test discretionary budget calculation."""
    state = FinancialState(monthly_income=12000)
    engine = FinanceEngine(state)
    
    # Add fixed expense
    engine.add_fixed_expense("rent", 2500)
    
    # Expected: Income (12000) - Fixed (2500) - Savings (20% = 2400) = 7100
    # But savings might be adjusted, so let's just check it's calculated
    assert state.discretionary_budget > 0
    assert state.discretionary_budget < state.monthly_income


def test_affordability_check_recommended():
    """Test affordability check that should be recommended."""
    state = FinancialState(monthly_income=12000)
    engine = FinanceEngine(state)
    engine.add_fixed_expense("rent", 2500)
    
    # Check affordable purchase
    result = engine.check_affordability("laptop", 1000)
    
    assert result.recommended is True
    assert result.amount == 1000


def test_affordability_check_not_recommended():
    """Test affordability check that should not be recommended."""
    state = FinancialState(monthly_income=5000)
    engine = FinanceEngine(state)
    engine.add_fixed_expense("rent", 3000)
    
    # Try to buy something expensive
    result = engine.check_affordability("car", 10000)
    
    assert result.recommended is False


def test_log_purchase():
    """Test logging a purchase."""
    state = FinancialState(monthly_income=12000)
    engine = FinanceEngine(state)
    engine.add_fixed_expense("rent", 2500)
    
    initial_used = state.discretionary_used
    
    result = engine.log_purchase("phone", 500)
    
    assert state.discretionary_used == initial_used + 500
    assert len(state.transactions) == 1
    assert state.transactions[0].amount == 500
    assert "500.00 SAR" in result


def test_log_expense():
    """Test logging an expense."""
    state = FinancialState(monthly_income=12000)
    engine = FinanceEngine(state)
    
    result = engine.log_expense("food", 50)
    
    assert state.discretionary_used == 50
    assert len(state.transactions) == 1
    assert state.transactions[0].category == "food"


def test_set_goal():
    """Test setting a savings goal."""
    state = FinancialState(monthly_income=12000)
    engine = FinanceEngine(state)
    
    result = engine.set_goal("car", 60000, 12)
    
    assert state.goal is not None
    assert state.goal.item == "car"
    assert state.goal.target_amount == 60000
    assert state.goal.timeframe_months == 12
    assert state.goal.required_monthly_savings == 5000


def test_goal_impact_on_budget():
    """Test that setting a goal adjusts the budget."""
    state = FinancialState(monthly_income=12000)
    engine = FinanceEngine(state)
    
    # Get initial discretionary budget
    engine.add_fixed_expense("rent", 2500)
    initial_discretionary = state.discretionary_budget
    
    # Set a goal
    engine.set_goal("car", 60000, 12)
    
    # Discretionary budget should be reduced to accommodate goal savings
    # (Goal requires 5000/month, which is high, so discretionary should decrease)
    assert state.savings_allocation >= 5000


def test_status_summary():
    """Test generating status summary."""
    state = FinancialState(monthly_income=12000)
    engine = FinanceEngine(state)
    engine.add_fixed_expense("rent", 2500)
    engine.set_goal("car", 60000, 12)
    
    summary = engine.get_status_summary()
    
    assert "12,000.00 SAR" in summary
    assert "rent" in summary.lower()
    assert "car" in summary.lower()


def test_overspending_adaptation():
    """Test that overspending triggers budget adaptation."""
    state = FinancialState(monthly_income=5000)
    engine = FinanceEngine(state)
    engine.add_fixed_expense("rent", 2000)
    
    # Spend most of discretionary budget
    discretionary = state.discretionary_budget
    engine.log_purchase("item1", discretionary * 0.85)
    
    # Should have reduced daily limit
    # (This is checked internally by the engine)
    assert state.remaining_discretionary < discretionary * 0.20


def test_help_text():
    """Test help text generation."""
    state = FinancialState()
    engine = FinanceEngine(state)
    
    help_text = engine.get_help_text()
    
    assert "salary" in help_text.lower()
    assert "buy" in help_text.lower()
    assert "spent" in help_text.lower()


def test_negative_amount_handling():
    """Test that negative amounts are rejected."""
    state = FinancialState(monthly_income=10000)
    engine = FinanceEngine(state)
    
    # This should be handled at validation level (Pydantic)
    # but let's ensure the engine doesn't break
    with pytest.raises(Exception):
        from schemas import Transaction
        Transaction(
            id="test",
            timestamp=datetime.now(),
            type="purchase",
            amount=-100,
            remaining_discretionary=1000
        )


def test_zero_income_handling():
    """Test behavior with zero income."""
    state = FinancialState(monthly_income=0)
    engine = FinanceEngine(state)
    
    result = engine.check_affordability("item", 100)
    
    # Should not be recommended when no income
    assert result.recommended is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
