import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
SCHEMA_DIR = Path(os.getenv("SCHEMA_DIR", BASE_DIR / "schemas"))

DOCUMENTS_PATH = DATA_DIR / "documents.json"
METADATA_STORE_PATH = DATA_DIR / "metadata_store.json"
QUERIES_PATH = DATA_DIR / "queries.json"
EXPECTED_RESULTS_PATH = DATA_DIR / "expected_results.json"

CHROMA_DIR = Path(os.getenv("CHROMA_DIR", BASE_DIR / "chroma_db"))

EMBEDDING_MODEL = "all-MiniLM-L6-v2"

DEFAULT_TOP_K = 5

ROLES = [
    "teller",
    "loan_officer",
    "risk_analyst",
    "compliance_officer",
    "branch_manager",
    "admin",
]

DOCUMENT_TYPES = [
    "loan_application",
    "kyc_profile",
    "credit_report",
    "risk_assessment",
    "internal_note",
    "compliance_report",
    "policy_document",
]

BRANCH_IDS = ["BR_001", "BR_002", "BR_003", "BR_004", "BR_005"]

SENSITIVITY_LEVELS = ["public", "internal", "medium", "high", "restricted"]

COLLECTION_NAME = "banking_documents"
