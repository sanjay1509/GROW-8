#!/bin/sh
# Copies the files this package shares with the rest of the repository, so the
# package can be zipped and submitted on its own. The repository files stay the
# single source of truth: edit them, then run this script.
#
#   sh ENSF608-Final-Artifacts/sync.sh          refresh the copies
#   sh ENSF608-Final-Artifacts/sync.sh --check  only report copies that differ
set -eu

PKG=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$PKG/.." && pwd)

# source (relative to the repo root) -> copy (relative to this folder)
MAP="
docs/diagrams/ER-diagram.drawio.svg               01-conceptual-model/Conceptual-ERD-Part1.drawio.svg
docs/diagrams/ER-diagram-part2-reports.drawio.svg 01-conceptual-model/Conceptual-ERD-Part2-Reports.drawio.svg
docs/diagrams/GROW8-ER-Diagram.pdf                02-logical-model/Logical-ERD-and-Relational-Schema.pdf
docs/diagrams/GROW8-ER-Diagram.svg                02-logical-model/Logical-ERD.svg
docs/diagrams/GROW8-Relational-Schema.svg         02-logical-model/Relational-Schema.svg
docs/db/relational-schema.md                      02-logical-model/Relational-Schema.md
grow8-backend/db/init/001_schema.sql              04-implementation/01_create_schema.sql
grow8-backend/db/init/002_seed.sql                04-implementation/02_populate_reference_and_core_data.sql
grow8-backend/db/init/004_seed_workflow.sql       04-implementation/03_populate_workflow_history.sql
docs/db/test-report.md                            06-testing/Database-Test-Report.md
docs/db/relationship-validation.md                06-testing/Relationship-Validation.md
docs/db/data-dictionary.md                        07-documentation/Data-Dictionary.md
"

status=0
while read -r src dst; do
    [ -z "$src" ] && continue
    if [ "${1:-}" = "--check" ]; then
        if ! cmp -s "$ROOT/$src" "$PKG/$dst"; then
            echo "out of date: $dst (source: $src)"
            status=1
        fi
    else
        cp "$ROOT/$src" "$PKG/$dst"
        echo "copied $src -> $dst"
    fi
done <<EOF_MAP
$MAP
EOF_MAP

[ "${1:-}" = "--check" ] && [ $status -eq 0 ] && echo "all copies up to date"
exit $status
