# Module 01: Data Structures & SQL

## Learning Objectives

After completing this module you should be able to:
1. Describe the relational schema used in chemical databases like ChEMBL.
2. Write SQL queries that extract and combine chemical and biological data across multiple tables.
3. Translate a scientific question (e.g., "which compounds inhibit COX-2 below 50 nM?") into a concrete SQL statement.
4. Navigate the core entity-relationship model that connects molecules, targets, and assay results.

## Prerequisites

- Docker and Docker Compose installed and running.
- Comfort with a command-line terminal.

## Environment Setup

Before writing queries you need to load the ChEMBL dataset into the local PostgreSQL container.

### Step 1: Download the ChEMBL Data

The compressed PostgreSQL dump is approximately 3 GB.

**Option A — Make (recommended)**

```bash
make setup-chembl
```

**Option B — Manual download**

1. Download `chembl_33_postgresql.tar.gz` from the [EBI FTP server](https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/releases/chembl_33/chembl_33_postgresql.tar.gz).
2. Place the archive in the repository root.

### Step 2: Connect to the Database

Once the container is running, PostgreSQL is available for connections.

**Command-line (psql)**

```bash
docker-compose exec postgres psql -U labuser -d lab_db
```
Type `\q` to exit.

**GUI client (recommended for exploration)**

Tools like DBeaver, TablePlus, or pgAdmin make it easier to browse schemas and iterate on queries. Connection parameters:

| Parameter | Value |
|---|---|
| Host | `localhost` |
| Port | `5432` |
| Database | `lab_db` |
| User | `labuser` |
| Password | See your `.env` file |

---

## Next Steps

Proceed to [concepts.md](./concepts.md) for a walkthrough of the core ChEMBL tables and how they relate to one another.
