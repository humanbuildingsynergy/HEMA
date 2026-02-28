# HEMA - Home Energy Management Assistant

**An LLM-based Multi-Agent System for Home Energy Management**

A multi-agent conversational AI system for home energy management, built with LangGraph and FastAPI.

## Overview

HEMA helps homeowners understand and optimize their energy consumption through:
- **Energy Analysis**: Load and analyze appliance-level consumption data
- **Knowledge Base**: Answer questions about energy concepts, technologies, and best practices
- **Device Control**: Manage smart home devices (thermostat, EV charger, etc.)

## Architecture

### Multi-Agent System

The system uses a hierarchical multi-agent architecture with LLM-based query classification:

```
User Query
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│                    LLM Classifier                            │
│  (Semantic understanding with cascade fallback)              │
└─────────────────────────────────────────────────────────────┘
    │
    ├─► Analysis Agent     → Energy data analysis & recommendations
    ├─► Knowledge Agent    → Theoretical Q&A about energy topics
    ├─► Control Agent      → Smart device management (simulated)
    └─► Orchestrator       → General conversation & help
```

### Specialized Agents

| Agent | Responsibilities | Tools (count) |
|-------|-----------------|---------------|
| **Analysis Agent** | Data loading, consumption analysis, appliance breakdown, TOU/solar analysis, recommendations | 18 tools: `load_energy_data`, `analyze_consumption`, `analyze_appliances`, `analyze_utility_rate`, `query_energy_data`, `compare_energy_periods`, `analyze_energy_period`, `analyze_peak_hours`, `compare_weekday_weekend`, `calculate_rolling_average`, `analyze_usage_frequency`, `analyze_usage_variability`, `analyze_solar_availability`, `analyze_solar_alignment`, `list_available_data`, `get_tracked_appliances`, `get_utility_rate`, `get_analysis_summary` |
| **Knowledge Agent** | Energy concepts, weather, rebates, RAG document search | 8 tools: `search_energy_documents`, `get_knowledge_base_status`, `energy_knowledge`, `get_current_weather`, `get_weather_forecast`, `get_weather_energy_impact`, `get_historical_weather`, `get_user_context` |
| **Control Agent** | Device discovery, control, scheduling, energy tracking | 10 tools: `get_device_list`, `get_device_status`, `get_available_actions`, `control_device`, `schedule_device_action`, `get_automation_rules`, `get_device_energy`, `get_all_devices_energy`, `get_utility_rate`, `get_current_weather` |
| **Fallback Handler** | Greetings, help requests, general conversation | - |

### LLM Providers

The system supports multiple LLM providers with automatic fallback:

1. **Primary**: OpenAI (gpt-4o-mini)
2. **Fallback 1**: Ollama (local, llama3.1)
3. **Fallback 2**: Google (gemini-1.5-flash)
4. **Fallback 3**: Anthropic (claude-3-haiku)

If the primary LLM fails, the system automatically tries the next provider in the cascade.

## Project Structure

