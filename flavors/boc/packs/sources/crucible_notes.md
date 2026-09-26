# CRUCIBLE: integration notes for PixelGoblin

Source: `/root/.claude/skills/synced/ef45a90d-.../crucible/` (read-only). DB: `build/db/crucible.db`
(schema in `build/db/schema.sql`, built by `build/db/populate.py`). I read it from a copy opened with
`?mode=ro`. The shipped `-wal` file is 0 bytes, so the `.db` alone holds everything.

## Tables (row counts)

| table | rows | key columns |
|---|---|---|
| `materials` | 39 | id, name, mat_class (metal/ceramic/polymer/composite/semiconductor/wood/stone/glass), density_kg_m3, youngs_modulus_gpa, yield_strength_mpa, tensile_strength_mpa, **hardness (TEXT, mixed scales)**, thermal_cond_w_mk, elec_resistivity_ohm_m, melting_k, specific_heat_j_kgk, poisson_ratio, notes |
| `elements` | 118 | z (PK), symbol, name, atomic_mass, period, group_num, block, category, phase_stp, valence_e, electronegativity, density_g_cm3, melting_k, boiling_k, oxidation_states, synthetic, notes |
| `compounds` | 38 | id, formula, name, common_name, molar_mass, state_stp, category, bonding, solubility, **density_g_cm3 / melting_k / boiling_k: NULL for every row** |
| `boc_bridge` | 16 | id, boc_material, boc_catalog (flora/fauna/fungi/ores/fish/special), crucible_material_id -> materials, crucible_element_z -> elements, dim_signature_id, grounding_mode ('grounded','partial','intentionally_ungrounded'), grounding_note |
| `adjacencies` | 18 | real_a_type/id, real_b_type/id, relation (constituent_of, governs, phase_of, appears_in) |
| `constants` | 21 | symbol, name, value, uncertainty, unit. Includes g0=9.80665, G, R, k_B, sigma (Stefan-Boltzmann), atm |
| `units` | 35 | name, symbol, si_factor, si_offset, dim_signature_id |
| `dim_signatures` | 27 | label, M L T I TH N J exponents, si_unit |
| `laws` | 33 | name, domain, equation, variables, statement, regime (validity envelope) |
| `engineering_systems` | 12 | name, domain, governing_laws, key_params, sandbox_module |
| `reactions` | 18 | equation, rxn_type, delta_h_kj |
| `particles` | 21 | Standard Model |
| `block_types` | 11 | code 0x20-0x2A (QRen wire block types) |
| `synergies` | 15 | name, domain_a, domain_b, effect |
| `provenance` | 2 | real_type, source ('sandbox:structural', ...), created_at, parameters JSON |

Data gaps that matter for a game:
- Elements: only about 30 of the 118 have density and melting point. Most transition metals are NULL, including Ti, Mn, Co, Mo, Os, Ir, Bi and Sb.
- Compounds carry no physical numbers. Water has no density row, so buoyancy needs rho_water from outside the DB, or from the materials table if someone adds it.
- **There is no colour, appearance or reflectance data anywhere.** tools/crucible_ramps.py is correct to author base colours by hand.

## Querying density / hardness / colour

```sql
-- density (kg/m^3) and melting point (K) of a material
SELECT name, mat_class, density_kg_m3, melting_k, hardness, elec_resistivity_ohm_m
FROM materials WHERE name = 'Bronze (Cu-Sn)';
-- element (g/cm^3 -> x1000 for kg/m^3)
SELECT symbol, density_g_cm3, melting_k FROM elements WHERE symbol = 'Fe';
-- a BoC name to its grounded numbers
SELECT b.boc_material, b.grounding_mode, m.name, m.density_kg_m3, e.symbol, e.density_g_cm3
FROM boc_bridge b LEFT JOIN materials m ON m.id = b.crucible_material_id
                  LEFT JOIN elements  e ON e.z  = b.crucible_element_z;
```

Hardness is free text with mixed scales: '6-7 Mohs', '~120 HB', '36 HRC', '~2800 HV', '~65 D', '-'.
Only 6 rows are in Mohs (granite, marble, both glasses, diamond, graphite). No conversion table exists.
The export parses only the Mohs strings and leaves the rest null (raw string is kept in `hardness_raw`).
Colour cannot be queried.

## Sandbox API (`build/sandbox/`, stdlib, float math)

Import as the package `sandbox` from `build/`. The DB path comes from env `CRUCIBLE_DB`, defaulting to `../db/crucible.db`.
**Warning:** `db.connect()` opens the DB read-write. `structural.axial_member` INSERTs a provenance row,
and so does any `record(...)` helper and `cli demo`. Point `CRUCIBLE_DB` at a copy, and never run these against the skill folder.
Every function is float-based. For PixelGoblin's integer runtime, use them at tool/bake time only, or port the formula to integer math.

