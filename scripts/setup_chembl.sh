#!/bin/bash
set -e

# Configuration
DB_CONTAINER="lab-postgres"
DB_USER="labuser"
DB_NAME="lab_db"
DEFAULT_SCHEMA="chembl_36"

# Check arguments
DUMP_FILE="$1"
SCHEMA_NAME="${2:-$DEFAULT_SCHEMA}"

if [ -z "$DUMP_FILE" ]; then
    # Try to find a .dmp or .sql file in the current directory
    FOUND_FILES=$(ls *.dmp *.sql 2>/dev/null | head -n 1)
    
    if [ -n "$FOUND_FILES" ]; then
        DUMP_FILE="$FOUND_FILES"
        echo "⚠️  No file argument provided. Auto-detected: $DUMP_FILE"
    else
        echo "❌ Error: No dump file specified and none found in current directory."
        echo "Usage: make setup-chembl FILE=chembl_36.dmp"
        exit 1
    fi
fi

if [ ! -f "$DUMP_FILE" ]; then
    echo "❌ Error: File '$DUMP_FILE' not found!"
    exit 1
fi

echo "🚀 Starting ChEMBL setup..."
echo "📂 File: $DUMP_FILE"
echo "🗄️  Schema: $SCHEMA_NAME"

# Reset schema
echo "♻️  Resetting schema '$SCHEMA_NAME'..."
docker exec -i $DB_CONTAINER psql -U $DB_USER -d $DB_NAME -c "DROP SCHEMA IF EXISTS $SCHEMA_NAME CASCADE;"
docker exec -i $DB_CONTAINER psql -U $DB_USER -d $DB_NAME -c "CREATE SCHEMA $SCHEMA_NAME;"

# Import data
echo "📥 Importing data (this may take a while)..."
# Determine file type and import method
if [[ "$DUMP_FILE" == *.sql ]]; then
    echo "📄 Detected plain SQL file. Using psql..."
    docker exec -i $DB_CONTAINER psql -U $DB_USER -d $DB_NAME -c "SET search_path TO $SCHEMA_NAME;" -f - < "$DUMP_FILE"
else
    echo "📦 Detected custom dump format. Using pg_restore..."
    
    # Strategy: ChEMBL dumps are hardcoded to 'public' schema. 
    # We must import to public, then rename public to our target schema.
    
    echo "⚠️  NOTE: This operation will temporarily wipe the 'public' schema to ensure clean import."
    
    # 1. Clear everything
    echo "♻️  Clearing schemas..."
    docker exec -i $DB_CONTAINER psql -U $DB_USER -d $DB_NAME -c "DROP SCHEMA IF EXISTS $SCHEMA_NAME CASCADE;"
    docker exec -i $DB_CONTAINER psql -U $DB_USER -d $DB_NAME -c "DROP SCHEMA IF EXISTS public CASCADE;"
    docker exec -i $DB_CONTAINER psql -U $DB_USER -d $DB_NAME -c "CREATE SCHEMA public;"
    
    # 2. Restore to public
    echo "📥 Restoring to temporary public schema..."
    docker exec -i $DB_CONTAINER pg_restore --username $DB_USER --dbname $DB_NAME --no-owner --role=$DB_USER < "$DUMP_FILE" || {
        echo "⚠️  pg_restore finished with warnings (usually safe)"
    }
    
    # 3. Rename public -> target
    echo "🔄 Moving 'public' schema to '$SCHEMA_NAME'..."
    docker exec -i $DB_CONTAINER psql -U $DB_USER -d $DB_NAME -c "ALTER SCHEMA public RENAME TO $SCHEMA_NAME;"
    
    # 4. Restore public
    docker exec -i $DB_CONTAINER psql -U $DB_USER -d $DB_NAME -c "CREATE SCHEMA public;"
fi

# Update search path
echo "🔄 Updating default search path..."
docker exec -i $DB_CONTAINER psql -U $DB_USER -d $DB_NAME -c "ALTER DATABASE $DB_NAME SET search_path TO \"$SCHEMA_NAME\", public;"

echo "✅ ChEMBL setup complete!"
echo "To verify: docker exec -it $DB_CONTAINER psql -U $DB_USER -d $DB_NAME -c 'SELECT count(*) FROM $SCHEMA_NAME.target_dictionary;'"