```
HEMA/
├── agents/
│   ├── graph/                    # LangGraph implementation
│   │   ├── builder.py            # Graph construction
│   │   ├── self_consistency_classifier.py  # SC-CoT query routing
│   │   ├── routing.py            # Agent routing logic
│   │   ├── nodes.py              # Agent node factory
│   │   └── state.py              # State schema
│   ├── prompts/                  # System prompts for agents
│   │   ├── _common.py            # Shared prompt sections
│   │   ├── analysis_prompt.py
│   │   ├── knowledge_prompt.py
│   │   ├── control_prompt.py
│   │   └── fallback_prompt.py
│   ├── specialized/              # ReAct agents
│   │   ├── analysis_agent.py
│   │   ├── knowledge_agent.py
│   │   └── control_agent.py
│   └── tools/                    # Agent tools (organized by agent)
│       ├── analysis_tools/       # 18 tools
│       ├── knowledge_tools/      # 8 tools (includes RAG)
│       ├── control_tools/        # 10 tools
│       └── common/               # Shared utilities
├── api/                          # FastAPI backend
│   └── routes/
├── frontend/                     # React chat interface
├── config/
│   ├── config.py                 # LLM and data configuration
│   └── llm_factory.py            # Multi-provider LLM factory
├── core/                         # Framework-agnostic business logic
│   ├── analysis/
│   ├── data/
│   └── weather/
├── evaluation/                   # LLM-as-user evaluation framework
│   ├── config/                   # Personas and scenarios
│   ├── metrics/                  # 23 objective metrics
│   ├── comparison/               # HEMA vs vanilla LLM comparison
│   ├── run_experiment.py         # Main evaluation entry point
│   └── results/                  # Output directory (gitignored)
├── data/
│   ├── home_power/               # Energy consumption CSVs
│   ├── utility_rate/             # TOU rate CSVs
│   ├── device_config/            # Smart device configurations
│   └── knowledge_base/           # Public energy documents for RAG
├── main.py                       # CLI entry point
├── run_api.py                    # API server entry point
└── requirements.txt
```

## Installation

### Prerequisites

- Python 3.10+
- Node.js 18+ (for frontend)
- API key for at least one LLM provider (OpenAI recommended)

### Backend Setup

```bash
# Clone the repository
git clone https://github.com/humanbuildingsynergy/HEMA.git
cd HEMA

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API key(s)
```

### Frontend Setup

```bash
cd frontend
npm install
```

## Configuration

### LLM Provider

Edit `config/config.py` to configure your LLM provider:

```python
# Primary provider (default: OpenAI)
LLM_PROVIDER: LLMProvider = LLMProvider.OPENAI

# Available options:
# - LLMProvider.OPENAI     (requires OPENAI_API_KEY)
# - LLMProvider.OLLAMA     (local, no API key required)
# - LLMProvider.GOOGLE     (requires GOOGLE_API_KEY)
# - LLMProvider.ANTHROPIC  (requires ANTHROPIC_API_KEY)
```

### Environment Variables

For cloud LLM providers, set the appropriate API keys:

```bash
export OPENAI_API_KEY="your-openai-key"
export GOOGLE_API_KEY="your-google-key"
export ANTHROPIC_API_KEY="your-anthropic-key"
```

### Data Files

HEMA comes with sample energy data pre-configured for immediate use:

```python
# Default data files (sample data - 24 hours)
DEFAULT_ENERGY_FILE = "data/home_power/energy_data_sample.csv"
DEFAULT_RATE_FILE = "data/utility_rate/utility_rate_sample.csv"
DEFAULT_THRESHOLDS_FILE = "data/home_power/appliance_thresholds_sample.csv"
```

**Using Your Own Data:**

To use your own energy data, replace the files in `data/home_power/` and `data/utility_rate/` with your data. See [data/DATA_FORMAT.md](data/DATA_FORMAT.md) for the required format and structure.

## Quick Start (5 minutes)

Get HEMA running immediately with sample data, no configuration needed:

```bash
# 1. Start the backend (uses sample data by default)
python run_api.py

# 2. In another terminal, start the frontend
cd frontend && npm run dev

# 3. Open browser to http://localhost:3000
# Try: "What are my top energy consumers?"
#      "Show me my energy usage patterns"
#      "How can I reduce peak hour consumption?"
```

**That's it!** HEMA is ready to use with sample data. See [data/DATA_FORMAT.md](data/DATA_FORMAT.md) to use your own energy data.

## Running the Application

### Option 1: Full Stack (Frontend + Backend)

**Terminal 1 - Start Backend:**
```bash
cd HEMA
python run_api.py
```
Backend runs at: `http://localhost:8000`

**Terminal 2 - Start Frontend:**
```bash
cd HEMA/frontend
npm run dev
```
Frontend runs at: `http://localhost:3000`

Open your browser to `http://localhost:3000` to use the chat interface.

