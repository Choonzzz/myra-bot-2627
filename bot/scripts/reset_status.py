# scripts/reset_status.py
# One-off admin utility: replaces the "user_status" hash in Redis with the
# current RA_DISPLAY_ORDER roster from config.py, all set to OUT.
#
# Run from the bot/ directory: python scripts/reset_status.py

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from redis_client import get_redis
from config import RA_DISPLAY_ORDER


def main():
    r = get_redis()

    old_names = list(r.hgetall("user_status").keys())
    if old_names:
        r.hdel("user_status", *old_names)

    for name in RA_DISPLAY_ORDER:
        r.hset("user_status", name, "OUT")

    print(f"Removed {len(old_names)} old name(s): {old_names}")
    print(f"Set {len(RA_DISPLAY_ORDER)} name(s) to OUT: {RA_DISPLAY_ORDER}")


if __name__ == "__main__":
    main()
