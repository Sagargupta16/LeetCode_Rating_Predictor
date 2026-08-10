"""Centralised configuration loaded from environment variables."""

import os
import re

# LeetCode API
LEETCODE_GRAPHQL_URL = os.environ.get(
    "LEETCODE_GRAPHQL_URL", "https://leetcode.com/graphql"
)

GRAPHQL_HEADERS = {
    "Content-Type": "application/json",
    "Referer": "https://leetcode.com/",
}

# Contest name validation (prevents SSRF)
CONTEST_NAME_RE = re.compile(r"^(weekly|biweekly)-contest-\d+$")

# Caching
CACHE_TTL = int(os.environ.get("CACHE_TTL", "300"))

# CORS
_default_origins = "http://localhost:3000,http://127.0.0.1:3000"
ALLOWED_ORIGINS = [
    o.strip()
    for o in os.environ.get("ALLOWED_ORIGINS", _default_origins).split(",")
    if o.strip()
]

# Model artifacts. Exported by scripts/export_model.py; the runtime needs no
# ML framework to read them.
WEIGHTS_PATH = os.environ.get("WEIGHTS_PATH", "./models/weights.npz")
SCALER_PATH = os.environ.get("SCALER_PATH", "./models/scaler.json")

# Sanity bound on model output. A single contest cannot plausibly move a rating
# further than this, so a larger magnitude means the model or its inputs are
# wrong and the request should fail loudly instead of returning nonsense.
MAX_RATING_CHANGE = float(os.environ.get("MAX_RATING_CHANGE", "500"))

# Rate limiting (requests per window, per client IP)
RATE_LIMIT_REQUESTS = int(os.environ.get("RATE_LIMIT_REQUESTS", "30"))
RATE_LIMIT_WINDOW = int(os.environ.get("RATE_LIMIT_WINDOW", "60"))

# Server
API_HOST = os.environ.get("API_HOST", "0.0.0.0")
API_PORT = int(os.environ.get("API_PORT", "8000"))