### Option 2: CLI Mode

For quick testing without the web interface:

```bash
# Interactive mode
python main.py --interactive

# Demo mode (runs test queries)
python main.py
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/chat` | POST | Send a message and get a response |
| `/api/session/{id}/history` | GET | Get conversation history |
| `/api/session/{id}/profile` | GET | Get user profile |
| `/api/data/files` | GET | List available data files |
| `/api/health` | GET | Health check |

## Usage Examples

### Chat Interface

The web interface provides a modern chat experience similar to ChatGPT/Claude:
- Dark/light mode toggle
- Session management (multiple conversations)
- Markdown rendering for responses
- Suggestion buttons for common queries

### Example Queries

**Analysis:**
- "What appliances are we tracking?"
- "Load my energy data and analyze consumption"
- "Which appliances use the most energy?"
- "Give me recommendations to reduce my bill"

**Knowledge:**
- "What is time-of-use pricing?"
- "How do heat pumps work?"
- "Tips for reducing phantom loads"

**Control:**
- "What's the thermostat set to?"
- "Set temperature to 72 degrees"
- "Schedule the EV to charge at midnight"

## Data

HEMA is designed to work with appliance-level home energy consumption data. The repository does **not** include proprietary household data, allowing you to use your own data sources.

### ⚠️ Sample Data is Synthetic

**All included data files are synthetic and not from real households:**
- `data/home_power/energy_data_sample.csv` — Generated demonstration data
- `data/utility_rate/utility_rate_sample.csv` — Representative rate structure
- For real analysis, use your own energy data or academic datasets

### Supported Data Sources

HEMA requires **appliance-level** energy consumption data (not whole-home smart meter data):

