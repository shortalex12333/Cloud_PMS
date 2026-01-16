#!/bin/bash

# LAUNCH CLAUDE WITH FULL PERMISSIONS
# Run this script to start a new Claude session with autonomous mode

# Change to the main project directory
cd /Users/celeste7/Documents/Cloud_PMS

# Launch Claude with:
# --dangerously-skip-permissions: Skip all permission prompts (autonomous mode)
# --add-dir: Add documentation folder as additional working directory

claude --dangerously-skip-permissions \
  --add-dir /Users/celeste7/Desktop/Cloud_PMS_docs_v2 \
  --add-dir /Users/celeste7/Documents/Cloud_PMS

# Alternative if --add-dir doesn't work in your version:
# claude --dangerously-skip-permissions
