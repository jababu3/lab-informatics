# Concepts: Relational Models in Drug Discovery

## Why Relational Databases?

Pharmacological datasets have a natural many-to-many structure: one compound can be tested against many biological targets, and one target can be screened against thousands of compounds. Storing this data in flat files (spreadsheets, CSVs) forces redundant duplication — the compound's name, molecular weight, and structure must be copied onto every row where it appears. Any correction to a compound attribute then requires updating every duplicate, which is error-prone and does not scale.

**Relational Database Management Systems (RDBMS)** address this through normalization: each entity type is stored in its own table, and relationships between entities are maintained by shared key columns. This eliminates redundancy and allows the database engine to enforce referential integrity — for example, preventing an activity record from referencing a compound that does not exist.

## Core ChEMBL Tables

The full ChEMBL schema contains dozens of tables, but the majority of practical cheminformatics queries can be constructed from four:

### 1. `molecule_dictionary`

The primary registry of chemical entities.

| Column | Description |
|---|---|
| `molregno` | Internal integer ID (Primary Key) |
| `chembl_id` | Public identifier, e.g. `CHEMBL25` |
| `pref_name` | Common name, e.g. `ASPIRIN` |

### 2. `compound_structures`

Stores the structural representation of each registered molecule.

| Column | Description |
|---|---|
| `molregno` | Foreign key → `molecule_dictionary` |
| `canonical_smiles` | Line-notation string encoding the molecular graph, e.g. `CC(=O)OC1=CC=CC=C1C(=O)O` |
| `standard_inchi_key` | Fixed-length hash of the structure, useful for deduplication |

### 3. `target_dictionary`

Catalogs the biological targets — proteins, cell lines, organisms — used in experimental assays.

| Column | Description |
|---|---|
| `tid` | Internal Target ID (Primary Key) |
| `pref_name` | Target name, e.g. `Cyclooxygenase-1` |
| `organism` | Source species, e.g. `Homo sapiens` |

### 4. `activities`

Records experimental measurements. This is the junction table that links compounds to targets.

| Column | Description |
|---|---|
| `molregno` | Foreign key → compound |
| `tid` | Foreign key → target |
| `standard_type` | Measurement type: `IC50`, `Ki`, `EC50`, etc. |
| `standard_value` | Numeric result, e.g. `25.5` |
| `standard_units` | Unit of measurement, e.g. `nM` |

## SQL JOINs

Scientific questions typically span multiple tables. SQL `JOIN` operations combine rows from different tables based on shared keys.

**Example:** Retrieve the SMILES string for Aspirin.

The information lives in two separate tables — the name is in `molecule_dictionary` and the SMILES is in `compound_structures`. An `INNER JOIN` on `molregno` links them:

```sql
SELECT md.pref_name, cs.canonical_smiles
FROM molecule_dictionary md
INNER JOIN compound_structures cs ON md.molregno = cs.molregno
WHERE md.pref_name = 'ASPIRIN';
```

This normalized design lets the database handle millions of records without the consistency problems inherent in flat-file storage.

---

Proceed to [exercises.md](./exercises.md) to practice writing these queries.
