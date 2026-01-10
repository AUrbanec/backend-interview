## Improvement 2 — Add thermal dynamics + safety signaling (beyond “ambient temperature”)

### What you have today
- You set `"Ambient temperature [K]"` from `temperature_celsius`.
- But the outputs you return are purely electrical (time/voltage/current, maybe discharge capacity).

In real battery simulation, temperature isn’t just a parameter — it’s an output and a constraint.

### Upgrade goal
Support “thermal-aware” simulations that answer questions engineers actually ask:
- “At this C-rate and ambient temp, what peak temperature does the cell hit?”
- “Does temperature runaway risk appear under aggressive pulses?”
- “How does cooling strength change performance and degradation risk?”

### What to change (conceptually)
1. **Add a thermal mode switch**
   - Use `custom_parameters` to opt into a thermal submodel (e.g., “lumped thermal” vs “isothermal”).
   - Default remains the current behavior so the simple demo still works.

2. **Introduce thermal boundary condition inputs**
   - You already accept `temperature_celsius` — extend with optional fields like:
     - cooling strength / heat transfer coefficient
     - external cooling temperature (could default to ambient)
   - Keep these as optional keys in `custom_parameters` to avoid schema churn.

3. **Return thermal outputs + safety annotations**
   - Add outputs that make the sim feel “engineering-grade”:
     - cell temperature over time
     - max temperature, time-above-threshold
     - heat generation proxy (if available)
   - Add “safety flags” in `results.summary`, e.g.:
     - `max_temp_exceeded: true/false`
     - `voltage_violation: true/false`
     - `events: [...]` (timestamped warnings)

4. **Tie progress reporting to experiment steps**
   - Right now progress jumps early to 10 and later to 100.
   - Thermal runs are heavier; step-level progress (based on protocol steps) will feel dramatically more “production.”

