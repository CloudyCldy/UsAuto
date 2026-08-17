import sys, traceback
from pathlib import Path

# Ensure project root is on sys.path so `config` can be imported when running
# this script from the `scripts/` folder.
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from config.database import MONGO_URI
from pymongo import MongoClient

print('Using URI:', MONGO_URI)
try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000, connectTimeoutMS=5000)
    client.admin.command('ping')
    print('PING_OK')
except Exception:
    traceback.print_exc()
    print('PING_FAILED')
    sys.exit(1)
