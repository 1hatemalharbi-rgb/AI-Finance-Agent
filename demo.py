"""
Quick demo script to test the finance companion without Streamlit.
Run: python demo.py
"""
from finance_engine import FinanceEngine
from intent_router import IntentRouter
from storage import Storage
from schemas import FinancialState


def main():
    """Run a simple demo conversation."""
    print("=" * 60)
    print("Personal Finance AI Companion - Demo")
    print("=" * 60)
    print()
    
    # Initialize
    storage = Storage()
    state = storage.load_state()
    engine = FinanceEngine(state)
    router = IntentRouter()  # Will use fallback if no API key
    
    if router.use_llm:
        print("✓ Using LLM intent parsing")
    else:
        print("⚠ Using offline keyword matching (no API key)")
    print()
    
    # Demo conversation
    test_inputs = [
        "My salary is 12000",
        "Rent is 2500 monthly",
        "I want to save 50000 for a car in 6 months",
        "Can I buy a fridge for 2000?",
        "I bought it",
        "Spent 40 on food",
        "Summary"
    ]
    
    for user_input in test_inputs:
        print(f"User: {user_input}")
        print()
        
        # Parse intent
        intent = router.parse(user_input)
        print(f"[Intent: {intent.intent}, Amount: {intent.amount}]")
        
        # Process
        response = process_intent(engine, intent)
        print(f"Bot: {response}")
        print()
        print("-" * 60)
        print()
        
        # Save state after each interaction
        storage.save_state(state)
    
    print("Demo complete! Check data/state.json for saved state.")


def process_intent(engine, intent):
    """Process intent and return response."""
    if intent.intent == "SET_INCOME":
        return engine.set_income(intent.amount)
    
    elif intent.intent == "SET_FIXED_EXPENSE":
        name = intent.fixed_expense_name or "expense"
        return engine.add_fixed_expense(name, intent.amount, "monthly")
    
    elif intent.intent == "SET_GOAL":
        # Parse timeframe
        timeframe_months = 6  # Default from demo
        if intent.goal_timeframe:
            import re
            numbers = re.findall(r'\d+', intent.goal_timeframe)
            if numbers:
                timeframe_months = int(numbers[0])
        
        return engine.set_goal(intent.goal_item, intent.goal_amount, timeframe_months)
    
    elif intent.intent == "AFFORDABILITY_CHECK":
        result = engine.check_affordability(intent.item, intent.amount)
        return result.explanation
    
    elif intent.intent == "LOG_PURCHASE":
        return engine.log_purchase(intent.item or "item", intent.amount or 2000)
    
    elif intent.intent == "LOG_EXPENSE":
        return engine.log_expense(intent.category or "food", intent.amount)
    
    elif intent.intent == "SHOW_STATUS":
        return engine.get_status_summary()
    
    else:
        return "Intent not fully implemented in demo"


if __name__ == "__main__":
    main()
