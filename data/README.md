# Sample Energy Data

This directory contains sample/synthetic energy data files that demonstrate the required data format for HEMA.

## ⚠️ Important: About the Included Data

> **All data files in this directory are SYNTHETIC and NOT from actual households.**
>
> - `energy_data_sample.csv` — Synthetic energy consumption data
> - `appliance_thresholds_sample.csv` — Synthetic threshold values
> - `utility_rate_sample.csv` — Sample rate structure (representative only)
>
> **These files are intended for:**
> - Understanding required data formats
> - Testing HEMA functionality without sensitive data
> - Quick demonstrations and evaluation
> - Development and debugging
>
> **For real analysis**, replace with your own energy data from:
> - Your utility provider's smart meter downloads
> - Pecan Street Dataport (academic access)
> - Your own home energy monitoring devices
>
> **Research Note:** The manuscript evaluation used real data from Pecan Street Dataport with proper consent. This repository includes only generic samples to allow public distribution without privacy concerns.

## File Descriptions

### 1. `energy_data_sample.csv`

**15-minute interval energy consumption data** for individual appliances.

**Format:**
- Column 1: Timestamp (ISO 8601 format with timezone)
- Columns 2+: Power consumption in kW for each appliance

**Example:**
```
local_15min,HVAC unit,Refrigerator,Electric water heater,Washing machine,Clothes dryer,...
2024-01-15 00:00:00+00:00,0.5,0.2,0.1,0.0,0.0,...
2024-01-15 00:15:00+00:00,0.5,0.2,0.1,0.0,0.0,...
```

