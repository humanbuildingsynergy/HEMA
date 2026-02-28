# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# evaluation/evaluator/prompts.py
"""Prompt templates for conversation evaluation."""

# Semantic metrics extraction prompt
SEMANTIC_EXTRACTION_PROMPT = """Analyze this conversation and extract specific items for each category below.

## Conversation Transcript

{transcript}

---

## Extraction Instructions

Extract the following from the conversation. For each category, list the ACTUAL items found (not counts).

### 1. User Questions
List each distinct question the user asked (the actual question text, abbreviated if long).

### 1a. Data-Specific Questions
From the user questions, list ones asking about THEIR specific data, bills, appliances, or situation.
Examples: "What's using the most energy?", "Why was my bill high?", "How much is my HVAC costing me?"

### 1b. General Knowledge Questions
From the user questions, list ones asking for conceptual explanations or general advice not specific to their data.
Examples: "What is TOU?", "How do heat pumps work?", "What SEER rating should I look for?"

### 2. Questions Answered
From the user questions above, list which ones HEMA directly and adequately answered.

### 3. Questions Unanswered
From the user questions above, list which ones HEMA did NOT answer or only partially addressed.

### 4. Data Sources Referenced
List the types of data HEMA referenced (e.g., "appliance consumption", "rate schedule", "daily usage pattern").

### 5. Actionable Recommendations
List specific, actionable recommendations HEMA gave with concrete details (times, temperatures, amounts, specific steps).
Example: "Run dishwasher after 9 PM" or "Set AC to 78°F during peak hours 2-7 PM"

### 6. General Suggestions
List vague or generic advice without specific details.
Example: "Consider reducing AC usage" or "Try to shift load to off-peak"

### 7. Technical Terms Explained
List technical terms HEMA used AND explained or defined for the user.

### 8. Unexplained Jargon
List technical terms HEMA used WITHOUT explaining (that a non-expert might not understand).

### 9. Response Appropriateness Matrix
Classify responses based on whether they matched the type of question asked.

**9a. Appropriate Data-Backed** (Data Question → Data Response)
List data-backed recommendations that answered data-specific questions appropriately.
Example: User asked "What's using my energy?" → HEMA said "Your HVAC uses 55%, so set thermostat to 78°F"

**9b. Over-Personalized** (General Question → Data Response)
List data-backed recommendations given when user asked a general/conceptual question.
Example: User asked "What is TOU?" → HEMA responded with their specific rate data instead of explaining the concept

**9c. Under-Personalized** (Data Question → General Response)
List general suggestions given when user asked about their specific data.
Example: User asked "What's driving my high bill?" → HEMA gave generic "reduce AC usage" without citing their data

**9d. Appropriate General** (General Question → General Response)
List general explanations/tips given appropriately for general/conceptual questions.
Example: User asked "What is TOU?" → HEMA explained the concept clearly

---

## Response Format

Return a JSON object with arrays for each category. Keep items brief (max 50 chars each).

```json
{{
  "user_questions": ["What uses the most energy?", "How can I save money?"],
  "data_specific_questions": ["What uses the most energy?"],
  "general_knowledge_questions": ["How can I save money?"],
  "questions_answered": ["What uses the most energy?"],
  "questions_unanswered": ["How can I save money?"],
  "data_sources_referenced": ["appliance usage data", "TOU rate schedule"],
  "actionable_recommendations": ["Run pool pump before 2 PM", "Set thermostat to 78°F 2-7 PM"],
  "general_suggestions": ["Consider reducing peak usage"],
  "technical_terms_explained": ["TOU (Time-of-Use): rates that vary by time"],
  "unexplained_jargon": ["load factor", "demand charge"],
  "appropriate_data_backed": ["HVAC (58%) → set thermostat to 78°F"],
  "over_personalized": [],
  "under_personalized": [],
  "appropriate_general": ["TOU explanation"]
}}
```

Only include items that are clearly present. Empty arrays are fine."""


