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

# Model paths
MODEL_PATH = os.environ.get("MODEL_PATH", "./model.keras")
SCALER_PATH = os.environ.get("SCALER_PATH", "./scaler.save")

# Server
API_HOST = os.environ.get("API_HOST", "0.0.0.0")
API_PORT = int(os.environ.get("API_PORT", "8000"))
