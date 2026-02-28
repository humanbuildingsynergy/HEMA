# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# evaluation/runners/vanilla_llm.py
"""Vanilla LLM runner for comparative evaluation.

Provides multiple vanilla LLM baselines for comparison with HEMA:
- VanillaLLMRunner: Raw CSV data with minimal prompting
- VanillaStructuredRunner: Preprocessed structured data with minimal prompting
- VanillaStructuredCoTRunner: Preprocessed structured data with CoT prompting
"""

from dataclasses import dataclass
from typing import Optional, List
import time

import pandas as pd
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from config.llm_factory import create_llm
from config.config import LLMProvider


@dataclass
class VanillaResponse:
    """Response from vanilla LLM."""

    response: str
    latency_ms: float
    input_tokens: int
    output_tokens: int


class VanillaLLMRunner:
    """Single LLM baseline for comparison with HEMA.

    Uses the same LLM as HEMA's agents but without:
    - Multi-agent routing
    - Specialized tools
    - RAG retrieval
    - Device control capabilities
    """

    def __init__(
        self,
        provider: LLMProvider = LLMProvider.OPENAI,
        model: str = "gpt-4o-mini",
        data_context: Optional[str] = None,
        temperature: float = 0.2,
    ):
        """Initialize the vanilla LLM runner.

        Args:
            provider: LLM provider (default: OpenAI)
            model: Model name (default: gpt-4o-mini, same as HEMA)
            data_context: Raw energy data as string (CSV format)
            temperature: Temperature for generation (default: 0.2)
        """
        self.provider = provider
        self.model = model
        self.llm = create_llm(provider, model, temperature)
        self.data_context = data_context
        self.conversation_history: List[dict] = []
        self.system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        """Build system prompt with raw energy data context."""
        return f"""You are an energy advisor helping homeowners understand and optimize their electricity usage.

You have access to the following energy consumption data for this household (raw CSV format, 15-minute intervals, values in kW):

{self.data_context or "No energy data available."}

Using this data, answer the user's questions about their energy usage, provide insights about their consumption patterns, and offer recommendations for reducing their energy bills.

Guidelines:
- Be helpful and conversational
- Analyze the raw data to answer questions (values are in kW, multiply by 0.25 to get kWh per interval)
- When users ask about "my" usage, cite their specific numbers from the data
- Provide actionable recommendations with specific numbers (not generic advice)
- Adapt to the user's technical level: explain terms like kWh, peak hours, and load factor for beginners
- If asked about weather forecasts or comparisons to other homes, acknowledge you don't have that data"""

    def invoke(self, user_message: str) -> VanillaResponse:
        """Get response from vanilla LLM.

        Args:
            user_message: The user's message

        Returns:
            VanillaResponse with response text and metrics
        """
        start_time = time.time()

        # Build messages with conversation history
        messages = [SystemMessage(content=self.system_prompt)]
        for turn in self.conversation_history:
            if turn["role"] == "user":
                messages.append(HumanMessage(content=turn["content"]))
            else:
                messages.append(AIMessage(content=turn["content"]))
        messages.append(HumanMessage(content=user_message))

        # Get response
        response = self.llm.invoke(messages)
        latency_ms = (time.time() - start_time) * 1000

        # Extract token usage from response metadata
        input_tokens = 0
        output_tokens = 0
        if hasattr(response, "response_metadata") and response.response_metadata:
            usage = response.response_metadata.get("usage", {}) or response.response_metadata.get("token_usage", {})
            input_tokens = usage.get("prompt_tokens", 0) or usage.get("input_tokens", 0)
            output_tokens = usage.get("completion_tokens", 0) or usage.get("output_tokens", 0)

        # Update conversation history
        self.conversation_history.append({"role": "user", "content": user_message})
        self.conversation_history.append({"role": "assistant", "content": response.content})

        return VanillaResponse(
            response=response.content,
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

    def get_conversation_history(self) -> List[dict]:
        """Get the full conversation history."""
        return self.conversation_history.copy()

    def reset(self):
        """Reset conversation history for a new conversation."""
        self.conversation_history = []


def load_raw_data_context(data_file: str, days: int = 14) -> str:
    """Load raw CSV data directly without any preprocessing.

    The vanilla LLM receives the raw data exactly as it appears in the CSV,
    with only time-based filtering to limit to the specified number of days.
    No aggregation, no statistics, no summarization - the LLM must interpret
    the raw 15-minute interval data itself.

    IMPORTANT: Uses the FIRST N days of data (from start of dataset) to ensure
    consistency with HEMA's data window for fair comparison.

    Args:
        data_file: Path to energy CSV file
        days: Number of days of data to include (default 14 for 2 weeks)

    Returns:
        Raw CSV content as string (header + filtered rows)
    """
    df = pd.read_csv(data_file)

    # Filter to FIRST N days (from start of dataset) for consistency with HEMA
    df["_timestamp"] = pd.to_datetime(df["local_15min"])
    start_date = df["_timestamp"].min()
    end_date = start_date + pd.Timedelta(days=days)
    df = df[df["_timestamp"] < end_date]
    df = df.drop(columns=["_timestamp"])  # Remove helper column

    # Return raw CSV content - no processing, no aggregation
    return df.to_csv(index=False)


def load_structured_data_context(data_file: str, days: int = 14) -> str:
    """Load and preprocess energy data using HEMA's existing analysis functions.

    Reuses the same analysis logic that HEMA's tools use, ensuring consistency
    between the structured data context and what HEMA would compute.

    IMPORTANT: Uses the FIRST N days of data (from start of dataset) to ensure
    consistency with HEMA's data window for fair comparison.

    Args:
        data_file: Path to energy CSV file
        days: Number of days of data to include (default 14 for 2 weeks)

    Returns:
        Structured summary string with pre-computed analysis
    """
    import os
    from core.analysis.appliance_analyzer import ApplianceAnalyzer
    from core.analysis.consumption_analyzer import ConsumptionAnalyzer
    from core.analysis.aggregation import AggregationEngine

    # Load and filter data to FIRST N days (keep local_15min column for AggregationEngine)
    df = pd.read_csv(data_file)
    df["local_15min"] = pd.to_datetime(df["local_15min"])
    start_date = df["local_15min"].min()
    end_date = start_date + pd.Timedelta(days=days)
    df = df[df["local_15min"] < end_date]

    # Detect solar columns
    solar_cols = {"solar", "solar2", "Solar power generation 1", "Solar power generation 2"}
    has_solar = any(col in df.columns for col in solar_cols)

    # Use HEMA's analyzers
    appliance_analyzer = ApplianceAnalyzer()
    consumption_analyzer = ConsumptionAnalyzer()
    aggregation_engine = AggregationEngine(df)

    # Get analysis results using HEMA's functions
    appliance_results = appliance_analyzer.analyze(df)
    consumption_results = consumption_analyzer.analyze(df)
    peak_analysis = aggregation_engine.analyze_peak_hours()
    weekday_weekend = aggregation_engine.compare_weekday_weekend()

    # Get additional analyses for fair comparison
    frequency_results = appliance_analyzer.analyze_usage_frequency(df)
    variability_results = appliance_analyzer.analyze_usage_variability(df)

    # Build structured summary from HEMA's analysis output
    summary = f"""## Energy Consumption Analysis

**Date Range:** {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')} ({days} days)

### Overall Consumption
- **Total:** {consumption_results['summary']['total_kwh']:.1f} kWh
- **Daily Average:** {consumption_results['summary']['avg_daily_kwh']:.1f} kWh/day
- **Peak Demand:** {consumption_results['summary']['peak_demand_kw']:.2f} kW
- **Base Load:** {consumption_results['summary']['base_load_kw']:.2f} kW
- **Load Factor:** {consumption_results['summary']['load_factor']:.2f}

### Appliance Rankings (by total kWh)
"""
    for i, item in enumerate(appliance_results["consumption_rankings"][:10], 1):
        summary += f"{i}. {item['appliance']}: {item['total_kwh']:.1f} kWh ({item['percentage']:.1f}%)\n"

    summary += f"""
### Peak vs Off-Peak ({peak_analysis['peak_period']})
- **Peak Consumption:** {peak_analysis['consumption']['peak_kwh']:.1f} kWh ({peak_analysis['consumption']['peak_pct']:.1f}%)
- **Off-Peak Consumption:** {peak_analysis['consumption']['off_peak_kwh']:.1f} kWh ({peak_analysis['consumption']['off_peak_pct']:.1f}%)
- **Peak Intensity Ratio:** {peak_analysis['intensity']['ratio']:.2f}x

### Weekday vs Weekend
- **Weekday Average:** {weekday_weekend['weekday']['avg_daily_kwh']:.1f} kWh/day
- **Weekend Average:** {weekday_weekend['weekend']['avg_daily_kwh']:.1f} kWh/day
- **Higher On:** {weekday_weekend['comparison']['higher_on']} ({weekday_weekend['comparison']['difference_pct']:.1f}% difference)
"""

    # Add Usage Frequency section
    freq_summary = frequency_results.get("summary", {})
    freq_profiles = frequency_results.get("appliance_profiles", {})
    most_active = freq_summary.get("most_active_appliance", "N/A")
    busiest_hour = freq_summary.get("busiest_hour")

    summary += f"""
### Usage Frequency (When Appliances Run)
- **Most Active Appliance:** {most_active}
- **Busiest Hour:** {f"{busiest_hour}:00" if busiest_hour is not None else "N/A"}

**Peak Usage Hours by Appliance:**
"""
    for appliance, profile in list(freq_profiles.items())[:5]:
        if "error" not in profile:
            peak_hours = profile.get("peak_usage_hours", [])
            avg_active = profile.get("avg_daily_active_hours", 0)
            if peak_hours:
                hours_str = ", ".join(f"{h}:00" for h in sorted(peak_hours)[:4])
                summary += f"- {appliance}: {hours_str} ({avg_active:.1f} hrs/day active)\n"
            else:
                summary += f"- {appliance}: No consistent peak ({avg_active:.1f} hrs/day active)\n"

    # Add Usage Variability section
    var_summary = variability_results.get("summary", {})
    var_rankings = variability_results.get("rankings", [])
    most_variable = var_summary.get("most_variable", "N/A")
    most_consistent = var_summary.get("most_consistent", "N/A")

    summary += f"""
### Usage Variability (Load Shifting Flexibility)
CV = Coefficient of Variation (higher = more variable = easier to shift)

| Appliance | CV | Variability | Avg kWh/day |
|-----------|-----|------------|-------------|
"""
    for rank in var_rankings[:5]:
        cv = rank.get("cv", 0)
        level = rank.get("variability_level", "unknown")
        mean_kwh = rank.get("mean_kwh", 0)
        summary += f"| {rank['appliance']} | {cv:.2f} | {level} | {mean_kwh:.2f} |\n"

    summary += f"""
- **Most Flexible (High CV):** {most_variable} - good candidate for load shifting
- **Most Consistent (Low CV):** {most_consistent} - baseload appliance
"""

    # Add TOU Rate Analysis with cost estimates
    # Load rate data to get actual rates
    rate_path = "data/utility_rate/utility_rate_sample.csv"
    if os.path.exists(rate_path):
        rate_df = pd.read_csv(rate_path)
        # Check if it's TOU (multiple time periods)
        is_tou = rate_df["Start Time"].nunique() > 1 if "Start Time" in rate_df.columns else False

        if is_tou and "Rate (cents per kWh)" in rate_df.columns:
            peak_rate = rate_df["Rate (cents per kWh)"].max()
            off_peak_rate = rate_df["Rate (cents per kWh)"].min()

            peak_kwh = peak_analysis["consumption"]["peak_kwh"]
            off_peak_kwh = peak_analysis["consumption"]["off_peak_kwh"]
            peak_cost = peak_kwh * peak_rate / 100
            off_peak_cost = off_peak_kwh * off_peak_rate / 100

            # Estimate savings from shifting 20% of peak to off-peak
            shift_amount = peak_kwh * 0.20
            savings_per_period = shift_amount * (peak_rate - off_peak_rate) / 100
            monthly_savings = savings_per_period * (30 / days)

            summary += f"""
### TOU Rate Analysis
- **Peak Rate:** {peak_rate:.2f} ¢/kWh | **Off-Peak Rate:** {off_peak_rate:.2f} ¢/kWh

**Consumption by Rate Period:**
- Peak: {peak_kwh:.1f} kWh ({peak_analysis['consumption']['peak_pct']:.1f}%) - ${peak_cost:.2f}
- Off-Peak: {off_peak_kwh:.1f} kWh ({peak_analysis['consumption']['off_peak_pct']:.1f}%) - ${off_peak_cost:.2f}

**Savings Potential:** Shifting 20% of peak usage to off-peak could save ~${monthly_savings:.2f}/month
"""

    # Add Solar Analysis if solar columns present
    if has_solar:
        try:
            from core.analysis.solar import SolarAvailabilityAnalyzer, SolarAlignmentAnalyzer

            solar_analyzer = SolarAvailabilityAnalyzer()
            solar_profile = solar_analyzer.get_average_hourly_profile(df)

            if "error" not in solar_profile:
                avg_daily_kwh = solar_profile.get("avg_daily_kwh", 0)
                peak_hour = solar_profile.get("peak_hour", 12)
                peak_kw = solar_profile.get("peak_mean_kw", 0)
                gen_start = solar_profile.get("generation_start", 6)
                gen_end = solar_profile.get("generation_end", 18)

                summary += f"""
### Solar Generation Profile
- **Average Daily Generation:** {avg_daily_kwh:.1f} kWh
- **Peak Generation Hour:** {peak_hour}:00 ({peak_kw:.2f} kW average)
- **Generation Window:** {gen_start}:00 - {gen_end}:00
"""

            # Get solar alignment for appliances
            alignment_analyzer = SolarAlignmentAnalyzer()
            alignment_results = alignment_analyzer.calculate_alignment(df)

            if alignment_results.get("success") and "appliance_alignments" in alignment_results:
                alignments = alignment_results["appliance_alignments"]

                # Sort by alignment score
                sorted_alignments = sorted(
                    [(app, data) for app, data in alignments.items()
                     if data.get("alignment_score") is not None],
                    key=lambda x: x[1].get("alignment_score", 0),
                    reverse=True,
                )

                if sorted_alignments:
                    summary += """
### Solar Alignment (Self-Consumption Opportunity)
| Appliance | Alignment | Interpretation |
|-----------|-----------|----------------|
"""
                    for app, data in sorted_alignments[:5]:
                        score = data.get("alignment_percentage", 0)
                        if score >= 70:
                            indicator = "High - runs during solar"
                        elif score >= 40:
                            indicator = "Medium - some overlap"
                        else:
                            indicator = "Low - consider shifting"
                        summary += f"| {app} | {score:.0f}% | {indicator} |\n"

                    best = sorted_alignments[0]
                    worst = sorted_alignments[-1]
                    summary += f"""
- **Best Aligned:** {best[0]} ({best[1].get('alignment_percentage', 0):.0f}%) - runs mostly during solar
- **Worst Aligned:** {worst[0]} ({worst[1].get('alignment_percentage', 0):.0f}%) - consider shifting to solar hours
"""
        except ImportError:
            pass  # Solar analyzers not available
        except Exception:
            pass  # Solar analysis failed, continue without it

    # Add Key Insights at the end
    summary += "\n### Key Insights\n"
    for insight in appliance_results.get("insights", [])[:5]:
        summary += f"- {insight}\n"

    return summary


class VanillaStructuredRunner(VanillaLLMRunner):
    """Vanilla LLM with preprocessed structured data context (minimal prompting)."""

    def _build_system_prompt(self) -> str:
        """Build system prompt for structured data context."""
        return f"""You are an energy advisor helping homeowners understand and optimize their electricity usage.

You have access to the following energy analysis summary for this household:

{self.data_context or "No energy data available."}

Using this analysis, answer the user's questions about their energy usage, provide insights about their consumption patterns, and offer recommendations for reducing their energy bills.

Guidelines:
- Be helpful and conversational
- When users ask about "my" usage, cite their specific numbers from the data
- Provide actionable recommendations with specific numbers (not generic advice)
- Adapt to the user's technical level: explain terms like kWh, peak hours, and load factor for beginners
- If asked about weather forecasts or comparisons to other homes, acknowledge you don't have that data"""


class VanillaStructuredCoTRunner(VanillaLLMRunner):
    """Vanilla LLM with structured data AND CoT prompting."""

    def _build_system_prompt(self) -> str:
        """Build system prompt with structured data and comprehensive CoT reasoning."""
        return f"""You are an energy advisor helping homeowners understand and optimize their electricity usage.

## Your Expertise Areas

**Analysis**: You excel at interpreting energy consumption data:
- Consumption patterns (daily, weekly, seasonal)
- Appliance-level breakdown and rankings
- Peak vs off-peak usage analysis
- Cost optimization strategies

**Knowledge**: You can explain energy concepts and best practices:
- Energy Concepts: Time-of-use pricing, demand response, net metering, peak hours
- Technologies: Heat pumps, solar panels, smart thermostats, EVs, battery storage
- Best Practices: Energy efficiency tips, behavioral changes, home improvements
- Utility Information: Rate structures, typical rebate programs

---

## Pre-Analyzed Energy Data

{self.data_context or "No energy data available."}

---

## Step-by-Step Reasoning Process

### Step 1: Identify Query Type
Determine if this is:
- **Analysis question**: About their specific data (usage, costs, patterns)
- **Knowledge question**: About concepts, technologies, or general best practices
- **Hybrid**: Needs both data interpretation AND concept explanation

### Step 2: Extract Relevant Information
- For analysis questions: Pull specific numbers from the data context above
- For knowledge questions: Draw on energy concepts and best practices

### Step 3: Detect User's Technical Level

**Expert signals** (use technical, data-rich responses):
- Uses terms like kWh, SEER, TOU, load factor, demand charge, CV
- Asks for specific metrics, percentages, or calculations
- Mentions specific temperatures, times, or rates
- Requests payback periods or efficiency comparisons

**Beginner signals** (use simple, actionable responses):
- Uses vague terms: "a lot", "too high", "normal"
- Asks "what is" or "what does X mean" questions
- Expresses confusion or frustration
- Uses everyday language about bills or costs

### Step 4: Form Response with Appropriate Style

**For Expert Users:**
- Lead with numbers and data
- Include percentages, comparisons, and statistical measures
- Use technical terminology without extensive definitions
- Provide detailed calculations when relevant

**For Beginner Users:**
- Lead with the key takeaway in plain language
- Define technical terms on first use (kWh = energy units, kW = power)
- Focus on actionable strategies they can implement
- Keep initial response concise—offer to explain more

### Step 5: Apply Rate-Aware Strategy

- **Flat rate (no TOU)**: Focus on total consumption reduction; timing doesn't affect cost
- **TOU rates**: Emphasize peak-hour consumption and load shifting opportunities
- **Solar homes**: Note solar alignment; poor alignment = opportunity to shift usage to solar hours
- **TOU + Solar**: Prioritize appliances with both poor solar alignment AND high peak usage

---

## Pacing Guidelines

- **Don't dump information**: Start with the main finding, then offer more detail
- **For beginners**: Present ONE key insight, then ask if they want more
- **For complex topics**: Use clear section headings to organize
- **End with an offer**: "Would you like me to explain further?" or "Want specific savings calculations?"

---

## Specific Recommendation Requirements

When suggesting changes, ALWAYS include:
1. **Their data first**: Cite specific numbers from the context
2. **What to do**: Specific action to take
3. **When to do it**: Specific times or conditions
4. **Savings estimate**: Calculated or estimated from their data

**Examples:**
- BAD: "Consider reducing your HVAC usage"
- GOOD: "Your HVAC at 55% is your biggest cost. Raising the thermostat 2°F during peak hours (2-7pm) could save ~10% on cooling costs."

- BAD: "A heat pump might be a good option"
- GOOD: "Based on your 1,067 kWh HVAC usage, a heat pump upgrade (SEER 16+) could cut cooling costs by 30-40%. Typical rebates are $500-1,500."

---

## Critical Guidelines

### Data Integrity
**NEVER fabricate or estimate numbers not in the provided data.**
- Only cite numbers that appear in the pre-analyzed context above
- If asked about data you don't have, say "I don't have that specific data"
- Be explicit about what the data shows vs. what it doesn't
- When data is limited to a specific time period, clearly state that boundary

### Knowledge Accuracy
When explaining concepts or giving advice beyond the data:
- Base recommendations on established energy best practices
- Note that rebate amounts and rate details vary by location and time
- Suggest verifying specific programs with local utility

### Limitations
You do NOT have access to:
- Real-time weather data or forecasts
- Comparison data from other homes
- Live utility rate updates
- Data outside the pre-analyzed period

If asked about these, acknowledge the limitation honestly and provide what help you can based on the available data and general knowledge."""
