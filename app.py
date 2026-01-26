"""
Streamlit multi-page app for Personal Finance AI Companion.
Pages: Profile Setup, Chat Assistant, Dashboard
"""
import os
import streamlit as st
from dotenv import load_dotenv
from intent_router import IntentRouter
from finance_engine import FinanceEngine
from storage import Storage

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="Finance AI Companion",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if "storage" not in st.session_state:
    st.session_state.storage = Storage()

if "state" not in st.session_state:
    st.session_state.state = st.session_state.storage.load_state()

if "engine" not in st.session_state:
    st.session_state.engine = FinanceEngine(st.session_state.state)

if "router" not in st.session_state:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    st.session_state.router = IntentRouter(api_key)

if "messages" not in st.session_state:
    st.session_state.messages = []

if "pending_intent" not in st.session_state:
    st.session_state.pending_intent = None

if "confirm_reset" not in st.session_state:
    st.session_state.confirm_reset = False


# Helper functions
def save_state():
    """Save current state to storage."""
    st.session_state.storage.save_state(st.session_state.state)
    st.session_state.engine = FinanceEngine(st.session_state.state)


def process_chat_input(user_input: str) -> str:
    """Process chat input with improved intent handling."""
    engine = st.session_state.engine
    router = st.session_state.router
    
    # Handle pending intent (waiting for amount)
    if st.session_state.pending_intent:
        return handle_pending_intent(user_input)
    
    # Parse intent
    try:
        intent = router.parse(user_input)
    except Exception as e:
        return f"❌ Error: {str(e)}\n\nPlease try again or type 'help' for guidance."
    
    # Handle intents
    if intent.intent == "AFFORDABILITY_CHECK":
        if not intent.amount:
            st.session_state.pending_intent = {
                "intent": "AFFORDABILITY_CHECK",
                "item": intent.item or "item"
            }
            return f"💭 How much does the **{intent.item or 'item'}** cost?"
        
        item = intent.item or "item"
        result = engine.check_affordability(item, intent.amount)
        
        response = f"## {'✅ RECOMMENDED' if result.recommended else '❌ NOT RECOMMENDED'}\n\n"
        response += f"**{item.title()}** for **{intent.amount:,.0f} SAR**\n\n"
        
        if result.recommended:
            response += f"- ✅ Remaining after purchase: **{result.remaining_discretionary:,.0f} SAR**\n"
            response += f"- 📊 Uses **{result.usage_percentage:.1f}%** of your discretionary budget\n"
        else:
            response += f"- ❌ Exceeds budget by **{intent.amount - engine.state.remaining_discretionary:,.0f} SAR**\n"
            response += f"- 💡 You have **{engine.state.remaining_discretionary:,.0f} SAR** available\n"
        
        if result.goal_impact:
            response += f"- 🎯 Goal impact: {result.goal_impact}\n"
        
        response += f"- 📅 Daily limit: **{result.daily_limit:,.0f} SAR**\n"
        
        return response
    
    elif intent.intent == "LOG_PURCHASE":
        if not intent.amount:
            st.session_state.pending_intent = {
                "intent": "LOG_PURCHASE",
                "item": intent.item or "item"
            }
            return f"💭 How much did the **{intent.item or 'item'}** cost?"
        
        item = intent.item or "item"
        engine.log_purchase(item, intent.amount, intent.category)
        save_state()
        
        response = f"## ✅ Purchase Logged\n\n"
        response += f"**{item.title()}** for **{intent.amount:,.0f} SAR**\n\n"
        response += f"- 💳 Remaining budget: **{engine.state.remaining_discretionary:,.0f} SAR**\n"
        response += f"- 📊 Budget used: **{engine.state.discretionary_usage_percentage:.1f}%**\n"
        
        if engine.state.goal and engine.state.remaining_discretionary < engine.state.goal.required_monthly_savings:
            response += f"- ⚠️ This may impact your savings goal\n"
        
        return response
    
    elif intent.intent == "LOG_EXPENSE":
        if not intent.amount:
            category = intent.category or "expense"
            return f"💭 How much did you spend on **{category}**?"
        
        category = intent.category or "general"
        engine.log_expense(category, intent.amount)
        save_state()
        
        response = f"## ✅ Expense Logged\n\n"
        response += f"**{category.title()}** for **{intent.amount:,.0f} SAR**\n\n"
        response += f"- 💳 Remaining budget: **{engine.state.remaining_discretionary:,.0f} SAR**\n"
        
        return response
    
    elif intent.intent == "SHOW_STATUS":
        return engine.get_status_summary()
    
    elif intent.intent == "HELP":
        return get_chat_help_text()
    
    else:
        return ("💡 **I can help you with:**\n\n"
                "- **'Can I buy [item] for [amount]?'** - Check affordability\n"
                "- **'I bought [item] for [amount]'** - Log a purchase\n"
                "- **'I spent [amount] on [category]'** - Log an expense\n"
                "- **'summary'** or **'status'** - View your budget\n\n"
                "Try asking me one of these!")


