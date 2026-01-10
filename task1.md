## Improvement 1 — Chemistry-aware experiment protocols (real lab workflows, not just “cycle N times”)

### What you have today
- You currently support `chemistry`, `c_rate`, `temperature_celsius`, `cycles`, plus arbitrary `custom_parameters`.
- If `cycles > 1`, you run a fixed “Discharge → Rest → Charge → CV Hold → Rest” pattern repeated `cycles` times.
- If `cycles == 1`, you run a single discharge with a coarse `t_eval` window.

This is already a solid demo, but Ionworks will care that the simulation matches **standard test plans** used by cell engineers.

### Upgrade goal
Make simulations reflect **real experiment protocols** engineers actually run:
- **Capacity / characterization**: CCCV charge + C/20 discharge (to establish baseline capacity & OCV)
- **Rate capability**: repeated discharges at different C-rates with rests
- **Drive-cycle / variable current**: time-varying current profile (e.g., pulses / WLTP-like)
- **Pulse Power / HPPC**: repeated current pulses at different SOC points with rests

### What to change (conceptually)
1. **Add an explicit “protocol” concept** to your simulation requests
   - Keep your existing API stable by interpreting a new key inside `custom_parameters` (e.g., `protocol_type`, `protocol_steps`, etc.).
   - Default stays close to what you already do, so nothing breaks.

2. **Make voltage limits chemistry-aware instead of hard-coded**
   - Right now your cycle protocol uses fixed cutoffs (e.g., 2.5V discharge cutoff and 4.2V charge ceiling).
   - Real workflows use cutoffs that are chemistry/cell dependent.
   - For “impress factor,” define a small “safe defaults” table per `chemistry` (LFP vs NMC/NCA/LCO), and allow overriding via `custom_parameters`.

3. **Always run through `Experiment` (even for one cycle)**
   - This unifies behavior, makes results more interpretable, and makes it easy to add protocols like HPPC and drive-cycle profiles.

4. **Return step segmentation + per-step metrics**
   - Instead of just time/voltage/current arrays, add:
     - step boundaries (index ranges)
     - per-step summary: average current, delivered Ah/Wh, end voltage, step duration
   - This mirrors how battery engineers analyze “what happened during each step,” not just the whole trace.