**Requirements:**
- Timestamps must be consecutive at 15-minute intervals
- Power values must be non-negative
- Values can be 0 for appliances not in use
- Include actual appliance columns that exist in your home (e.g., if you don't have a pool pump, exclude that column)

**Typical Coverage:**
- Multiple weeks of continuous data (30-90 days recommended for meaningful analysis)
- All hours of day and all seasons for comprehensive analysis
- Examples: 2023-06-30 through 2023-08-15 (summer pattern with AC usage), or full year for seasonal variation

### 2. `appliance_thresholds_sample.csv`

**Threshold values** to automatically detect when appliances turn "on".

Used by the Analysis Agent to identify appliance usage periods.

**Format:**
```
appliance_name,threshold_kw
HVAC unit,0.5
Refrigerator,0.2
Electric water heater,0.15
Washing machine,0.1
...
```

**Requirements:**
- One row per appliance (must match appliance columns in energy data)
- Threshold should be the minimum power draw that indicates the appliance is actively running
- For always-on appliances (refrigerator), use a value that distinguishes normal operation from idle

**Guidelines:**
- **HVAC/Heating units**: 0.4-1.0 kW (compressor power)
- **Electric water heater**: 0.1-0.5 kW depending on capacity
- **EV charger**: 1.0-7.0 kW depending on charging mode
- **Clothes dryer**: 2.0-5.0 kW
- **Washing machine**: 0.05-0.5 kW
- **Dishwasher**: 0.1-0.5 kW
- **Microwave/Oven**: 1.0-3.0 kW
- **Refrigerator**: 0.1-0.3 kW (continuous baseline)
- **Pool pump**: 0.5-2.0 kW

**Important: Thresholds File is OPTIONAL** ✅
- The HEMA system works **without** appliance thresholds
- If no thresholds file is provided, the system uses a default 0.01 kW threshold for all appliances
- Thresholds improve accuracy of appliance frequency analysis and standby power detection
- For best results: provide accurate thresholds specific to your appliances
- Without thresholds: HEMA still analyzes consumption patterns, just with less appliance-level granularity

### 3. `utility_rate_sample.csv`

**Time-of-use (TOU) electricity rate structure**.

Defines different rates for different hours and seasons.

### 4. `knowledge_base/` (Knowledge Base Documents for RAG)

**Energy education documents** for the Knowledge Agent's Retrieval-Augmented Generation (RAG) system.

The Knowledge Agent uses semantic search over these documents to answer energy-related questions. See [README Knowledge Base & RAG section](../README.md#knowledge-base--rag) for details.

**Directory Structure:**
```
data/knowledge_base/
├── guides/                          # Energy efficiency guides
│   └── energy-saver-guide-2022.pdf  # General energy saving tips
├── utility_rates/                   # Rate and pricing information
│   ├── austin_energy_rates.md       # TOU rate schedules
│   └── COA-Utilities-Rates-and-Fees.pdf
└── rebates/                         # Incentive programs
    └── austin_energy_rebates.md     # Available rebates and incentives
```

**Adding Your Own Documents:**

To include custom energy education documents:

1. Place documents in appropriate `knowledge_base/` subdirectories
2. Supported formats: PDF, Markdown, plain text
3. On first Knowledge Agent query, the system will automatically:
   - Load all documents from `knowledge_base/`
   - Create semantic chunks for searching
   - Build vector embeddings (requires OPENAI_API_KEY)
   - Cache in `data/vector_index/` (not tracked in git)

**Examples of content to add:**
- Local utility rebate programs
- ENERGY STAR appliance specifications
- Renewable energy guidelines
- Home efficiency improvement guides
- Demand response program information

**Format:**
```
hour_start,hour_end,month,day_type_id,rate_kwh,adjustment_kwh
0,5,1,1,0.095,0.0
5,9,1,1,0.121,0.0
9,14,1,1,0.095,0.0
14,20,1,1,0.215,0.0
20,23,1,1,0.095,0.0
...
```

**Columns:**
- `hour_start`: Hour when rate begins (0-23)
- `hour_end`: Hour when rate ends (0-23, exclusive)
- `month`: Month number (1-12)
- `day_type_id`: 1 = weekday, 2 = weekend/holiday
- `rate_kwh`: Electricity price in $/kWh
- `adjustment_kwh`: Grid adjustment factor (typically 0.0)

**Requirements:**
- Must cover all hours of the day (0-24) for every month and day type
- No overlapping time periods for same month/day_type
- Rates should reflect actual utility rates (check your electric bill)

**Common TOU Patterns:**
- **Off-peak (night/early morning)**: $0.08-0.10/kWh (typically 9 PM - 5 AM)
- **Mid-peak (morning/evening)**: $0.10-0.12/kWh (typically 5-9 AM and 9 PM onwards)
- **Peak (afternoon/early evening)**: $0.20-0.30/kWh (typically 2-8 PM)
- **Weekend rates**: Generally 10-20% lower than weekday

## Data Volume Recommendations

| Use Case | Duration | Records | File Size |
|----------|----------|---------|-----------|
| Quick testing | 1 week | 672 | ~30 KB |
| Basic evaluation | 30 days | 2,880 | ~130 KB |
| Comprehensive evaluation | 90 days | 8,640 | ~390 KB |
| Full year (recommended) | 365 days | 35,040 | ~1.6 MB |

## How to Use Your Own Data

1. **Export from your energy monitoring system:**
   - HEMA requires **appliance-level** (sub-metered) data, not whole-home smart meter data
   - Use home energy monitors with circuit-level tracking (e.g., Sense, Emporia Vue, IoTaWatt)
   - Or access appliance-level datasets like Pecan Street Dataport (academic access)

2. **Format your data:**
   - Convert timestamps to ISO 8601 format with UTC timezone
   - Organize by appliance/circuit name
   - Ensure no missing intervals (HEMA requires complete sequences)

3. **Set thresholds:**
   - Analyze your consumption patterns to determine on/off thresholds
   - Start conservative and adjust based on HEMA's analysis results

4. **Verify rates:**
   - Use your actual electric bill's rate schedule
   - Include all time-of-use periods from your utility

5. **Place in data/ directory:**
   ```bash
   # Option A: Replace the existing files
   cp my_energy_data.csv data/home_power/energy_use_data_XXXX.csv
   cp my_thresholds.csv data/home_power/appliance_thresholds_XXXX.csv
   cp my_rates.csv data/utility_rate/utility_rate_XXX.csv

   # Option B: Keep samples and create new directory
   mkdir data/samples/my_home
   cp my_energy_data.csv data/samples/my_home/
   ```

## Notes

- The sample data provided here is **synthetic and realistic** but not from an actual home
- Power values are representative of typical household appliances
- For production analysis, replace with your actual home energy data
- HEMA's Analysis Agent works best with at least 30 days of data for meaningful patterns
- For seasonal analysis (e.g., comparing summer AC usage), include full season data

## Threshold File Behavior

### Works Without Thresholds File ✅

HEMA's evaluation framework and all tools work correctly **without** appliance thresholds:

```python
# Evaluation runs fine without thresholds
python -m evaluation.run_experiment --persona confused_newcomer --scenario understand_utility_rate

# Even without data/home_power/appliance_thresholds_sample.csv file
```

**What happens when thresholds are missing:**
1. System logs a warning (not an error)
2. Tools use default 0.01 kW threshold for all appliances
3. Energy analysis continues normally with aggregated/total consumption metrics
4. Evaluation metrics are calculated successfully

**For Evaluation:**
- The 23 evaluation metrics don't depend on threshold accuracy
- Metrics like "factual accuracy", "user questions", "response quality" are independent of thresholds
- Appliance frequency analysis would use default thresholds (still valid, just less precise)

### Recommended: Provide Thresholds for Better Results 🎯

When thresholds ARE provided:
- Appliance-specific analysis is more accurate
- Standby power filtering works better
- Frequency detection is more precise
- Users get better appliance-level insights

**Testing approach:**
1. Test without thresholds first → validates core functionality
2. Add thresholds file → improves appliance-level analysis accuracy
3. Compare results to see the difference

## Data Privacy

- These samples contain no real household data
- If using your own data, consider privacy implications before sharing
- Pecan Street dataset (used in manuscript) contains real data with consent