def handle_pending_intent(user_input: str) -> str:
    """Handle pending intent when waiting for amount."""
    engine = st.session_state.engine
    pending = st.session_state.pending_intent
    
    # Extract amount
    import re
    numbers = re.findall(r'\d+(?:\.\d+)?', user_input)
    
    if not numbers:
        return "❌ Please provide a number. How much is it?"
    
    amount = float(numbers[0])
    intent_type = pending["intent"]
    item = pending["item"]
    
    # Clear pending intent
    st.session_state.pending_intent = None
    
    # Process based on intent type
    if intent_type == "AFFORDABILITY_CHECK":
        result = engine.check_affordability(item, amount)
        
        response = f"## {'✅ RECOMMENDED' if result.recommended else '❌ NOT RECOMMENDED'}\n\n"
        response += f"**{item.title()}** for **{amount:,.0f} SAR**\n\n"
        
        if result.recommended:
            response += f"- ✅ Remaining after purchase: **{result.remaining_discretionary:,.0f} SAR**\n"
            response += f"- 📊 Uses **{result.usage_percentage:.1f}%** of your discretionary budget\n"
        else:
            response += f"- ❌ Exceeds budget by **{amount - engine.state.remaining_discretionary:,.0f} SAR**\n"
        
        if result.goal_impact:
            response += f"- 🎯 Goal impact: {result.goal_impact}\n"
        
        return response
    
    elif intent_type == "LOG_PURCHASE":
        engine.log_purchase(item, amount)
        save_state()
        
        response = f"## ✅ Purchase Logged\n\n"
        response += f"**{item.title()}** for **{amount:,.0f} SAR**\n\n"
        response += f"- 💳 Remaining budget: **{engine.state.remaining_discretionary:,.0f} SAR**\n"
        
        return response
    
    return "Something went wrong. Please try again."


def get_chat_help_text() -> str:
    """Get help text for chat interface."""
    return """## 💬 Chat Commands

Ask me naturally! Here are some examples:

**Check Affordability:**
- "Can I buy a laptop for 5000?"
- "Should I get a new phone for 3000?"
- "Is 2000 too much for a fridge?"

**Log Purchases:**
- "I bought a TV for 3000"
- "Paid 500 for shoes"
- "Got a new watch for 1500"

**Log Expenses:**
- "Spent 200 on groceries"
- "Paid 50 for food today"
- "150 on entertainment"

**View Status:**
- "Show my budget"
- "How much do I have left?"
- "Summary"

💡 **Tip:** I understand casual language! Try "can i buy", "thinking of getting", "already bought", etc.
"""


