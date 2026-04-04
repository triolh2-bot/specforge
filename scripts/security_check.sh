#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "[security] running static checks"

if ! command -v bandit >/dev/null 2>&1; then
  echo "[security] missing dependency: bandit"
  echo "[security] install with: pip install -r requirements-security.txt"
  exit 1
fi

if ! command -v pip-audit >/dev/null 2>&1; then
  echo "[security] missing dependency: pip-audit"
  echo "[security] install with: pip install -r requirements-security.txt"
  exit 1
fi

if ! command -v detect-secrets >/dev/null 2>&1; then
  echo "[security] missing dependency: detect-secrets"
  echo "[security] install with: pip install -r requirements-security.txt"
  exit 1
fi

bandit -c .bandit -r specforge app.py
pip-audit -r requirements.txt
detect-secrets scan --all-files --baseline .secrets.baseline

echo "[security] checks completed"
