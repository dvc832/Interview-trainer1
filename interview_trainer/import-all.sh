#!/usr/bin/env bash
# import-all.sh — Import all Interview Trainer tools and agent into watsonx Orchestrate
# Usage: ./interview_trainer/import-all.sh
# Make executable: chmod +x interview_trainer/import-all.sh

set -e
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

echo "========================================="
echo " Interview Trainer — watsonx Orchestrate"
echo " Importing tools and agent …"
echo "========================================="

# ── 1. Python Tools ──────────────────────────────────────────────────────────
echo ""
echo "[1/3] Importing Python tools …"
for tool_file in interview_tools.py; do
  echo "  → $tool_file"
  orchestrate tools import -k python -f "${SCRIPT_DIR}/tools/${tool_file}"
done

# ── 2. Flow Tools ─────────────────────────────────────────────────────────────
echo ""
echo "[2/3] Importing Flow tools …"
for flow_file in interview_flow.py report_flow.py; do
  echo "  → $flow_file"
  orchestrate tools import -k flow -f "${SCRIPT_DIR}/tools/${flow_file}"
done

# ── 3. Agent ──────────────────────────────────────────────────────────────────
echo ""
echo "[3/3] Importing agent …"
orchestrate agents import -f "${SCRIPT_DIR}/agents/interview_trainer_agent.yaml"

echo ""
echo "========================================="
echo " ✅  Import complete!"
echo " Launch the chat UI with:"
echo "     orchestrate chat start"
echo " Then select: interview_trainer_agent"
echo "========================================="