def show_profile_page():
    """Display the profile setup page."""
    st.title("👤 Financial Profile Setup")
    st.write("Set up your financial information to get personalized budget recommendations.")
    
    state = st.session_state.state
    engine = st.session_state.engine
    
    # Income section
    st.header("💰 Monthly Income")
    income = st.number_input(
        "What is your monthly salary?",
        min_value=0.0,
        value=float(state.monthly_income),
        step=1000.0,
        format="%.0f",
        help="Enter your total monthly income in SAR"
    )
    
    st.divider()
    
    # Fixed expenses section
    st.header("🏠 Fixed Monthly Expenses")
    st.write("These are recurring expenses you pay every month (rent, bills, subscriptions, etc.)")
    
    # Display existing expenses
    expenses_to_remove = []
    for name, expense in state.fixed_expenses.items():
        col1, col2, col3 = st.columns([3, 2, 1])
        with col1:
            st.text(f"📌 {name.title()}")
        with col2:
            st.text(f"{expense.amount:,.0f} SAR")
        with col3:
            if st.button("❌", key=f"remove_{name}"):
                expenses_to_remove.append(name)
    
    # Remove expenses
    for name in expenses_to_remove:
        del state.fixed_expenses[name]
        save_state()
        st.rerun()
    
    # Add new expense
    with st.expander("➕ Add Fixed Expense", expanded=len(state.fixed_expenses) == 0):
        col1, col2 = st.columns([2, 1])
        with col1:
            expense_name = st.text_input("Expense Name", placeholder="e.g., Rent, Internet, Insurance")
        with col2:
            expense_amount = st.number_input("Amount (SAR)", min_value=0.0, step=100.0, format="%.0f")
        
        if st.button("Add Expense") and expense_name and expense_amount > 0:
            engine.add_fixed_expense(expense_name.lower(), expense_amount, "monthly")
            save_state()
            st.success(f"✅ Added {expense_name}")
            st.rerun()
    
    st.divider()
    
    # Savings goal section
    st.header("🎯 Savings Goal (Optional)")
    st.write("Set a goal to help manage your spending and savings better")
    
    if state.goal:
        st.success(f"🎯 Current Goal: **{state.goal.item}** - {state.goal.target_amount:,.0f} SAR in {state.goal.timeframe_months} months")
        if st.button("Remove Goal"):
            state.goal = None
            save_state()
            st.rerun()
    else:
        with st.expander("➕ Add Savings Goal", expanded=False):
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                goal_item = st.text_input("What are you saving for?", placeholder="e.g., Car, House, Vacation")
            with col2:
                goal_amount = st.number_input("Target Amount (SAR)", min_value=0.0, step=1000.0, format="%.0f")
            with col3:
                goal_months = st.number_input("Months", min_value=1, max_value=120, value=12)
            
            if st.button("Set Goal") and goal_item and goal_amount > 0:
                engine.set_goal(goal_item, goal_amount, goal_months)
                save_state()
                st.success(f"✅ Goal set!")
                st.rerun()
    
    st.divider()
    
    # Save button
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("💾 Save Profile", use_container_width=True, type="primary"):
            if income != state.monthly_income:
                engine.set_income(income)
            save_state()
            st.success("✅ Profile saved successfully!")
            st.balloons()
    
    # Show budget preview
    if state.monthly_income > 0:
        st.divider()
        st.header("📊 Budget Preview")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "💰 Monthly Income",
                f"{state.monthly_income:,.0f} SAR"
            )
        
        with col2:
            st.metric(
                "🏠 Fixed Expenses",
                f"{state.total_fixed_expenses:,.0f} SAR"
            )
        
        with col3:
            st.metric(
                "💳 Discretionary",
                f"{state.discretionary_budget:,.0f} SAR"
            )
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric(
                "💎 Monthly Savings",
                f"{state.savings_allocation:,.0f} SAR"
            )
        
        with col2:
            st.metric(
                "📅 Daily Limit",
                f"{state.daily_limit:,.0f} SAR"
            )


def show_chat_page():
    """Display the chat assistant page."""
    st.title("💬 Finance Chat Assistant")
    
    # Check if profile is set up
    if st.session_state.state.monthly_income == 0:
        st.warning("⚠️ Please set up your profile first!")
        if st.button("Go to Profile Setup"):
            st.rerun()
        return
    
    st.write("Ask me about purchases, expenses, or your budget!")
    
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Ask me anything... (e.g., 'Can I buy a laptop for 5000?')"):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Process and add assistant response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = process_chat_input(prompt)
                st.markdown(response)
        
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.rerun()
    
    # Help button
    if len(st.session_state.messages) == 0:
        with st.chat_message("assistant"):
            st.markdown(get_chat_help_text())
    
    # Quick actions
    st.divider()
    st.subheader("⚡ Quick Actions")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📊 Show Budget Summary", use_container_width=True):
            summary = st.session_state.engine.get_status_summary()
            st.session_state.messages.append({"role": "user", "content": "summary"})
            st.session_state.messages.append({"role": "assistant", "content": summary})
            st.rerun()
    
    with col2:
        if st.button("❓ Help", use_container_width=True):
            help_text = get_chat_help_text()
            st.session_state.messages.append({"role": "user", "content": "help"})
            st.session_state.messages.append({"role": "assistant", "content": help_text})
            st.rerun()
    
    with col3:
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.messages = []
            st.session_state.pending_intent = None
            st.rerun()


