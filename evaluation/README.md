# HEMA Evaluation Framework

This directory contains the evaluation framework for the HEMA (Home Energy Management Assistant) system. It implements the LLM-as-Simulated-User methodology described in the manuscript.

## Overview

The evaluation framework tests HEMA's performance across:
- **3 user personas** with varying technical levels (novice, intermediate, expert)
- **7 evaluation scenarios** covering Analysis, Control, and Knowledge agents
- **Multiple LLM systems** for comparative analysis (HEMA vs vanilla baselines)
- **Objective metrics only**: Three tiers of automatically-counted metrics (no subjective LLM judgment)

### Data Sources and Reproducibility

**This Public Evaluation Uses:**
- **Synthetic energy data** (`data/home_power/energy_data_sample.csv`)
- **LLM-simulated users** (not real people, following predefined personas)
- **Generic device configurations** (not tied to specific households)

**Manuscript Evaluation Used:**
- Real household data from **Pecan Street Dataport** with proper consent
- Published results cannot be exactly reproduced without access to Pecan Street data
- However, **methodology and relative performance** (HEMA vs baselines) are reproducible with synthetic data

**For Reproducibility:**
- Run the public evaluation to validate methodology and framework
- Compare relative performance: HEMA should outperform vanilla baselines
- Use your own energy data for production analysis

## Quick Start

### Prerequisites

Enable session logging (required for evaluation):

```bash
export HEMA_LOG_SESSIONS=true
# Or add to .env file
```

### Single Scenario

```bash
python -m evaluation.run_experiment --persona confused_newcomer --scenario understand_utility_rate
```

### Multiple Runs

```bash
python -m evaluation.run_experiment --persona tech_savvy_optimizer --scenario appliance_analysis --runs 5
```

### Compare with Baselines

```bash
python -m evaluation.run_experiment --persona tech_savvy_optimizer --scenario appliance_analysis --comparison-mode
```

### Full Matrix

```bash
# All personas x all scenarios
python -m evaluation.run_experiment --matrix

# Filtered matrix with multiple runs
python -m evaluation.run_experiment --matrix --personas confused_newcomer,tech_savvy_optimizer --scenarios appliance_analysis,understand_utility_rate --runs 5
```

### List Available Options

```bash
python -m evaluation.run_experiment --list-personas
python -m evaluation.run_experiment --list-scenarios
```

### Command-Line Options

```
--persona PERSONA_ID       Specific persona (default: confused_newcomer)
--scenario SCENARIO_ID     Specific scenario (default: understand_utility_rate)
--runs N                   Number of runs per combination (default: 1)
--matrix                   Run all persona x scenario combinations
--personas P1,P2           Filter personas for --matrix (default: all)
--scenarios S1,S2          Filter scenarios for --matrix (default: all)
--system {hema|vanilla|vanilla_structured|vanilla_structured_cot|all}
--comparison-mode          Compare HEMA against baselines
--list-personas            Show available personas
--list-scenarios           Show available scenarios
--output-dir DIRECTORY     Output directory (default: evaluation/results)
--validate                 Run validation tests
```

## Scenarios

The 7 scenarios provide comprehensive coverage of HEMA's capabilities:

### Analysis Agent Scenarios (4)

1. **understand_utility_rate** - Basic TOU rate understanding
   - Tests: Communication clarity with novice users
   - Evaluation: Factual accuracy on rate information

2. **appliance_analysis** - Identify high-consuming appliances
   - Tests: Data analysis and tool usage
   - Evaluation: Task effectiveness and factual accuracy

3. **peak_reduction_strategy** - Reduce consumption during peak hours
   - Tests: Complex reasoning and actionable recommendations
   - Evaluation: Communication quality, task effectiveness

4. **multi_step_investigation** - Complex multi-angle analysis
   - Tests: Chain-of-thought reasoning and integration
   - Evaluation: Full reasoning chain assessment

### Control Agent Scenarios (2)

5. **thermostat_adjustment** - Simple device control
   - Tests: Basic device state modification
   - Evaluation: Action correctness and explanation quality

6. **vacation_preparation** - Multi-device coordination
   - Tests: Complex multi-device orchestration
   - Evaluation: Coordination of multiple changes

