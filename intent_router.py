"""
Intent router: converts natural language to structured JSON commands.
Uses LLM when available, falls back to keyword matching otherwise.

ENHANCED VERSION with:
- Robust typo/misspelling handling
- Profile update detection
- Reality/feasibility awareness
- Better confidence scoring
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
        """Parse using LLM (Claude) with enhanced understanding."""
        system_prompt = """You are an intelligent intent parser for a personal finance application.

CORE RESPONSIBILITIES:

1) ROBUST LANGUAGE UNDERSTANDING
   - Handle misspellings (e.g. "bogt" → "bought", "spen" → "spent", "salery" → "salary")
   - Understand slang and informal language
   - Ignore random punctuation or symbols
   - Parse unusual word orders (e.g. "I bogt a 500 fridge" → item="fridge", amount=500)
   - NEVER ask users to correct spelling
   - NEVER mention mistakes
   - Just understand and proceed

2) REALITY & FEASIBILITY AWARENESS
   - Identify potentially unrealistic scenarios (e.g. saving 500,000 SAR in 12 months with 5,000 salary)
   - Still parse the intent correctly
   - Mark confidence lower for unrealistic requests (0.4-0.6)
   - DO NOT calculate exact budgets
   - DO NOT reject the intent
   - DO NOT invent numbers

3) PROFILE MUTABILITY
   - Users can update their profile directly from chat
   - Examples:
     * "Actually my salary is 9000 now" → SET_INCOME
     * "Change rent to 3000" → SET_FIXED_EXPENSE
     * "Update my income to 12000" → SET_INCOME
     * "My new salary is 15000" → SET_INCOME
     * "Change my goal to buy a house for 200000 in 24 months" → SET_GOAL
   - Treat all profile updates as valid commands

OUTPUT FORMAT - Return ONLY valid JSON (NO markdown, NO explanations):
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

INTENT MAPPING:
- AFFORDABILITY_CHECK: "can I buy", "should I buy", "afford", "thinking of getting"
- LOG_PURCHASE: "I bought", "purchased", "paid for", "got" (past tense)
- LOG_EXPENSE: "spent", "paid", "expense"
- SET_INCOME: "salary", "income", "earn", "update income", "change salary", "new salary"
- SET_FIXED_EXPENSE: "rent", "fixed expense", "monthly bill", "update rent", "utilities"
- SET_VARIABLE_LIMITS: "daily budget", "weekly limit", "food budget"
- SET_GOAL: "goal", "save for", "want to save", "target", "change goal", "update goal"
- SHOW_STATUS: "summary", "status", "how much left", "remaining", "balance"
- HELP: "help", "what can you do", "commands"
- UNKNOWN: Unclear or irrelevant input

EXTRACTION:
- Amounts: numbers only (remove currency symbols). "5000 SAR" → 5000
- Items: without numbers. "fridge 2000" → item="fridge"
- Timeframes: text with units. "6 months" → "6 months", "24 months" → "24 months"
- Categories: from "on" or "for". "spent 40 on food" → category="food"

CONFIDENCE SCORING:
1.0 = Perfect clarity
0.8-0.9 = Minor typos but clear intent
0.6-0.7 = Some ambiguity or informal language
0.4-0.5 = Unrealistic scenario but parseable (e.g. saving 500000 in 12 months with 5000 salary)
0.0-0.3 = Very unclear

Examples:
- "My salary is 12000" → confidence: 1.0
- "My salery is 12000" → confidence: 0.9 (typo)
- "I bogt a fridge 2000" → confidence: 0.8 (typo)
- "save 500000 for car in 12 months" (with 5000 salary) → confidence: 0.5 (unrealistic)
- "change my goal to 50000 in 6 months" → SET_GOAL, confidence: 1.0

