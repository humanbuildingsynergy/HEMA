# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# agents/tools/knowledge_tools/knowledge_base.py
"""Knowledge base tool for the Knowledge Agent - handles theoretical Q&A about energy."""
from langchain_core.tools import tool
from utils.logger import setup_logger

logger = setup_logger()

# Energy knowledge base - can be expanded or replaced with RAG
ENERGY_KNOWLEDGE_BASE = {
    "time_of_use": """
**Time-of-Use (TOU) Pricing**

Time-of-use pricing is an electricity rate structure where the price per kWh varies based on the time of day:

- **Peak hours**: Highest rates, typically weekday afternoons/evenings (e.g., 2-7 PM)
- **Off-peak hours**: Lowest rates, typically nights and weekends
- **Partial-peak/Shoulder**: Mid-level rates between peak and off-peak

**Benefits of TOU:**
- Incentivizes shifting usage to off-peak hours
- Reduces strain on the electrical grid during peak demand
- Can lower electricity bills if you shift usage strategically

**Tips for TOU savings:**
1. Run dishwashers, laundry after 9 PM
2. Pre-cool your home before peak hours
3. Use timers for high-consumption appliances
4. Charge EVs overnight
""",
    "heat_pump": """
**Heat Pumps**

A heat pump is an energy-efficient alternative to traditional HVAC systems that transfers heat rather than generating it.

**How it works:**
- In winter: Extracts heat from outside air/ground and moves it inside
- In summer: Works like an AC, moving heat from inside to outside

**Types:**
1. **Air-source**: Most common, uses outdoor air
2. **Ground-source (geothermal)**: Uses stable ground temperature, more efficient
3. **Mini-splits**: Ductless systems for specific zones

**Efficiency:**
- COP (Coefficient of Performance): 2-4x more efficient than electric resistance heating
- Works well in mild climates; may need backup heat in extreme cold

**Benefits:**
- Lower operating costs than gas/electric furnaces
- Both heating and cooling in one system
- Reduces carbon footprint
""",
    "solar": """
**Solar Energy for Homes**

Rooftop solar panels convert sunlight into electricity for your home.

**Key components:**
1. **Solar panels**: Convert sunlight to DC electricity
2. **Inverter**: Converts DC to AC for home use
3. **Net meter**: Tracks energy sent to/from grid
4. **Battery (optional)**: Stores excess energy

**Net metering:**
- Excess solar energy is sent to the grid
- You receive credits on your electricity bill
- Credits offset nighttime/cloudy day usage

**Considerations:**
- Roof orientation and shading affect output
- Upfront cost vs. long-term savings
- Local incentives and tax credits
- Utility buyback rates vary
""",
    "energy_efficiency": """
**Home Energy Efficiency**

Improving energy efficiency reduces consumption and costs without sacrificing comfort.

**High-impact improvements:**
1. **Insulation**: Attic, walls, floors
2. **Air sealing**: Weatherstripping, caulking
3. **Windows**: Double/triple pane, low-E coating
4. **HVAC maintenance**: Regular filter changes, annual tune-ups

**Appliance efficiency:**
- Look for ENERGY STAR certification
- Compare EnergyGuide labels
- Consider lifecycle costs, not just purchase price

**Behavioral changes:**
- Adjust thermostat (68°F winter, 78°F summer)
- Use natural lighting when possible
- Unplug phantom loads (standby power)
- Use cold water for laundry

**Energy audits:**
- Professional audits identify specific opportunities
- Many utilities offer free or subsidized audits
""",
    "demand_response": """
**Demand Response Programs**

Demand response (DR) programs incentivize reducing electricity usage during peak demand periods.

**How it works:**
1. Utility sends signal during high-demand events
2. Participants reduce usage temporarily
3. Participants receive bill credits or incentives

**Types of programs:**
- **Direct load control**: Utility cycles your AC/water heater
- **Time-of-use rates**: Different prices at different times
- **Critical peak pricing**: Very high rates during grid emergencies
- **Peak rewards**: Credits for reducing usage on peak days

**Smart devices for DR:**
- Smart thermostats (Nest, Ecobee)
- Smart water heaters
- EV chargers with demand response capability

**Benefits:**
- Lower electricity bills
- Helps prevent grid blackouts
- Supports renewable energy integration
""",
    "phantom_load": """
**Phantom Loads (Standby Power)**

Phantom load is electricity consumed by devices when they're turned off but still plugged in.

**Common phantom loads:**
- TV and entertainment systems: 5-30W
- Computer and monitor: 5-20W
- Phone/laptop chargers: 1-5W
- Microwave (clock display): 2-5W
- Gaming consoles: 1-25W

**Impact:**
- Average home: 5-10% of electricity bill
- Can be 50+ watts continuous (over 400 kWh/year)

**Solutions:**
1. **Smart power strips**: Cut power to multiple devices
2. **Unplug chargers** when not in use
3. **Enable power-saving modes** on electronics
4. **Use outlet timers** for devices with standby modes

**Measuring phantom loads:**
- Use a plug-in energy monitor (Kill-A-Watt)
- Smart plugs with energy monitoring
"""
}


@tool
def energy_knowledge(topic: str) -> str:
    """
    Get information about energy concepts, technologies, and best practices.

    Use this tool to answer theoretical questions about energy topics like:
    - Time-of-use pricing
    - Heat pumps
    - Solar energy
    - Energy efficiency
    - Demand response programs
    - Phantom loads / standby power

    Args:
        topic: The energy topic to get information about. Examples:
               'time_of_use', 'heat_pump', 'solar', 'energy_efficiency',
               'demand_response', 'phantom_load'

    Returns:
        Detailed information about the requested energy topic.
    """
    logger.info(f"Knowledge query for topic: {topic}")

    # Normalize topic
    topic_lower = topic.lower().replace(" ", "_").replace("-", "_")

    # Direct match
    if topic_lower in ENERGY_KNOWLEDGE_BASE:
        return ENERGY_KNOWLEDGE_BASE[topic_lower]

    # Fuzzy matching
    topic_keywords = {
        "time_of_use": ["tou", "time", "peak", "off_peak", "rate", "pricing"],
        "heat_pump": ["heat", "pump", "hvac", "heating", "cooling", "geothermal"],
        "solar": ["solar", "pv", "photovoltaic", "panel", "net_meter"],
        "energy_efficiency": ["efficiency", "efficient", "save", "saving", "reduce", "insulation"],
        "demand_response": ["demand", "response", "dr", "grid", "peak_shaving"],
        "phantom_load": ["phantom", "standby", "vampire", "idle", "power_strip"],
    }

    for key, keywords in topic_keywords.items():
        if any(kw in topic_lower for kw in keywords):
            return ENERGY_KNOWLEDGE_BASE[key]

    # No match found - provide available topics
    available = ", ".join(ENERGY_KNOWLEDGE_BASE.keys())
    return f"""I don't have specific information about '{topic}' in my knowledge base.

**Available topics:**
{available}

You can ask about any of these topics, or rephrase your question.

For questions about your specific energy data, please use the analysis tools instead."""
