#!/usr/bin/env python3
"""Import schema.sql and seed_data.sql into Sealos PostgreSQL."""
import sys
import psycopg2

DB_URL = "postgresql://postgres:pqlhjv6k@dbconn.sealosgzg.site:45920/superinsight"

def run_sql_file(conn, filepath):
    with open(filepath, 'r') as f:
        sql = f.read()
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()
    print(f"✅ {filepath} executed successfully")

def main():
    print(f"Connecting to {DB_URL.split('@')[1]}...")
    conn = psycopg2.connect(DB_URL)
    
    # 0. Clean up: drop all existing objects
    print("🧹 Cleaning up existing objects...")
    with conn.cursor() as cur:
        cur.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
    conn.commit()
    print("   Schema reset done")
    
    # 1. Import schema
    print("\n📦 Importing schema.sql...")
    run_sql_file(conn, "deploy/sealos/schema.sql")
    
    # 2. Check tables
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE'")
        count = cur.fetchone()[0]
        print(f"📊 Tables created: {count}")
    
    # 3. Import seed data
    print("\n🌱 Importing seed_data.sql...")
    run_sql_file(conn, "deploy/sealos/seed_data.sql")
    
    # 4. Verify users
    with conn.cursor() as cur:
        cur.execute("SELECT username, role FROM public.users ORDER BY username")
        rows = cur.fetchall()
        print(f"\n👥 Users ({len(rows)}):")
        for row in rows:
            print(f"   {row[0]} - {row[1]}")
    
    conn.close()
    print("\n🎉 Done!")

if __name__ == "__main__":
    main()
