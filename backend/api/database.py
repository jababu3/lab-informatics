import os

try:
    from pymongo import MongoClient

    mongo_client = MongoClient(os.getenv("MONGODB_URL", "mongodb://localhost:27017/"))
    db = mongo_client.lab_informatics
    compounds_collection = db.compounds
    experiments_collection = db.experiments
    MONGO_AVAILABLE = True
    print("✅ MongoDB connected")
except Exception as e:
    MONGO_AVAILABLE = False
    db = None
    compounds_collection = None
    experiments_collection = None
    print(f"⚠️  MongoDB: {e}")

try:
    from rdkit import Chem  # noqa: F401

    RDKIT_AVAILABLE = True
except ImportError:
    RDKIT_AVAILABLE = False
