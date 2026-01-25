"""
Pydantic schemas for data validation and structure.
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal
from datetime import datetime


class IntentSchema(BaseModel):
    """Schema for parsed intents from LLM router."""
    intent: Literal[
        "AFFORDABILITY_CHECK",
        "LOG_PURCHASE",
        "LOG_EXPENSE",
        "SET_INCOME",
        "SET_FIXED_EXPENSE",
        "SET_VARIABLE_LIMITS",
        "SET_GOAL",
        "SHOW_STATUS",
        "HELP",
        "UNKNOWN"
    ]
    item: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = "SAR"
    category: Optional[str] = None
    fixed_expense_name: Optional[str] = None
    frequency: Optional[Literal["monthly", "weekly", "daily", "one_time"]] = None
    goal_item: Optional[str] = None
    goal_amount: Optional[float] = None
    goal_timeframe: Optional[str] = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    @field_validator('amount', 'goal_amount')
    @classmethod
    def validate_positive_amount(cls, v):
        """Ensure amounts are positive."""
        if v is not None and v < 0:
            raise ValueError("Amount must be positive")
        return v


class Transaction(BaseModel):
    """Individual transaction record."""
    id: str
    timestamp: datetime
    type: Literal["purchase", "expense", "income", "fixed_expense"]
    item: Optional[str] = None
    amount: float
    category: Optional[str] = None
    remaining_discretionary: float

    @field_validator('amount')
    @classmethod
    def validate_positive_amount(cls, v):
        """Ensure amounts are positive."""
        if v < 0:
            raise ValueError("Amount must be positive")
        return v


class FixedExpense(BaseModel):
    """Fixed monthly expense."""
    name: str
    amount: float
    frequency: Literal["monthly", "weekly", "daily"] = "monthly"

    @field_validator('amount')
    @classmethod
    def validate_positive_amount(cls, v):
        """Ensure amounts are positive."""
        if v < 0:
            raise ValueError("Amount must be positive")
        return v


class SavingsGoal(BaseModel):
    """Savings goal with target and timeframe."""
    item: str
    target_amount: float
    timeframe_months: int
    current_savings: float = 0.0
    created_at: datetime = Field(default_factory=datetime.now)

    @field_validator('target_amount', 'current_savings')
    @classmethod
    def validate_positive_amount(cls, v):
        """Ensure amounts are positive."""
        if v < 0:
            raise ValueError("Amount must be positive")
        return v

    @field_validator('timeframe_months')
    @classmethod
    def validate_timeframe(cls, v):
        """Ensure timeframe is positive."""
        if v <= 0:
            raise ValueError("Timeframe must be positive")
        return v

    @property
    def required_monthly_savings(self) -> float:
        """Calculate required monthly savings to reach goal."""
        return (self.target_amount - self.current_savings) / self.timeframe_months

    @property
    def progress_percentage(self) -> float:
        """Calculate progress towards goal."""
        if self.target_amount == 0:
            return 100.0
        return (self.current_savings / self.target_amount) * 100


class FinancialState(BaseModel):
    """Complete financial state of the user."""
    monthly_income: float = 0.0
    fixed_expenses: dict[str, FixedExpense] = Field(default_factory=dict)
    discretionary_budget: float = 0.0  # Available for non-essential spending
    discretionary_used: float = 0.0
    savings_allocation: float = 0.0  # Amount allocated to savings each month
    current_savings: float = 0.0
    goal: Optional[SavingsGoal] = None
    transactions: list[Transaction] = Field(default_factory=list)
    daily_limit: float = 0.0  # Calculated daily spending limit
    created_at: datetime = Field(default_factory=datetime.now)
    last_updated: datetime = Field(default_factory=datetime.now)

    @property
    def total_fixed_expenses(self) -> float:
        """Calculate total fixed expenses per month."""
        return sum(exp.amount for exp in self.fixed_expenses.values())

    @property
    def remaining_discretionary(self) -> float:
        """Calculate remaining discretionary budget."""
        return max(0, self.discretionary_budget - self.discretionary_used)

    @property
    def discretionary_usage_percentage(self) -> float:
        """Calculate percentage of discretionary budget used."""
        if self.discretionary_budget == 0:
            return 0.0
        return (self.discretionary_used / self.discretionary_budget) * 100


class AffordabilityResponse(BaseModel):
    """Response for affordability check."""
    recommended: bool
    item: str
    amount: float
    remaining_discretionary: float
    usage_percentage: float
    goal_impact: Optional[str] = None
    daily_limit: float
    explanation: str
    warning: Optional[str] = None
