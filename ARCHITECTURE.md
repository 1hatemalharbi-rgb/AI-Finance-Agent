# System Architecture

## Overview

The Personal Finance AI Companion is a **rule-based** system that uses LLM only for intent parsing, NOT for financial decisions. All budget calculations and recommendations are deterministic and explainable.

## Component Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Streamlit Chat UI (app.py)                │
│  - User interface                                             │
│  - Chat history management                                    │
│  - Session state handling                                     │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              Intent Router (intent_router.py)                 │
│  ┌──────────────────────┬──────────────────────────────┐     │
│  │   LLM Mode (Claude)  │  Offline Mode (Keywords)    │     │
│  │  - Natural language  │  - Pattern matching         │     │
│  │  - High accuracy     │  - No API required          │     │
│  └──────────────────────┴──────────────────────────────┘     │
│                                                               │
│  Output: Structured JSON (IntentSchema)                       │
│  {                                                            │
│    "intent": "AFFORDABILITY_CHECK",                           │
│    "item": "laptop",                                          │
│    "amount": 5000,                                            │
│    "confidence": 0.95                                         │
│  }                                                            │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│            Finance Engine (finance_engine.py)                 │
│  ┌───────────────────────────────────────────────────────┐   │
│  │           RULE-BASED DECISION LOGIC                   │   │
│  │  - No AI/ML for financial decisions                   │   │
│  │  - Deterministic calculations                         │   │
│  │  - Explainable recommendations                        │   │
│  └───────────────────────────────────────────────────────┘   │
│                                                               │
│  Core Rules:                                                  │
│  1. Discretionary = Income - Fixed - Savings                  │
│  2. Affordable if: Amount ≤ Remaining Discretionary           │
│  3. Goal savings = Target / Timeframe                         │
│  4. Adapt limits based on spending patterns                   │
│  5. Reallocate surplus to savings                             │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│               Financial State (schemas.py)                    │
│  - FinancialState: Complete user financial profile            │
│  - Transaction: Individual spending records                   │
│  - FixedExpense: Recurring expenses                           │
│  - SavingsGoal: Goal tracking                                 │
│  - Pydantic validation ensures data integrity                 │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                Storage (storage.py)                           │
│  - JSON-based persistence (data/state.json)                   │
│  - Load/save state                                            │
│  - Transaction export                                         │
│  - Backup functionality                                       │
└─────────────────────────────────────────────────────────────┘
```

## Data Flow

### 1. User Input Processing

```
User: "Can I buy a laptop for 5000?"
     ↓
[app.py] Captures input
     ↓
[intent_router.py] Parses to JSON
     ↓
{
  "intent": "AFFORDABILITY_CHECK",
  "item": "laptop",
  "amount": 5000
}
```

### 2. Rule-Based Decision

```
[finance_engine.py]
     ↓
Calculate:
  Remaining = Discretionary - Used
  = 8000 - 3000 = 5000 SAR
     ↓
Check: 5000 ≤ 5000? ✓ YES
     ↓
Recommendation: APPROVED
  - Uses 100% of remaining budget
  - Check goal impact
  - Update daily limit
```

### 3. Response Generation

```
[finance_engine.py] → AffordabilityResponse
     ↓
[app.py] Formats for display
     ↓
User sees:
  ✅ RECOMMENDED
  • Remaining: 0 SAR (100% used)
  • Goal impact: ⚠️ May delay by 5 days
  • Updated daily limit: 0 SAR
```

## Intent Types

### Setup Intents
- `SET_INCOME` - Configure monthly income
- `SET_FIXED_EXPENSE` - Add recurring expenses
- `SET_GOAL` - Define savings goal

### Action Intents
- `AFFORDABILITY_CHECK` - "Can I buy X?"
- `LOG_PURCHASE` - "I bought X"
- `LOG_EXPENSE` - "Spent X on Y"

### Query Intents
- `SHOW_STATUS` - View budget summary
- `HELP` - Get usage instructions

### Fallback
- `UNKNOWN` - Unrecognized input

## Budget Calculation Rules

### Monthly Budget Allocation

```
INCOME = User's monthly salary
     ↓
FIXED = Sum of all fixed expenses
     ↓
GOAL_SAVINGS = Required monthly savings for goal
MIN_SAVINGS = 20% of income (minimum)
SAVINGS = max(GOAL_SAVINGS, MIN_SAVINGS)
     ↓
DISCRETIONARY = INCOME - FIXED - SAVINGS
     ↓
DAILY_LIMIT = DISCRETIONARY / 30
```

### Affordability Check

```
REMAINING = DISCRETIONARY - USED
     ↓
If AMOUNT ≤ REMAINING:
  ✅ RECOMMENDED
  • Calculate usage %
  • Check goal impact
  • Update daily limit
Else:
  ❌ NOT RECOMMENDED
  • Show shortfall
  • Suggest alternatives
```

### Goal Impact Calculation

```
REQUIRED_MONTHLY = Goal Amount / Timeframe
     ↓
REMAINING_AFTER = REMAINING - PURCHASE_AMOUNT
     ↓
If REMAINING_AFTER ≥ REQUIRED_MONTHLY:
  ✅ "On track"
Else:
  SHORTFALL = REQUIRED_MONTHLY - REMAINING_AFTER
  DELAY_DAYS = (SHORTFALL / REQUIRED_MONTHLY) × 30
  ⚠️ "May delay goal by X days"
