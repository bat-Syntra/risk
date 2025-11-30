#!/usr/bin/env python3
"""
Run the parlay system migration
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from migrations.add_parlay_system import run_migration

if __name__ == "__main__":
    print("🚀 Running parlay system migration...")
    run_migration()
    print("✅ Migration completed successfully!")