### Knowledge Agent Scenario (1)

7. **rebate_inquiry** - Retrieve rebate information
   - Tests: RAG (Retrieval-Augmented Generation) capabilities
   - Evaluation: Relevance and completeness of knowledge

## Personas

| Persona | Level | Focus | What it Tests |
|---------|-------|-------|----------|
| **confused_newcomer** | Novice | Communication clarity | Can HEMA explain clearly without jargon? |
| **tech_savvy_optimizer** | Expert | Complex analysis | Can HEMA provide technical depth? |
| **budget_conscious_parent** | Intermediate | Practical advice | Does HEMA give actionable, feasible recommendations? |

*Additional personas (eco_conscious_renter, skeptical_senior) are available in git history for specialized research use cases.*

## Output

Results are saved to `evaluation/results/` (auto-generated, gitignored) with JSON format including:
- **Conversation transcript** - Complete LLM-simulated-user exchanges
- **23 Objective metrics** - All Table 1 metrics (see below)
- **Supporting data** - Raw extracted items (questions, responses, claims) for auditability

## Framework Components

### Directory Structure

```
evaluation/
├── run_experiment.py          # Main entry point
├── run_comparison.py          # Baseline comparison entry point
├── runners/                   # Conversation infrastructure
│   ├── conversation.py        # HEMA conversation runner
│   ├── simulated_user.py      # LLM-as-Simulated-User
│   ├── vanilla_conversation.py # Vanilla baseline runner
│   ├── vanilla_llm.py         # Vanilla LLM backends
│   ├── dataclasses.py         # ConversationTurn, ConversationRecord
│   └── conversation_monitor.py # Turn monitoring and wrap-up detection
├── evaluator/                 # Objective metrics computation
│   ├── evaluator.py           # Main evaluator (3-tier pipeline)
│   ├── objective_metrics.py   # Tier 1-3 metric computation
│   └── dataclasses.py         # ObjectiveMetrics, EvaluationResult
├── metrics/                   # Result formatting and verification
│   ├── experiment.py          # Experiment-level aggregation
│   ├── formatters.py          # Human-readable output
│   ├── control_process.py     # Control Agent process metrics
│   └── device_verification.py # Device state verification
├── data/                      # Data utilities
│   ├── ground_truth.py        # Ground truth extraction
│   └── household_metrics.py   # Household profile comparison
├── config/                    # Evaluation configuration
│   ├── personas.py            # 3 user persona definitions
│   └── scenarios.py           # 7 scenario definitions
├── comparison/                # Comparative analysis
│   └── runners.py             # Multi-system comparison runner
└── validation_tests/          # Framework self-tests
    └── runner.py              # Validation test suite
```

### Key Modules

- **runners/simulated_user.py** - LLM-as-Simulated-User implementation. Generates natural user queries based on personas and scenarios with controlled/random opening modes and natural wrap-up signal detection.

- **runners/conversation.py** - HEMA conversation runner and `run_full_experiment()` entry point. Manages multi-turn conversations with device state tracking for control scenarios.