- **[Pecan Street Dataport](https://www.pecanstreet.org/dataport/)** - Academic access to appliance-level consumption data (recommended)
- **Home energy monitors** - Devices that provide per-appliance breakdowns (e.g., Sense, Emporia Vue)
- **Utility-provided data** - Some utilities offer appliance-level consumption exports

### Data Format

Energy data CSV should have:
- `local_15min`: Timestamp column (or similar datetime format)
- Appliance columns: Power consumption in kW
  - Examples: `HVAC`, `Refrigerator`, `Electric vehicle charger`, `Water heater`, `Dryer`, etc.

### Setting Up Your Data

1. Obtain energy data from your chosen source (Pecan Street, utility, or personal meter)
2. Save as CSV file
3. Place in `data/home_power/` directory
4. Update the file path in `config/config.py`:
   ```python
   DEFAULT_ENERGY_FILE = "data/home_power/your_data_file.csv"
   ```
5. (Optional) Create appliance thresholds file for better analysis:
   ```python
   DEFAULT_THRESHOLDS_FILE = "data/home_power/appliance_thresholds.csv"
   ```

### Privacy & Data Security

- HEMA is stateless and does not store user data
- All data processing happens locally in your environment
- No data is sent to external servers (except LLM API calls with cloud providers)
- See [SECURITY.md](SECURITY.md) for detailed security practices

## Knowledge Base & RAG

The Knowledge Agent uses **Retrieval-Augmented Generation (RAG)** to answer energy-related questions by retrieving relevant information from indexed documents.

### How It Works

```
User Query: "Are there rebates for heat pump water heaters?"
    ↓
Knowledge Agent receives query
    ↓
RAG Retriever searches indexed knowledge base documents
    ↓
Returns relevant sections with similarity scores
    ↓
Agent synthesizes response with retrieved information
```

### Knowledge Base Setup

HEMA includes sample knowledge base documents in `data/knowledge_base/`:

```
data/knowledge_base/
├── guides/                          # Energy efficiency guides
│   └── energy-saver-guide-2022.pdf
├── utility_rates/                   # Rate and pricing information
│   ├── austin_energy_rates.md
│   └── COA-Utilities-Rates-and-Fees.pdf
└── rebates/                         # Incentive programs
    └── austin_energy_rebates.md
```

### Adding Your Own Documents

To add custom energy documents to your knowledge base:

1. Create documents in `data/knowledge_base/` (PDF, markdown, or text)
2. On first Knowledge Agent query, the system will:
   - Load all documents from `data/knowledge_base/`
   - Create chunks for semantic search
   - Build vector embeddings using OpenAI's API
   - Save index to `data/vector_index/` (generated, not tracked in git)

### Configuration

RAG behavior can be customized in `agents/tools/knowledge_tools/rag/config.py`:

```python
RAG_CONFIG = RAGConfig(
    chunk_size=1000,           # Characters per chunk
    chunk_overlap=200,         # Overlap between chunks
    top_k=4,                   # Number of results to retrieve
    score_threshold=0.3,       # Minimum similarity score
)
```

### Vector Index Auto-Generation

- The vector index is **automatically generated on first use** (takes ~5 seconds)
- Index is cached in `data/vector_index/` for subsequent runs
- Not committed to git (treat as build artifact like `dist/` or `__pycache__/`)
- Rebuilds automatically if knowledge base documents change

### API Key Requirement

RAG requires an OpenAI API key for semantic embeddings:

```bash
# Set in .env or environment
export OPENAI_API_KEY="your-openai-api-key"
```

> **Note:** Embeddings use OpenAI's fast `text-embedding-3-small` model (~0.02 API cost per 1M tokens)

## Security

- API keys are read from environment variables (never committed to the repository)
- Energy data is processed locally; only LLM API calls are sent to cloud providers
- Use `.env.example` as a template; create your own `.env` file locally

For data privacy details, vulnerability reporting, and deployment guidelines, see [SECURITY.md](SECURITY.md).

## Evaluation & Reproducibility

HEMA includes a comprehensive evaluation framework to support the research claims in the manuscript. The framework uses the **LLM-as-Simulated-User methodology** with natural conversation flow to test system performance across diverse user scenarios.

### Core Evaluation

The evaluation framework includes:
- **7 core scenarios** covering Analysis, Control, and Knowledge agents
- **3 core personas** representing different user types (novice, intermediate, expert)
- **Natural wrap-up signal detection** - Users signal satisfaction naturally (e.g., "Thanks!", "Perfect!", "Got it!") rather than external goal evaluation, enabling realistic follow-up questions
- **23 objective metrics** from manuscript Table 1:
  - **Task Performance** (6): goal achievement, task completion, factual accuracy, error rates, factual claims
  - **Interaction Quality** (8): user questions, answer rate, response appropriateness, communication clarity
  - **Control Agent** (3): information gathering, action confirmation, explanation quality
  - **Device Scenarios** (3): target accuracy, scheduling correctness, mode correctness
  - **System Constraint** (1): constraint compliance rate
  - **System Diagnostics** (2): response latency, token usage

### Quick Start - Run an Evaluation

```bash
# Test HEMA with a specific scenario
python -m evaluation.run_experiment --persona confused_newcomer --scenario understand_utility_rate

# Compare with vanilla LLM baselines
python -m evaluation.run_experiment --persona tech_savvy_optimizer --scenario appliance_analysis --comparison-mode

# Run full evaluation matrix (all persona-scenario combinations)
python -m evaluation.run_experiment --full
```

### Evaluation Scenarios

**Analysis Agent** (Data analysis and recommendations):
- `understand_utility_rate` - TOU rate understanding
- `appliance_analysis` - Identify high-consuming appliances
- `peak_reduction_strategy` - Reduce peak hour consumption
- `multi_step_investigation` - Complex multi-angle analysis

**Control Agent** (Device management):
- `thermostat_adjustment` - Simple device control
- `vacation_preparation` - Multi-device coordination

**Knowledge Agent** (Information retrieval):
- `rebate_inquiry` - Retrieve rebate/incentive information

### Evaluation Metrics (23 Table 1 Metrics)

HEMA evaluation is based on **23 objective metrics** defined in manuscript Table 1:

| Category | Metrics | Count |
|----------|---------|-------|
| **Task Performance** | goal_achievement_rate, task_to_completion_rate, factual_accuracy, mean_error_percentage, factual_claims, accurate_claims | 6 |
| **Interaction Quality** | user_questions, answered_user_question_ratio, appropriate_data_backed_response, over_personalized_response, under_personalized_response, appropriate_general_response, technical_terms_explained, average_system_response_length | 8 |
| **Control Agent Process** | information_before_action_rate, action_confirmation_rate, action_explanation_rate | 3 |
| **Device Scenarios** | target_device_accuracy, schedule_correctness, mode_correctness | 3 |
| **System Compliance** | constraint_compliance_rate | 1 |
| **System Diagnostics** | response_latency, token_usage | 2 |

All metrics are **objective** (no subjective LLM judgment) and automatically computed from conversation transcripts.

### Evaluation Output

Results are saved as JSON files under `evaluation/results/` (gitignored). The directory structure depends on the run type:

| Run Type | Directory | Key Files |
|----------|-----------|-----------|
| Single experiment | `eval_run_{TIMESTAMP}/` | `structured_data_{TIMESTAMP}.json`, `test_report_{TIMESTAMP}.txt` |
| Multi-run | `multirun_{N}x_{TIMESTAMP}/` | `aggregate_summary_{TIMESTAMP}.json`, `individual_runs_{TIMESTAMP}.json` |
| Comparison | `comparison_{TIMESTAMP}/` | `runs/{SYSTEM}_{PERSONA}_{SCENARIO}_run{N}.json`, `comparison_summary.json` |
| Full matrix | `comparison_matrix_{TIMESTAMP}/` | `runs/`, `aggregated/`, `summary.json` |

Each JSON file contains:
- **Identifiers**: experiment ID, persona, scenario, timestamp
- **Task metrics**: goal achievement, turns to completion, efficiency score
- **System metrics**: latency, token counts, tool usage, error rates
- **Quality metrics**: QA rate, jargon explanation rate, communication scores
- **Conversation data**: full transcript with turn-by-turn details
- **Device state changes** (Control scenarios only): before/after states, verification results

You can override the default output directory with `--output-dir`:
```bash
python -m evaluation.run_experiment --persona confused_newcomer --scenario appliance_analysis --output-dir my_results/
```

### For More Details

See [evaluation/README.md](evaluation/README.md) for:
- Complete usage instructions
- Persona descriptions
- Scenario details
- Framework extension guide
- Research methodology

To reproduce manuscript results:
```bash
python -m evaluation.run_experiment --full --runs 5
```

This evaluates all persona-scenario combinations with 5 runs each for statistical rigor.

## Development

### Adding a New Agent

1. Create tools in `agents/tools/`
2. Create agent in `agents/specialized/`
3. Add routing in `agents/graph/classifier.py`
4. Register in `agents/graph/builder.py`

### Adding a New LLM Provider

1. Add provider to `LLMProvider` enum in `config/config.py`
2. Implement creation function in `config/llm_factory.py`
3. Add to `LLM_CASCADE` if desired

## Credit

Developed by Dr. [Wooyoung Jung](https://hubs.engr.arizona.edu/director.html) at the Human-Building Synergy Lab, University of Arizona.

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

## Citation

A journal article describing HEMA has been submitted to SoftwareX. Citation information will be added upon acceptance.

## Support & Contributing

- **Bug Reports**: Open a [GitHub Issue](https://github.com/humanbuildingsynergy/HEMA/issues)
- **Questions**: Open a [GitHub Discussion](https://github.com/humanbuildingsynergy/HEMA/discussions)
- **Contributing**: See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines
- **Maintainer**: Dr. Wooyoung Jung (wooyoung -at- arizona -dot- edu), Human-Building Synergy Lab, University of Arizona