| game need | function (signature) | law |
|---|---|---|
| carry weight / item mass | none built in. Compute mass = `density_kg_m3 * volume_m3`. Use `structural.material(name, conn=None) -> dict` (returns name, density_kg_m3, youngs_modulus_gpa, yield_strength_mpa, tensile_strength_mpa, poisson_ratio) | - |
| weight force | `mechanics.potential_energy(mass_kg, height_m, g=None)`; `constants.const('g0')` -> 9.80665 | PE = mgh |
| falling / thrown | `mechanics.kinematic_v(u, a, t)`, `mechanics.kinematic_s(u, a, t)`, `mechanics.projectile(v0, angle_deg, g=None) -> {range_m, max_height_m, flight_time_s, vx, vy}` | non-relativistic |
| impact damage proxy | `mechanics.kinetic_energy(mass_kg, v)`, `mechanics.momentum(mass_kg, v)` | KE = 1/2 mv^2 |
| buoyancy | **none** (no fluids module, no water density). Sink/float = compare density_kg_m3 against an external rho_water | - |
| beam / shelf / bridge strength | `structural.second_moment_rectangle(b, h)`, `second_moment_circle(d)`, `bending_stress(moment_nm, dist_to_fibre_m, I_m4)`, `factor_of_safety(strength_pa, applied_stress_pa)` | sigma = My/I |
| column / pillar collapse | `structural.euler_buckling(youngs_modulus_pa, I_m4, length_m, end_condition='pinned'\|'fixed-free'\|'fixed-fixed'\|'fixed-pinned') -> {P_cr_N, K, end_condition}` | Euler |
| rope / rod / chain link | `structural.axial_stress(force_n, area_m2)`, `axial_strain(stress_pa, E_pa)`, `axial_member(force_n, diameter_m, material_name, conn=None) -> {stress_MPa, strain, factor_of_safety_yield, ...}` (**writes provenance**) | Hooke |
| heating / smelting energy | `thermo.sensible_heat(mass_kg, specific_heat_j_kgk, dT_k)`, `thermo.material_specific_heat(name, conn=None)` (raises KeyError when NULL); melting point from `materials.melting_k` | Q = mc dT |
| furnace / engine efficiency | `thermo.carnot_efficiency(T_hot_k, T_cold_k)`, `conversion_efficiency(out_j, in_j)` | Carnot |
| alchemy / crafting yields | `chemistry.parse_formula(f) -> {el: n}`, `molar_mass(formula, conn=None)`, `moles(grams, formula)`, `limiting_reagent({formula: (grams, coeff)})`, `ph_strong(conc, kind='acid'\|'base')`, `ideal_gas(P=None, V=None, n=None, T=None)` | stoichiometry |
| lightning / circuits | `electrical.ohms_law(V=None, I=None, R=None)`, `series_resistance(*r)`, `parallel_resistance(*r)`, `dc_power(...)`, `rc_charge(V, R, C, t)`, `rc_discharge(V0, R, C, t)` | Ohm |
| glow colour of spells / lamps | `quantum.photon_energy_from_wavelength(m)`, `bohr_transition(n_i, n_f)` (gives wavelength, for example H-alpha 656 nm) | Planck / Bohr |
| units | `units.UnitEngine(db_path=None).q(value, symbol)` / `.to(qty, symbol)`; `Quantity` refuses to add mismatched dimensions | - |

CLI: `python3 -m sandbox.cli demo | molar F | ph c acid | gas P=? V= n= T= | ohm V= R= | beam F= d= mat="..." | photon nm= | bohr n1 n2`.

## The `intentionally_ungrounded` convention

- `boc_bridge.grounding_mode` takes one of three values:
  - `grounded`: real numbers apply.
  - `partial`: some properties are borrowed. Tin ore maps to bronze. Limestone maps to marble. Brain-Coral maps to alumina "props approximated". Quartz maps to soda-lime glass.
  - `intentionally_ungrounded`: fantasy stays fantasy.
- There are three ungrounded rows: **Mithril, Dragonbone, Ley-crystal**. All three have NULL material and element links.
- Design rule (MARK_DESIGN_DECISIONS, CALS_NAMESPACE [FLOOR]): "CRUCIBLE does **not** fabricate physics to make Mithril 'real.' Grounding that invents convenient numbers is not grounding." Ungrounded Reals are NADA_PROTECTED, meaning "real as fiction". They are kept, never "corrected" into real numbers.
- OQ-CRU-2 (open) proposes a richer `partial` contract: add a `grounded_properties` JSON column so that, for example, Mithril could borrow density or modulus while its existence stays fictional. This is not implemented.
- Implication for PixelGoblin: a fantasy material must carry an explicit ungrounded flag, and its numbers must be labelled AUTHORED. Do not back-fill them from CRUCIBLE and do not present them as CRUCIBLE-derived.
- The boc-aether docs (updates/documentation) extend the same rule: enchantment, cultivation BUILDUP/BEYOND_MASTER and "old magic" are all ungrounded.

## About the export (crucible_materials.json)

- Output: 99 materials (31 from `materials`, 54 from `elements`, 14 from `compounds`) plus all 16 `boc_bridge_rows`.
- Excluded:
  - the modern plastics and composites (ids 28-33, 35, 36)
  - gases and lanthanides
  - rare radioactives
  - acids, caustics and organics
- Every number comes from the DB. Derived fields, and how each was derived, are listed in `_meta.derived_fields`:
  - Mohs midpoint for ranges
  - resistivity class thresholds (<1e-5 conductor, matching crucible_ramps.py; <1e6 semiconductor)
  - element and compound density from g/cm3 x 1000
- `boc_bridge` per entry is a list of matching bridge rows, or null.
