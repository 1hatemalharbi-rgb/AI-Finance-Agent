"""
Storage module for persisting financial state to JSON.
"""
import json
import os
from pathlib import Path
from typing import Optional
from datetime import datetime
from schemas import FinancialState, Transaction, FixedExpense, SavingsGoal


class Storage:
    """Handle reading and writing financial state to JSON file."""

    def __init__(self, data_dir: str = "data"):
        """Initialize storage with data directory."""
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.state_file = self.data_dir / "state.json"

    def load_state(self) -> FinancialState:
        """Load financial state from JSON file."""
        if not self.state_file.exists():
            # Return empty state if file doesn't exist
            return FinancialState()

        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Convert nested dicts back to Pydantic models
            if 'fixed_expenses' in data:
                data['fixed_expenses'] = {
                    name: FixedExpense(**exp) 
                    for name, exp in data['fixed_expenses'].items()
                }
            
            if 'goal' in data and data['goal']:
                data['goal'] = SavingsGoal(**data['goal'])
            
            if 'transactions' in data:
                data['transactions'] = [
                    Transaction(**t) for t in data['transactions']
                ]
            
            # Convert datetime strings back to datetime objects
            if 'created_at' in data:
                data['created_at'] = datetime.fromisoformat(data['created_at'])
            if 'last_updated' in data:
                data['last_updated'] = datetime.fromisoformat(data['last_updated'])
            
            return FinancialState(**data)
        
        except Exception as e:
            print(f"Error loading state: {e}")
            # Return empty state if load fails
            return FinancialState()

    def save_state(self, state: FinancialState) -> bool:
        """Save financial state to JSON file."""
        try:
            # Update last_updated timestamp
            state.last_updated = datetime.now()
            
            # Convert to dict for JSON serialization
            data = state.model_dump(mode='json')
            
            # Ensure data directory exists
            self.data_dir.mkdir(exist_ok=True)
            
            # Write to file with pretty formatting
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
            
            return True
        
        except Exception as e:
            print(f"Error saving state: {e}")
            return False

    def backup_state(self) -> Optional[Path]:
        """Create a backup of the current state."""
        if not self.state_file.exists():
            return None
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = self.data_dir / f"state_backup_{timestamp}.json"
            
            with open(self.state_file, 'r', encoding='utf-8') as src:
                data = src.read()
            
            with open(backup_file, 'w', encoding='utf-8') as dst:
                dst.write(data)
            
            return backup_file
        
        except Exception as e:
            print(f"Error creating backup: {e}")
            return None

    def clear_state(self) -> bool:
        """Clear all state (delete the state file)."""
        try:
            if self.state_file.exists():
                # Create backup before clearing
                self.backup_state()
                self.state_file.unlink()
            return True
        
        except Exception as e:
            print(f"Error clearing state: {e}")
            return False

    def export_transactions(self, output_file: Optional[str] = None) -> Optional[Path]:
        """Export transactions to a separate JSON file."""
        state = self.load_state()
        
        if not state.transactions:
            return None
        
        try:
            if output_file is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_file = f"transactions_{timestamp}.json"
            
            output_path = self.data_dir / output_file
            
            transactions_data = [t.model_dump(mode='json') for t in state.transactions]
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(transactions_data, f, indent=2, default=str)
            
            return output_path
        
        except Exception as e:
            print(f"Error exporting transactions: {e}")
            return None