def show_dashboard_page():
    """Display the dashboard page."""
    st.title("📊 Financial Dashboard")
    
    state = st.session_state.state
    
    # Check if profile is set up
    if state.monthly_income == 0:
        st.warning("⚠️ Please set up your profile first!")
        if st.button("Go to Profile Setup"):
            st.rerun()
        return
    
    # Key metrics
    st.header("📈 Key Metrics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "💰 Monthly Income",
            f"{state.monthly_income:,.0f} SAR"
        )
    
    with col2:
        st.metric(
            "💳 Remaining Budget",
            f"{state.remaining_discretionary:,.0f} SAR"
        )
    
    with col3:
        st.metric(
            "📊 Budget Used",
            f"{state.discretionary_usage_percentage:.1f}%"
        )
    
    with col4:
        st.metric(
            "📅 Daily Limit",
            f"{state.daily_limit:,.0f} SAR"
        )
    
    st.divider()
    
    # Goal tracking
    if state.goal:
        st.header("🎯 Goal Progress")
        
        goal = state.goal
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "Target",
                f"{goal.target_amount:,.0f} SAR"
            )
        
        with col2:
            st.metric(
                "Saved",
                f"{goal.current_savings:,.0f} SAR"
            )
        
        with col3:
            st.metric(
                "Remaining",
                f"{goal.target_amount - goal.current_savings:,.0f} SAR"
            )
        
        # Progress bar
        progress = min(goal.progress_percentage / 100, 1.0)
        st.progress(progress)
        st.caption(f"{goal.item.title()}: {goal.progress_percentage:.1f}% complete")
        
        # Monthly requirement
        st.info(f"📅 You need to save **{goal.required_monthly_savings:,.0f} SAR** per month to reach your goal in {goal.timeframe_months} months")
        
        st.divider()
    
    # Recent transactions
    st.header("📝 Recent Transactions")
    
    if state.transactions:
        # Show last 10 transactions
        recent_transactions = state.transactions[-10:]
        recent_transactions.reverse()  # Most recent first
        
        for trans in recent_transactions:
            col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
            
            with col1:
                st.text(trans.timestamp.strftime("%Y-%m-%d %H:%M"))
            
            with col2:
                item_text = trans.item or trans.category or trans.type
                st.text(f"📌 {item_text.title()}")
            
            with col3:
                st.text(f"{trans.amount:,.0f} SAR")
            
            with col4:
                # Type emoji
                emoji = {"purchase": "🛍️", "expense": "💸", "income": "💰"}.get(trans.type, "📝")
                st.text(emoji)
        
        # Export option
        if st.button("📥 Export Transactions"):
            export_path = st.session_state.storage.export_transactions()
            if export_path:
                st.success(f"✅ Exported to {export_path}")
    else:
        st.info("No transactions yet. Start using the chat to log purchases and expenses!")


# Sidebar navigation
with st.sidebar:
    st.title("💰 Finance AI")
    
    # Page navigation
    st.subheader("📑 Navigation")
    page = st.radio(
        "Go to:",
        ["👤 Profile Setup", "💬 Chat Assistant", "📊 Dashboard"],
        label_visibility="collapsed"
    )
    
    st.divider()
    
    # Mode indicator
    if st.session_state.router.use_llm:
        st.success("🤖 AI Mode: Active")
    else:
        st.warning("🔧 Offline Mode")
    
    st.divider()
    
    # Quick stats
    state = st.session_state.state
    
    if state.monthly_income > 0:
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Income", f"{state.monthly_income:,.0f}")
        with col2:
            st.metric("Remaining", f"{state.remaining_discretionary:,.0f}")
        
        # Progress bar for budget usage
        if state.discretionary_budget > 0:
            usage_pct = state.discretionary_usage_percentage / 100
            st.progress(usage_pct)
            st.caption(f"Budget used: {state.discretionary_usage_percentage:.1f}%")
    else:
        st.info("📝 Set up your profile to get started!")
    
    if state.goal:
        st.divider()
        st.subheader("🎯 Goal")
        progress = min(state.goal.progress_percentage / 100, 1.0)
        st.progress(progress)
        st.caption(f"{state.goal.item}: {state.goal.progress_percentage:.1f}%")
    
    st.divider()
    
    # Reset button
    if st.button("🔄 Reset All Data", use_container_width=True):
        if st.session_state.confirm_reset:
            st.session_state.storage.clear_state()
            st.session_state.state = st.session_state.storage.load_state()
            st.session_state.engine = FinanceEngine(st.session_state.state)
            st.session_state.messages = []
            st.session_state.confirm_reset = False
            st.success("✅ Data reset!")
            st.rerun()
        else:
            st.session_state.confirm_reset = True
            st.warning("Click again to confirm reset")
    
    st.caption("💡 Made with Streamlit & Claude")


# Main content based on selected page
if page == "👤 Profile Setup":
    show_profile_page()
elif page == "💬 Chat Assistant":
    show_chat_page()
else:  # Dashboard
    show_dashboard_page()
