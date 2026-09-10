# import-all.ps1 — Windows PowerShell import script for Interview Trainer
# Usage: .\interview_trainer\import-all.ps1

$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Definition

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host " Interview Trainer - watsonx Orchestrate"
Write-Host " Importing tools and agent ..."
Write-Host "==========================================" -ForegroundColor Cyan

# 1. Python Tools
Write-Host "`n[1/3] Importing Python tools ..." -ForegroundColor Yellow
orchestrate tools import -k python -f "$SCRIPT_DIR\tools\interview_tools.py"

# 2. Flow Tools
Write-Host "`n[2/3] Importing Flow tools ..." -ForegroundColor Yellow
orchestrate tools import -k flow -f "$SCRIPT_DIR\tools\interview_flow.py"
orchestrate tools import -k flow -f "$SCRIPT_DIR\tools\report_flow.py"

# 3. Agent
Write-Host "`n[3/3] Importing agent ..." -ForegroundColor Yellow
orchestrate agents import -f "$SCRIPT_DIR\agents\interview_trainer_agent.yaml"

Write-Host "`n==========================================" -ForegroundColor Green
Write-Host " Import complete!" -ForegroundColor Green
Write-Host " Launch the chat UI with:"
Write-Host "     orchestrate chat start"
Write-Host " Then select: interview_trainer_agent"
Write-Host "==========================================" -ForegroundColor Green
