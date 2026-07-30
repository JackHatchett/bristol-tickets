#!/bin/bash
# Sets up the daily career-coach pipeline as a cron job.
# Run once from Terminal: bash setup_cron.sh
# Set CAREER_COACH_DIR to this agent's provisioned tools/data root before running
# (resolved per-instance via config, e.g. config.local.json's agent data mapping).

CAREER_COACH_DIR="${CAREER_COACH_DIR:?set CAREER_COACH_DIR to this agent's provisioned root first}"
PYTHON=$(which python3)
SCRIPT="$CAREER_COACH_DIR/tools/daily_pipeline.py"
LOG="$CAREER_COACH_DIR/applications/pipeline/logs/cron_output.log"
ENTRY="0 6 * * * $PYTHON $SCRIPT >> $LOG 2>&1"

# Check if the entry already exists
if crontab -l 2>/dev/null | grep -qF "daily_pipeline.py"; then
  echo "Cron job already installed. Nothing to do."
  crontab -l | grep "daily_pipeline.py"
else
  # Add the new entry to the existing crontab (preserve anything already there)
  (crontab -l 2>/dev/null; echo "$ENTRY") | crontab -
  echo "Done. Cron job installed:"
  echo "  $ENTRY"
  echo ""
  echo "The pipeline will run every morning at 6:00 AM."
  echo "Logs will appear in: $LOG"
fi
