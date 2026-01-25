"""
Finance Engine: Rule-based budget management and decision making.
All logic is deterministic and explainable - NO ML/AI decisions.
"""
import uuid
from datetime import datetime
from typing import Optional
from schemas import (
    FinancialState, Transaction, FixedExpense, SavingsGoal,
    IntentSchema, AffordabilityResponse
)


class FinanceEngine:
    """Rule-based financial decision engine."""

    def __init__(self, state: FinancialState):
        """Initialize engine with financial state."""
        self.state = state

    def set_income(self, amount: float) -> str:
        """Set monthly income and recalculate budgets."""
        self.state.monthly_income = amount
        self._recalculate_budgets()
        return f"✅ Monthly income set to {amount:,.2f} SAR"

    def add_fixed_expense(self, name: str, amount: float, 
                          frequency: str = "monthly") -> str:
        """Add a fixed expense (rent, bills, etc.)."""
        expense = FixedExpense(name=name, amount=amount, frequency=frequency)
        self.state.fixed_expenses[name] = expense
        self._recalculate_budgets()
        return f"✅ Fixed expense '{name}' set to {amount:,.2f} SAR/{frequency}"

    def set_goal(self, item: str, target_amount: float, 
                 timeframe_months: int) -> str:
        """Set a savings goal and adjust budgets."""
        goal = SavingsGoal(
            item=item,
            target_amount=target_amount,
            timeframe_months=timeframe_months,
            current_savings=self.state.current_savings
        )
        self.state.goal = goal
        self._recalculate_budgets()
        
        response = f"🎯 Goal set: {item} for {target_amount:,.2f} SAR "
        response += f"(target: {timeframe_months} month{'s' if timeframe_months > 1 else ''})\n"
        response += f"💡 Adjusting budgets to help you reach your goal...\n"
        response += f"   • Required monthly savings: {goal.required_monthly_savings:,.2f} SAR\n"
        response += f"   • New daily discretionary limit: {self.state.daily_limit:,.2f} SAR"
        
        return response

    def check_affordability(self, item: str, amount: float) -> AffordabilityResponse:
        """
        Check if purchase is affordable using rule-based logic.
        Returns detailed recommendation with explanation.
        """
        # Rule 1: Calculate remaining discretionary budget
        remaining = self.state.remaining_discretionary
        
        # Rule 2: Calculate usage percentage
        if amount > 0:
            usage_pct = (amount / self.state.discretionary_budget) * 100
        else:
            usage_pct = 0.0
        
        # Rule 3: Check if affordable
        recommended = amount <= remaining
        
        # Rule 4: Calculate goal impact
        goal_impact = None
        if self.state.goal:
            goal = self.state.goal
            required_monthly = goal.required_monthly_savings
            
            if recommended:
                # Calculate how much will be left for savings
                remaining_after = remaining - amount
                can_save = min(remaining_after, required_monthly)
                
                if can_save >= required_monthly:
                    goal_impact = f"✅ On track (saves {required_monthly:,.2f}/month)"
                else:
                    # Calculate delay in days
                    shortfall = required_monthly - can_save
                    days_delay = (shortfall / required_monthly) * 30
                    goal_impact = f"⚠️ May delay goal by ~{int(days_delay)} days"
            else:
                goal_impact = "❌ Would compromise your goal significantly"
        
        # Rule 5: Build explanation
        explanation = self._build_explanation(
            recommended, amount, remaining, usage_pct, goal_impact
        )
        
        # Rule 6: Check for warnings
        warning = None
        if usage_pct > 50 and recommended:
            warning = "⚠️ This purchase uses >50% of your discretionary budget"
        elif not recommended:
            warning = "❌ Exceeds available discretionary budget"
        
        return AffordabilityResponse(
            recommended=recommended,
            item=item,
            amount=amount,
            remaining_discretionary=remaining - amount if recommended else remaining,
            usage_percentage=usage_pct,
            goal_impact=goal_impact,
            daily_limit=self.state.daily_limit,
            explanation=explanation,
            warning=warning
        )

    def log_purchase(self, item: str, amount: float, 
                     category: Optional[str] = None) -> str:
        """Log a purchase and update state."""
        # Deduct from discretionary budget
        self.state.discretionary_used += amount
        
        # Create transaction record
        transaction = Transaction(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            type="purchase",
            item=item,
            amount=amount,
            category=category,
            remaining_discretionary=self.state.remaining_discretionary
        )
        self.state.transactions.append(transaction)
        
        # Check if overspending
        adaptation_msg = self._check_and_adapt_spending()
        
        response = f"✅ Purchase logged: {item} for {amount:,.2f} SAR\n"
        response += f"   • Remaining discretionary: {self.state.remaining_discretionary:,.2f} SAR\n"
        
        if self.state.goal:
            goal = self.state.goal
            if self.state.remaining_discretionary >= goal.required_monthly_savings:
                response += f"   • Still on track for your goal!\n"
            else:
                response += f"   • ⚠️ May impact your savings goal\n"
        
        if adaptation_msg:
            response += f"\n{adaptation_msg}"
        
        return response

    def log_expense(self, category: str, amount: float) -> str:
        """Log a general expense."""
        self.state.discretionary_used += amount
        
        transaction = Transaction(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            type="expense",
            category=category,
            amount=amount,
            remaining_discretionary=self.state.remaining_discretionary
        )
        self.state.transactions.append(transaction)
        
        adaptation_msg = self._check_and_adapt_spending()
        
        response = f"✅ Expense logged: {category} for {amount:,.2f} SAR\n"
        response += f"   • Remaining discretionary: {self.state.remaining_discretionary:,.2f} SAR"
        
        if adaptation_msg:
            response += f"\n\n{adaptation_msg}"
        
        return response

    def get_status_summary(self) -> str:
        """Generate a comprehensive budget status summary."""
        summary = "📊 **Budget Summary**\n\n"
        
        # Income
        summary += f"💰 **Income:** {self.state.monthly_income:,.2f} SAR\n\n"
        
        # Fixed expenses
        if self.state.fixed_expenses:
            summary += f"🏠 **Fixed Expenses:** {self.state.total_fixed_expenses:,.2f} SAR\n"
            for name, exp in self.state.fixed_expenses.items():
                summary += f"   • {name}: {exp.amount:,.2f} SAR\n"
            summary += "\n"
        
        # Discretionary budget
        summary += f"💳 **Discretionary Budget**\n"
        summary += f"   • Allocated: {self.state.discretionary_budget:,.2f} SAR\n"
        summary += f"   • Used: {self.state.discretionary_used:,.2f} SAR "
        summary += f"({self.state.discretionary_usage_percentage:.1f}%)\n"
        summary += f"   • Remaining: {self.state.remaining_discretionary:,.2f} SAR\n"
        summary += f"   • Daily limit: {self.state.daily_limit:,.2f} SAR\n\n"
        
        # Savings
        summary += f"💎 **Savings:** {self.state.current_savings:,.2f} SAR\n"
        if self.state.savings_allocation > 0:
            summary += f"   • Monthly allocation: {self.state.savings_allocation:,.2f} SAR\n"
        
        # Goal
        if self.state.goal:
            goal = self.state.goal
            summary += f"\n🎯 **Goal:** {goal.item}\n"
            summary += f"   • Target: {goal.target_amount:,.2f} SAR\n"
            summary += f"   • Progress: {goal.current_savings:,.2f} SAR "
            summary += f"({goal.progress_percentage:.1f}%)\n"
            summary += f"   • Required monthly: {goal.required_monthly_savings:,.2f} SAR\n"
            summary += f"   • Timeframe: {goal.timeframe_months} month(s)\n"
        
        # Recent transactions
        if self.state.transactions:
            summary += f"\n📝 **Recent Transactions** ({len(self.state.transactions)} total):\n"
            for trans in self.state.transactions[-5:]:  # Last 5
                summary += f"   • {trans.timestamp.strftime('%Y-%m-%d %H:%M')}: "
                summary += f"{trans.item or trans.category or trans.type} - "
                summary += f"{trans.amount:,.2f} SAR\n"
        
        return summary

    def _recalculate_budgets(self):
        """
        Recalculate all budgets based on income, expenses, and goals.
        This is the core rule-based allocation logic.
        """
        if self.state.monthly_income == 0:
            return
        
        # Step 1: Calculate total fixed expenses
        total_fixed = self.state.total_fixed_expenses
        
        # Step 2: Calculate required savings for goal
        required_savings = 0
        if self.state.goal:
            required_savings = self.state.goal.required_monthly_savings
        
        # Step 3: Allocate to savings (20% minimum or goal requirement, whichever is higher)
        min_savings = self.state.monthly_income * 0.20
        self.state.savings_allocation = max(min_savings, required_savings)
        
        # Step 4: Calculate discretionary budget
        # Discretionary = Income - Fixed - Savings
        self.state.discretionary_budget = (
            self.state.monthly_income - total_fixed - self.state.savings_allocation
        )
        
        # Ensure non-negative
        if self.state.discretionary_budget < 0:
            # If negative, reduce savings allocation
            self.state.savings_allocation = max(0, self.state.monthly_income - total_fixed)
            self.state.discretionary_budget = 0
        
        # Step 5: Calculate daily limit (assuming 30 days per month)
        if self.state.discretionary_budget > 0:
            self.state.daily_limit = self.state.discretionary_budget / 30
        else:
            self.state.daily_limit = 0

    def _check_and_adapt_spending(self) -> Optional[str]:
        """
        Check spending patterns and adapt budgets accordingly.
        Returns adaptation message if changes were made.
        """
        # Rule: If discretionary budget is exhausted
        if self.state.remaining_discretionary <= 0:
            msg = "⚠️ **Budget Alert:** Discretionary budget exhausted!\n"
            msg += "   • Consider postponing non-essential purchases\n"
            msg += "   • Your daily limit has been adjusted to 0 for the rest of the month"
            self.state.daily_limit = 0
            return msg
        
        # Rule: If >80% of budget used, reduce daily limit
        usage_pct = self.state.discretionary_usage_percentage
        if usage_pct > 80:
            # Reduce daily limit to stretch remaining budget
            days_left = 30  # Simplified: assume current day is irrelevant
            new_daily_limit = self.state.remaining_discretionary / days_left
            
            if new_daily_limit < self.state.daily_limit:
                self.state.daily_limit = new_daily_limit
                msg = "💡 **Budget Adaptation:** High spending detected\n"
                msg += f"   • Daily limit reduced to {new_daily_limit:,.2f} SAR\n"
                msg += f"   • This helps stretch your remaining budget"
                return msg
        
        # Rule: If <50% used and past mid-month, can reallocate surplus
        # (Simplified: we don't track actual days, so skip this for now)
        
        return None

    def _build_explanation(self, recommended: bool, amount: float, 
                          remaining: float, usage_pct: float,
                          goal_impact: Optional[str]) -> str:
        """Build detailed explanation for affordability decision."""
        if recommended:
            explanation = f"✅ **RECOMMENDED**\n"
            explanation += f"   • Remaining after purchase: {remaining - amount:,.2f} SAR\n"
            explanation += f"   • Uses {usage_pct:.1f}% of discretionary budget\n"
            if goal_impact:
                explanation += f"   • Goal impact: {goal_impact}\n"
            explanation += f"   • Suggested daily limit: {self.state.daily_limit:,.2f} SAR"
        else:
            explanation = f"❌ **NOT RECOMMENDED**\n"
            explanation += f"   • Amount exceeds remaining budget by {amount - remaining:,.2f} SAR\n"
            explanation += f"   • Would use {usage_pct:.1f}% of total discretionary budget\n"
            if goal_impact:
                explanation += f"   • Goal impact: {goal_impact}\n"
            explanation += f"   • Consider waiting or reducing the amount"
        
        return explanation

    def reset_monthly(self):
        """Reset monthly counters (called at start of new month)."""
        # Move remaining discretionary to savings
        surplus = self.state.remaining_discretionary
        if surplus > 0:
            self.state.current_savings += surplus
            if self.state.goal:
                self.state.goal.current_savings += surplus
        
        # Add monthly savings allocation
        self.state.current_savings += self.state.savings_allocation
        if self.state.goal:
            self.state.goal.current_savings += self.state.savings_allocation
        
        # Reset discretionary spending
        self.state.discretionary_used = 0
        
        # Recalculate budgets
        self._recalculate_budgets()

    def get_help_text(self) -> str:
        """Return help text with available commands."""
        return """🤖 **Personal Finance AI Companion**

I can help you make smart spending decisions! Here's what you can ask:

**Setup:**
• "My salary is 12000"
• "Rent is 2500 monthly"
• "I want to save 50000 for a car in 6 months"

**Daily Use:**
• "Can I buy a laptop for 5000?" - Check affordability
• "I bought a fridge for 2000" - Log purchase
• "Spent 40 on food" - Log expense
• "Summary" or "How much left?" - View budget status

**Tips:**
• I use rule-based logic - all decisions are explainable
• Set a goal to get personalized budget recommendations
• I'll adapt your daily limits based on spending patterns
• All amounts are in SAR (Saudi Riyal)

Try asking me something! 😊"""