- **evaluator/** - Three-tier objective metrics computation:
  - Tier 1: Direct counting (turns, questions, response length)
  - Tier 2: LLM extraction (factual claims, technical terms, response appropriateness)
  - Tier 3: Factual verification (claimed values vs ground truth)

- **runners/vanilla_llm.py** - Three vanilla LLM baselines:
  - `vanilla`: Raw CSV + minimal prompt
  - `vanilla_structured`: Structured data + minimal prompt
  - `vanilla_structured_cot`: Structured data + CoT reasoning

## Evaluation Metrics (Table 1: 23 Metrics)

The framework tracks **23 objective metrics** from manuscript Table 1:

### Task Performance (6 metrics)
1. **goal_achievement_rate** - % - Percentage of runs reaching completion
2. **task_to_completion_rate** - % - Success criteria met
3. **factual_accuracy** - % - Proportion of numerical claims with error ≤ 5%
4. **mean_error_percentage** - % - Average absolute percentage error across verified claims
5. **factual_claims** - Count - Total quantifiable claims extracted
6. **accurate_claims** - Count - Claims verified as accurate (error ≤ 5%)

### Interaction Quality (8 metrics)
7. **user_questions** - Count - Distinct questions asked during conversation
8. **answered_user_question_ratio** - % - User questions receiving direct answers
9. **appropriate_data_backed_response** - Count - Data questions answered with data
10. **over_personalized_response** - Count - General questions incorrectly using personal data
11. **under_personalized_response** - Count - Data questions answered with only generic info
12. **appropriate_general_response** - Count - General questions with appropriate context
13. **technical_terms_explained** - Count - Technical terms explicitly defined
14. **average_system_response_length** - Characters - Mean response length

### Control Agent Process (3 metrics)
15. **information_before_action_rate** - % - Control actions preceded by info gathering
16. **action_confirmation_rate** - % - Control actions followed by confirmation
17. **action_explanation_rate** - % - Control actions accompanied by explanation

### Target Device Scenarios (3 metrics)
18. **target_device_accuracy** - % - Device changes affecting intended target [Placeholder]
19. **schedule_correctness** - % - Scheduled actions following timing limits [Placeholder]
20. **mode_correctness** - % - Device control respecting mode constraints [Placeholder]

### System Constraint Compliance (1 metric)
21. **constraint_compliance_rate** - % - Valid temperature ranges and mode options [Placeholder]

### System Diagnostics (2 metrics)
22. **response_latency** - Seconds - Average response generation time
23. **token_usage** - Count - Total tokens consumed

**Note**: Metrics marked [Placeholder] require actual device state verification and currently return None.

## Research Methodology

The evaluation implements:

1. **LLM-as-Simulated-User**: Instead of recruiting human subjects, realistic user queries are generated using a capable LLM guided by persona and scenario prompts.

2. **Natural Wrap-Up Signal Detection**: Rather than external goal evaluation that terminates conversations prematurely, users naturally signal satisfaction through explicit gratitude and satisfaction expressions. This enables realistic follow-up questions, more accurate answered_user_question_ratio metrics, and conversation flow that matches actual user behavior.

3. **Self-Consistency Evaluation**: HEMA's output is evaluated using chain-of-thought reasoning and majority voting across multiple classifier runs.

4. **Multi-Dimensional Assessment**: Communication quality, task effectiveness, and factual accuracy are evaluated independently.

5. **Comparative Analysis**: Results are compared against vanilla LLM baselines to quantify the benefit of HEMA's multi-agent architecture.

## Extending the Framework

### Adding New Personas

1. Edit `config/personas.py`
2. Add a new `Persona` instance to the `PERSONAS` dictionary with: `id`, `description`, `background`, `technical_level`, `communication_style`, `typical_behaviors`, `constraints`
3. Test: `python -m evaluation.run_experiment --persona new_persona_id --list-scenarios`

### Adding New Scenarios

1. Edit `config/scenarios.py`
2. Add a new `Scenario` instance to the `SCENARIOS` dictionary with: `id`, `name`, `description`, `primary_goal`, `success_criteria`, `initial_context`, `opening_message`, `evaluation_dimensions`
3. For control scenarios: specify `expected_device_changes`
4. Test: `python -m evaluation.run_experiment --persona confused_newcomer --scenario new_scenario_id`

### Scenario Streamlining (v0.1.0)

The evaluation framework was streamlined to focus on 7 core scenarios that are sufficient for reproducing manuscript results, representative of all agent types, and manageable for public evaluation. Removed scenarios (weather_energy_impact, solar_consideration, hvac_optimization, energy_comparison, utility_rate_details, efficiency_upgrade_advice, ev_charging_schedule, device_status_check, water_heater_optimization, pool_pump_scheduling, demand_response_event, specific_date_query, appliance_time_cross) are available in git history and can be restored for more comprehensive evaluation.

## Citation

A journal article describing HEMA has been submitted to SoftwareX. Citation information will be added upon acceptance.

---

**Last Updated**: February 28, 2026
**Framework Version**: v0.1.0 - 23 Table 1 Metrics
**Maintained By**: Dr. Wooyoung Jung, Human-Building Synergy Lab, University of Arizona
