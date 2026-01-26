"""
Intent router: converts natural language to structured JSON commands.
Uses LLM when available, falls back to keyword matching otherwise.
"""
import os
import re
import json
from typing import Optional
from anthropic import Anthropic
from schemas import IntentSchema


class IntentRouter:
    """Routes user input to structured intents using LLM or fallback."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize router with optional API key."""
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.client = None
        self.use_llm = False
        
        if self.api_key:
            try:
                self.client = Anthropic(api_key=self.api_key)
                self.use_llm = True
            except Exception as e:
                print(f"Failed to initialize Anthropic client: {e}")
                self.use_llm = False

    def parse(self, user_input: str) -> IntentSchema:
        """Parse user input to intent. Use LLM if available, otherwise fallback."""
        user_input = user_input.strip()
        
        # Handle empty input
        if not user_input:
            return IntentSchema(intent="UNKNOWN", confidence=0.0)
        
        # Handle obvious greetings locally (no need for LLM)
        if self._is_greeting(user_input):
            return IntentSchema(intent="HELP", confidence=1.0)
        
        # Use LLM if available
        if self.use_llm:
            try:
                return self._parse_with_llm(user_input)
            except Exception as e:
                print(f"LLM parsing failed: {e}, falling back to keyword matching")
                return self._parse_with_keywords(user_input)
        else:
            return self._parse_with_keywords(user_input)

    def _is_greeting(self, text: str) -> bool:
        """Check if input is a simple greeting."""
        greetings = ["hi", "hello", "hey", "yo", "sup", "h", "hii", "hiii"]
        return text.lower() in greetings

    def _parse_with_llm(self, user_input: str) -> IntentSchema:
        """Parse using LLM (Claude)."""
        system_prompt = """You are an intent parser for a personal finance assistant. 
Convert user input into structured JSON. You ONLY parse intent - you NEVER calculate budgets or make decisions.

Return ONLY valid JSON with this exact structure:
{
  "intent": "AFFORDABILITY_CHECK|LOG_PURCHASE|LOG_EXPENSE|SET_INCOME|SET_FIXED_EXPENSE|SET_VARIABLE_LIMITS|SET_GOAL|SHOW_STATUS|HELP|UNKNOWN",
  "item": string|null,
  "amount": number|null,
  "currency": "SAR",
  "category": string|null,
  "fixed_expense_name": string|null,
  "frequency": "monthly|weekly|daily|one_time"|null,
  "goal_item": string|null,
  "goal_amount": number|null,
  "goal_timeframe": string|null,
  "confidence": number (0.0-1.0)
}

Intent mapping rules:
- "can I buy", "should I buy", "thinking of getting", "want to buy", "afford" → AFFORDABILITY_CHECK
- "I bought", "purchased", "paid for", "got" (past tense) → LOG_PURCHASE
- "spent", "expense" → LOG_EXPENSE
- "salary", "income", "earn", "my salary is" → SET_INCOME
- "rent is", "fixed expense", "monthly bill" → SET_FIXED_EXPENSE
- "daily budget", "weekly limit", "food budget" → SET_VARIABLE_LIMITS
- "goal", "save for", "want to save" → SET_GOAL
- "summary", "status", "how much left", "show budget" → SHOW_STATUS
- "help", "what can you do" → HELP
- Unclear/irrelevant → UNKNOWN

Extract amounts as numbers (remove currency symbols). Extract timeframes (e.g., "6 months" → "6 months").
Set confidence based on clarity (1.0 = very clear, 0.5 = ambiguous, 0.0 = unclear)."""

        message = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            temperature=0,
            system=system_prompt,
            messages=[{
                "role": "user",
                "content": user_input
            }]
        )

        # Extract JSON from response
        response_text = message.content[0].text.strip()
        
        # Try to parse JSON (may have markdown code blocks)
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
        if json_match:
            response_text = json_match.group(1)
        
        # Parse JSON
        try:
            intent_data = json.loads(response_text)
            return IntentSchema(**intent_data)
        except json.JSONDecodeError:
            # If JSON parsing fails, try to extract from text
            return self._parse_with_keywords(user_input)

    def _parse_with_keywords(self, user_input: str) -> IntentSchema:
        """Fallback: parse using keyword matching (offline mode)."""
        text = user_input.lower()
        
        # Extract numbers from text
        numbers = re.findall(r'\d+(?:\.\d+)?', user_input)
        amount = float(numbers[0]) if numbers else None
        
        # AFFORDABILITY_CHECK patterns
        if any(phrase in text for phrase in ["can i buy", "should i buy", "can i afford", 
                                               "thinking of getting", "want to buy", "thinking of buying"]):
            item = self._extract_item_after_keyword(user_input, 
                                                     ["can i buy", "should i buy", "thinking of getting", 
                                                      "want to buy", "thinking of buying"])
            return IntentSchema(
                intent="AFFORDABILITY_CHECK",
                item=item,
                amount=amount,
                currency="SAR",
                confidence=0.7
            )
        
        # LOG_PURCHASE patterns
        if any(phrase in text for phrase in ["i bought", "purchased", "paid for", "already bought", 
                                               "got a", "bought a"]):
            item = self._extract_item_after_keyword(user_input, 
                                                     ["i bought", "purchased", "paid for", 
                                                      "already bought", "got a", "bought a"])
            return IntentSchema(
                intent="LOG_PURCHASE",
                item=item,
                amount=amount,
                currency="SAR",
                confidence=0.7
            )
        
        # LOG_EXPENSE patterns
        if "spent" in text or "expense" in text:
            # Extract category (word after "on")
            category = None
            if " on " in text:
                parts = text.split(" on ", 1)
                if len(parts) > 1:
                    category = parts[1].split()[0] if parts[1].split() else None
            
            return IntentSchema(
                intent="LOG_EXPENSE",
                category=category,
                amount=amount,
                currency="SAR",
                confidence=0.7
            )
        
        # SET_INCOME patterns
        if any(word in text for word in ["salary", "income", "earn"]):
            return IntentSchema(
                intent="SET_INCOME",
                amount=amount,
                currency="SAR",
                confidence=0.8
            )
        
        # SET_FIXED_EXPENSE patterns
        if any(word in text for word in ["rent", "fixed expense", "monthly bill"]):
            expense_name = "rent" if "rent" in text else "expense"
            return IntentSchema(
                intent="SET_FIXED_EXPENSE",
                fixed_expense_name=expense_name,
                amount=amount,
                frequency="monthly",
                currency="SAR",
                confidence=0.7
            )
        
        # SET_GOAL patterns
        if any(word in text for word in ["goal", "save for", "want to save"]):
            # Extract item
            goal_item = self._extract_item_after_keyword(user_input, 
                                                          ["goal", "save for", "want to save", 
                                                           "saving for"])
            
            # Extract timeframe
            timeframe = None
            timeframe_match = re.search(r'(\d+)\s*(month|week|year)', text)
            if timeframe_match:
                num = timeframe_match.group(1)
                unit = timeframe_match.group(2)
                timeframe = f"{num} {unit}s" if int(num) > 1 else f"{num} {unit}"
            
            return IntentSchema(
                intent="SET_GOAL",
                goal_item=goal_item,
                goal_amount=amount,
                goal_timeframe=timeframe,
                currency="SAR",
                confidence=0.6
            )
        
        # SHOW_STATUS patterns
        if any(phrase in text for phrase in ["summary", "status", "how much left", 
                                               "show budget", "my budget", "remaining"]):
            return IntentSchema(
                intent="SHOW_STATUS",
                confidence=0.9
            )
        
        # HELP patterns
        if any(word in text for word in ["help", "what can you do", "commands"]):
            return IntentSchema(
                intent="HELP",
                confidence=1.0
            )
        
        # UNKNOWN
        return IntentSchema(
            intent="UNKNOWN",
            confidence=0.0
        )

    def _extract_item_after_keyword(self, text: str, keywords: list[str]) -> Optional[str]:
        """Extract item name after a keyword."""
        text_lower = text.lower()
        for keyword in keywords:
            if keyword in text_lower:
                # Find position after keyword
                pos = text_lower.find(keyword) + len(keyword)
                remaining = text[pos:].strip()
                
                # Remove "a" or "an" at the start
                remaining = re.sub(r'^(a|an)\s+', '', remaining, flags=re.IGNORECASE)
                
                # Extract first few words (likely the item name)
                words = remaining.split()
                if words:
                    # Take first 1-3 words as item name, exclude numbers at the end
                    item_words = []
                    for word in words[:3]:
                        if not re.match(r'^\d+(\.\d+)?$', word):
                            item_words.append(word)
                        else:
                            break
                    if item_words:
                        return " ".join(item_words)
        
        return None