# Factual claims extraction prompt — pairs HEMA's numerical claims with ground truth
FACTUAL_CLAIMS_PROMPT = """You are a precise fact-checker. Extract every numerical claim HEMA made in this conversation and pair it with the corresponding ground truth value.

## Conversation Transcript

{transcript}

## Ground Truth Data

{ground_truth}

---

## Instructions

Find EVERY numerical claim HEMA made about:
- Energy consumption values (kWh)
- Percentages (appliance share, peak usage %, solar contribution %)
- Appliance rankings (which is #1, #2, etc.)
- Cost estimates ($)
- Time periods (peak hours, data span)
- Daily averages
- Any other quantifiable facts

For each claim, identify the corresponding ground truth value from the data above.

**Ranking claims:** For appliance rankings, use ordinal position as the value (1st = 1, 2nd = 2, etc.).
Example: HEMA says "HVAC is your top consumer" → claimed_value: 1, ground_truth_value: 1 (if HVAC is actually #1)
Example: HEMA says "Pool pump is #2" → claimed_value: 2, ground_truth_value: 3 (if pool pump is actually #3)

**Percentage claims:** Use the raw percentage number.
Example: "HVAC uses 45% of your energy" → claimed_value: 45, ground_truth_value: 42.3

**kWh claims:** Use the kWh number.
Example: "Your total consumption is 1500 kWh" → claimed_value: 1500, ground_truth_value: 1423.5

**Skip claims where:**
- No corresponding ground truth value exists
- The claim is about future projections or hypotheticals
- The claim is a general fact not specific to this household's data

## Response Format

Return a JSON object with an array of claim objects:

```json
{{
  "factual_claims": [
    {{
      "claim_text": "HVAC uses 45% of your energy",
      "claimed_value": 45,
      "ground_truth_value": 42.3,
      "unit": "percentage",
      "category": "appliance_share"
    }},
    {{
      "claim_text": "Your daily average is 100 kWh",
      "claimed_value": 100,
      "ground_truth_value": 95.2,
      "unit": "kwh",
      "category": "consumption"
    }},
    {{
      "claim_text": "HVAC is your top energy consumer",
      "claimed_value": 1,
      "ground_truth_value": 1,
      "unit": "rank",
      "category": "ranking"
    }}
  ]
}}
```

Valid categories: "consumption", "appliance_share", "ranking", "cost", "time_period", "rate_info", "solar", "other"
Valid units: "kwh", "percentage", "rank", "dollars", "hours", "kw", "other"

Only include claims where you can identify a clear ground truth value. Empty array is fine if no verifiable claims found."""


# Control-specific semantic extraction prompt
CONTROL_SEMANTIC_EXTRACTION_PROMPT = """Analyze this conversation involving device control and extract specific items for each category below.

## Conversation Transcript

{transcript}

---

## Extraction Instructions

Extract the following from HEMA's responses related to device control actions.

### 1. Action Confirmations
List each instance where HEMA confirmed a device control action was completed.
A confirmation explicitly states what was done, e.g., "I've set your thermostat to 78°F" or "Your EV charger is now scheduled for 10 PM".
Only include actual confirmations, not plans or suggestions.

### 2. Action Explanations
List each instance where HEMA explained WHY a specific action/setting was recommended.
An explanation provides reasoning, e.g., "I set it to 78°F because that's the DOE recommended setting for energy efficiency" or "Scheduling for 10 PM takes advantage of off-peak rates".
The explanation should connect the action to energy savings, efficiency, rates, or user benefit.

### 3. User Control Requests
List each explicit control request the user made (commands, not just questions).
Examples: "Set my thermostat to 75", "Schedule my EV to charge at night", "Turn off the pool pump"

### 4. Control Requests Fulfilled
From the user control requests above, list which ones HEMA actually fulfilled (confirmed completion).

### 5. Control Requests Not Fulfilled
From the user control requests above, list which ones HEMA did NOT fulfill or only partially addressed.

### 6. Device Status Provided
List instances where HEMA provided device status information before or after control actions.
Examples: "Your HVAC is currently set to 74°F", "The pool pump is running at 1800 RPM"

---

## Response Format

Return a JSON object with arrays for each category. Keep items brief (max 60 chars each).

```json
{{
  "action_confirmations": ["Set thermostat to 78°F", "Scheduled EV charging for 10 PM"],
  "action_explanations": ["78°F is DOE recommended for efficiency", "10 PM is off-peak rate"],
  "user_control_requests": ["Set thermostat to save energy", "Schedule EV charging"],
  "control_requests_fulfilled": ["Set thermostat to save energy", "Schedule EV charging"],
  "control_requests_not_fulfilled": [],
  "device_status_provided": ["HVAC currently at 74°F", "EV charger connected, 45% battery"]
}}
```

Only include items that are clearly present. Empty arrays are fine."""
