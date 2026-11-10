---
paths:
  - "**/{migrations,migrate,alembic,db,database,prisma,drizzle,supabase}/**"
  - "**/*.sql"
  - "**/{schema.prisma,schema.rb,structure.sql,alembic.ini,knexfile.*,drizzle.config.*}"
  - "**/{models,entities}/**"
  - "**/{models,entities,schema}.{py,ts,js,rb,go}"
---

# babel-fish — Database Schema

> Written once by babel-fish; yours to edit.

1. **Every schema change is a migration**, never a hand edit to a live database: one migration per
   logical change, in the repo's migration tool and naming.
2. **NEVER edit a migration that has already run** anywhere but your machine. Fix it with a new one.
3. **Every migration is idempotent**: running it twice leaves the same state as running it once.
   Guard structure changes (`IF NOT EXISTS`, `IF EXISTS`, or the tool's check), write data changes
   as upserts or updates that skip rows already changed, never a blind insert. Prove it: run it
   twice on a scratch database, then down and up again.
4. **Change in steps that never break the running app**: add the new column or table, backfill,
   switch the code, then remove the old one in a later migration. NEVER rename or drop what the
   deployed code still uses.
5. **Every migration is reversible**, or says in a comment why it can't be.
6. **Constraints live in the database**: primary keys, foreign keys, `NOT NULL`, unique and check
   constraints, not only checks in the app. Index foreign keys and the columns you filter or join on.
7. **Data changes get their own migration**, apart from structure changes, batched on large tables.
8. **NEVER run a destructive migration** (dropping or truncating a table or column, deleting data)
   without explicit permission, and confirm a backup exists first.
9. **Follow the existing naming**: table and column case, plural or singular, timestamp and
   soft-delete columns.
