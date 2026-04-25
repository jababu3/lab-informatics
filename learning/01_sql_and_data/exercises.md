# Exercises: SQL Queries

Work through these exercises in your preferred SQL client. Writing and running the queries yourself is more effective than reading solutions.

## Part 1: Single-Table Queries (SELECT, WHERE)

### Exercise 1.1 — Look Up a Compound

Write a query that returns the `chembl_id`, `pref_name`, and `molregno` for the compound **Imatinib**.

*Table:* `molecule_dictionary`

### Exercise 1.2 — Count Targets for an Organism

How many biological targets in ChEMBL are associated with the malaria parasite **Plasmodium falciparum**?

*Table:* `target_dictionary`. Use `COUNT()`.

### Exercise 1.3 — Retrieve a Structure

Using the `molregno` you found for Imatinib in Exercise 1.1, retrieve its canonical SMILES string.

*Table:* `compound_structures`

---

## Part 2: Filtering and Sorting (WHERE, ORDER BY, LIMIT)

### Exercise 2.1 — Heavy Molecules

Return the 10 compounds with the highest monoisotopic molecular weight (`mw_monoisotopic`), restricted to those above 500 Da. Order the results descending by weight.

*Table:* `compound_properties`

### Exercise 2.2 — Potent IC50 Values

Find experimental activities where `standard_type = 'IC50'` and `standard_value < 100` (nM). Limit the output to 50 rows so you do not pull the entire table into memory.

*Table:* `activities`

---

## Part 3: Multi-Table Queries (JOIN)

### Exercise 3.1 — Names to Structures

Write a single query that returns the name (`pref_name`), ChEMBL ID, and canonical SMILES for **Imatinib**, **Aspirin**, and **Caffeine**.

*Approach:* `INNER JOIN` between `molecule_dictionary` and `compound_structures` on `molregno`. Filter with `WHERE pref_name IN (...)`.

### Exercise 3.2 — Target-Based Activity Search

You are investigating the enzyme **Cyclooxygenase-2** (COX-2). Find all compounds with an IC50 below 50 nM against this target. Your result set should include the compound name, target name, and IC50 value.

*Approach:*
1. Find the `tid` for Cyclooxygenase-2 in `target_dictionary`.
2. Join `activities` to both `molecule_dictionary` (on `molregno`) and `target_dictionary` (on `tid`).
3. Filter on the target's `tid` and the IC50 threshold.

---

## Solutions

If you get stuck, reference implementations are in the [solutions directory](./solutions/).