```

### Adaptive Budgeting

```
USAGE_PCT = (USED / DISCRETIONARY) × 100
     ↓
If USAGE_PCT > 80%:
  DAYS_LEFT = 30 - Current Day
  NEW_DAILY_LIMIT = REMAINING / DAYS_LEFT
  💡 "Daily limit reduced to stretch budget"
     ↓
If USAGE_PCT < 50% at month end:
  SURPLUS = REMAINING
  CURRENT_SAVINGS += SURPLUS
  💡 "Surplus moved to savings"
```

## State Persistence

### Data Model
```json
{
  "monthly_income": 12000,
  "fixed_expenses": {
    "rent": {"name": "rent", "amount": 2500, "frequency": "monthly"}
  },
  "discretionary_budget": 7100,
  "discretionary_used": 2000,
  "savings_allocation": 2400,
  "current_savings": 5000,
  "goal": {
    "item": "car",
    "target_amount": 50000,
    "timeframe_months": 6,
    "current_savings": 5000
  },
  "transactions": [
    {
      "id": "uuid",
      "timestamp": "2025-01-21T10:30:00",
      "type": "purchase",
      "item": "laptop",
      "amount": 2000,
      "remaining_discretionary": 5100
    }
  ],
  "daily_limit": 236.67
}
```

## LLM Usage Policy

### ✅ LLM IS USED FOR:
- Intent parsing (text → JSON)
- Understanding natural language variations
- Extracting entities (item names, amounts)

### ❌ LLM IS NEVER USED FOR:
- Budget calculations
- Affordability decisions
- Financial recommendations
- Numeric computations
- State updates

### Why This Separation?
1. **Explainability** - Rules are transparent and auditable
2. **Consistency** - Same input always gives same output
3. **Accuracy** - No hallucination risk in calculations
4. **Trust** - Users can verify the logic
5. **Debugging** - Easy to trace decision path

## Offline Mode

When no API key is provided:

```
[Keywords Detected]
"can i buy" → AFFORDABILITY_CHECK
"i bought" → LOG_PURCHASE
"spent" → LOG_EXPENSE
"salary" → SET_INCOME
"rent" → SET_FIXED_EXPENSE
"goal" → SET_GOAL
"summary" → SHOW_STATUS
```

### Trade-offs
- ✅ No API cost
- ✅ Works offline
- ✅ Instant response
- ❌ Less flexible parsing
- ❌ May miss intent variations
- ❌ Requires more specific phrasing

## Error Handling

### Input Validation
```
[Pydantic Schemas]
  ↓
Validate amounts > 0
Validate timeframes > 0
Validate intent types
  ↓
If invalid: Return clear error message
```

### Missing Information
```
User: "Can I buy a fridge?"
  ↓
Intent: AFFORDABILITY_CHECK
Amount: null
  ↓
[Store pending intent]
  ↓
Bot: "How much is the fridge?"
  ↓
User: "2000"
  ↓
[Complete pending intent]
  ↓
Process affordability check
```

### Edge Cases
- Zero income → Always not recommended
- Negative amounts → Validation error
- Empty input → UNKNOWN intent
- Greetings → Direct to HELP

## Testing Strategy

### Unit Tests
- `test_set_income()` - Income configuration
- `test_add_fixed_expense()` - Expense tracking
- `test_affordability_check_recommended()` - Approval logic
- `test_affordability_check_not_recommended()` - Rejection logic
- `test_log_purchase()` - Transaction logging
- `test_set_goal()` - Goal setting
- `test_goal_impact_on_budget()` - Budget adaptation

### Integration Tests
- Full conversation flows
- State persistence
- Intent routing (LLM + offline)

### Manual Testing
- Run `demo.py` for quick validation
- Use Streamlit UI for end-to-end testing

## Security & Privacy

- ✅ All data stored locally (data/state.json)
- ✅ No data sent to external services (except LLM for parsing)
- ✅ API key stored in .env (not committed)
- ✅ No authentication required (single-user system)

## Performance

- **Intent Parsing**: <1s (LLM) or <100ms (offline)
- **Rule Evaluation**: <10ms
- **State Persistence**: <50ms
- **Total Response Time**: <2s (LLM) or <200ms (offline)

## Scalability Considerations

Current: Single-user, monthly budget cycles
Future: Could extend to:
- Multi-user with user IDs
- Multiple budget periods
- Category-specific budgets
- Recurring transaction detection
- Predictive analytics (optional ML layer)

## Extension Points

### Adding New Intents
1. Add to `IntentSchema` in `schemas.py`
2. Update parser in `intent_router.py`
3. Add handler in `finance_engine.py`
4. Add UI logic in `app.py`

### Adding New Rules
1. Modify `_recalculate_budgets()` in `finance_engine.py`
2. Add validation in schemas
3. Update tests
4. Document in README

### Adding ML (Optional)
```
┌─────────────────────────────────────┐
│  Rule Engine (Always Active)        │
│  - Core decisions                    │
│  - Budget calculations               │
└─────────────┬───────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│  ML Layer (Optional Enhancement)     │
│  - Spending predictions              │
│  - Category recommendations          │
│  - Anomaly detection                 │
│  CLEARLY SEPARATED from core logic   │
└─────────────────────────────────────┘
```

---

**Key Principle**: Simple, explainable rules trump complex black-box models for financial decisions.
