# Finance AI Companion

Finance AI Companion is an experimental AI-powered system designed to help users better understand and manage their personal finances through natural language interaction.

The idea behind the project is to simulate a **financial assistant** that can:
- Track user income and expenses.
- Answer questions like:
  - *"Can I afford this purchase?"*
  - *"What happens if I spend more this week?"*
- Provide explainable recommendations based on simple, transparent rules.
- Adapt over time to the user’s behavior.

The goal is not to replace real financial advisors, but to explore how AI can support everyday financial decision-making in a clear and human-friendly way.

---

## Current Project Status

At its current stage, the project includes:

- A core **finance engine** that handles:
  - Budget calculations.
  - Remaining balance.
  - Simple affordability checks.
- A **state system** that stores user data in JSON:
  - Income.
  - Expenses.
  - Daily spending.
- An **intent router** that classifies user input:
  - Purchase questions.
  - Logging expenses.
  - General financial queries.
- Basic **storage layer** for persisting financial state.
- Initial **test cases** for the finance logic.

The project is still under active development and is mainly focused on:
- Proving the concept.
- Validating the system design.
- Building a clean and extensible architecture.

---

## Project Structure (Current)

FINANCE-AI-COMPANION/
├── data/
│ └── state.json
├── tests/
│ └── test_finance_engine.py
├── app.py
├── finance_engine.py
├── intent_router.py
├── storage.py
├── schemas.py
├── demo.py


---


## Direction

The system is gradually evolving towards:
- More interactive user experience.
- Better explanation of decisions.
- Smarter budget adaptation.
- Clear separation between logic, storage, and interface.

This README represents the **current state of progress**, not the final product.
The focus is still on experimentation, learning, and refining the core idea.