You PARSE intent. You do NOT calculate, decide, or store data."""

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
        """Fallback: parse using keyword matching (offline mode) with typo tolerance."""
        text = user_input.lower()
        
        # Extract numbers from text
        numbers = re.findall(r'\d+(?:\.\d+)?', user_input)
        amount = float(numbers[0]) if numbers else None
        
        # AFFORDABILITY_CHECK patterns (with typo variations)
        if any(phrase in text for phrase in ["can i buy", "should i buy", "can i afford", 
                                               "thinking of getting", "want to buy", "thinking of buying",
                                               "can i get", "should i get", "aford", "affor"]):
            item = self._extract_item_after_keyword(user_input, 
                                                     ["can i buy", "should i buy", "thinking of getting", 
                                                      "want to buy", "thinking of buying", "can i get"])
            return IntentSchema(
                intent="AFFORDABILITY_CHECK",
                item=item,
                amount=amount,
                currency="SAR",
                confidence=0.7
            )
        
        # LOG_PURCHASE patterns (with typo variations like "bogt", "bot", "bough")
        if any(phrase in text for phrase in ["i bought", "purchased", "paid for", "already bought", 
                                               "got a", "bought a", "i bot", "i bogt", "just bought",
                                               "bough", "purchas", "i got"]):
            item = self._extract_item_after_keyword(user_input, 
                                                     ["i bought", "purchased", "paid for", 
                                                      "already bought", "got a", "bought a",
                                                      "i bot", "i bogt", "just bought"])
            return IntentSchema(
                intent="LOG_PURCHASE",
                item=item,
                amount=amount,
                currency="SAR",
                confidence=0.7
            )
        
        # LOG_EXPENSE patterns (with typo variations like "spen", "spnt")
        if any(word in text for word in ["spent", "expense", "spen", "spnt", "spnd"]):
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
        
        # SET_INCOME patterns (including updates like "change", "update", "new")
        if any(word in text for word in ["salary", "income", "earn", "salery", "sallary", "incm"]) or \
           any(phrase in text for phrase in ["update income", "change salary", "new salary", 
                                              "actually my salary", "income is now", "my salary is now"]):
            return IntentSchema(
                intent="SET_INCOME",
                amount=amount,
                currency="SAR",
                confidence=0.8
            )
        
        # SET_FIXED_EXPENSE patterns (including updates)
        if any(word in text for word in ["rent", "fixed expense", "monthly bill", "utilities", "internet"]) or \
           any(phrase in text for phrase in ["update rent", "change rent", "rent is now"]):
            expense_name = "rent" if "rent" in text else "expense"
            if "utilities" in text or "utility" in text:
                expense_name = "utilities"
            elif "internet" in text:
                expense_name = "internet"
            
            return IntentSchema(
                intent="SET_FIXED_EXPENSE",
                fixed_expense_name=expense_name,
                amount=amount,
                frequency="monthly",
                currency="SAR",
                confidence=0.7
            )
        
        # SET_GOAL patterns (including updates)
        if any(word in text for word in ["goal", "save for", "want to save", "target", "saving for"]) or \
           any(phrase in text for phrase in ["change goal", "update goal", "change my goal", "update my goal"]):
            # Extract item
            goal_item = self._extract_item_after_keyword(user_input, 
                                                          ["goal", "save for", "want to save", 
                                                           "saving for", "target", "change goal to",
                                                           "update goal to", "change my goal to"])
            
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
        
        # SHOW_STATUS patterns (including variations)
        if any(phrase in text for phrase in ["summary", "status", "how much left", 
                                               "show budget", "my budget", "remaining",
                                               "balance", "what's left", "how much do i have"]):
            return IntentSchema(
                intent="SHOW_STATUS",
                confidence=0.9
            )
        
        # HELP patterns
        if any(word in text for word in ["help", "what can you do", "commands", "how to use"]):
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
                        # Skip "for", "in", "to" and numbers
                        if word.lower() not in ["for", "in", "to"] and not re.match(r'^\d+(\.\d+)?$', word):
                            item_words.append(word)
                        elif re.match(r'^\d+(\.\d+)?$', word):
                            break
                    if item_words:
                        return " ".join(item_words)
        
        return None
