# Device Configuration Files

This directory contains smart home device configurations for the Control Agent.

## Files

### `demo_home_devices.json` (Default)

Complete smart home device configuration with 14 devices configured for the evaluation framework.

**Included Devices:**
- **Climate Control**: HVAC system with scheduling and automation
- **Hot Water**: Electric water heater with vacation mode and scheduling
- **Transportation**: EV charger with smart scheduling for off-peak charging
- **Recreation**: Pool pump with variable speed and automation
- **Appliances**: Washing machine, dishwasher, dryer, cooktop
- **Kitchen**: Ovens, microwave, refrigerator
- **Solar**: Solar PV system with production monitoring
- **Garbage Disposal**: Manual operation (not smart-enabled)

**Features:**
- 14 smart-enabled devices with realistic configurations
- 5 automation rules for TOU optimization, demand response, and solar integration
- Device groups for coordinated control
- Detailed current state and control actions for each device
- Scheduling capabilities for HVAC, water heater, EV charger, and pool pump

**Used By:**
- Control Agent evaluation scenarios (thermostat_adjustment, vacation_preparation)
- Device status and control testing
- Automation rule evaluation

## Device Configuration Structure

Each device includes:

```json
{
  "device_id": "unique_identifier",
  "display_name": "User-friendly name",
  "device_type": "device_type",
  "manufacturer": "Manufacturer",
  "model": "Model number",
  "smart_enabled": true,
  "connection_status": "online",
  "capabilities": ["list", "of", "capabilities"],
  "current_state": {
    "key": "value"
  },
  "settings": {
    "constraints": "and",
    "valid": "ranges"
  },
  "control_actions": [
    {
      "action": "action_name",
      "params": ["param1", "param2"],
      "description": "What this action does"
    }
  ]
}
```

## Adding Your Own Device Configuration

To use a custom device configuration:

1. Create a new JSON file in this directory (e.g., `my_home_devices.json`)
2. Follow the structure above for each device
3. Update the default in `agents/tools/control_tools/device_state.py`:
   ```python
   DEFAULT_DEVICE_CONFIG = "data/device_config/my_home_devices.json"
   ```

## Device Types Supported

- `hvac` - Heating/cooling systems
- `water_heater` - Hot water systems
- `ev_charger` - Electric vehicle chargers
- `washing_machine` - Laundry appliances
- `dishwasher` - Kitchen dishwasher
- `clothes_dryer` - Dryer
- `cooktop` - Cooking surface
- `oven` - Cooking oven
- `refrigerator` - Refrigeration
- `pool_pump` - Pool equipment
- `solar_inverter` - Solar PV system
- `garbage_disposal` - Waste disposal
- `microwave` - Microwave oven

## Notes

- This is sample data for demonstration and evaluation purposes
- Real implementations would connect to actual device APIs (Home Assistant, SmartThings, etc.)
- Device states are simulated in-memory and do not persist between runs
- For production use, integrate with MCP (Model Context Protocol) server or device-specific APIs
