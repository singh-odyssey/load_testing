#!/bin/bash
# This script acts as a watchdog for boom.py, ensuring it runs continuously.
# It will automatically restart the Python script if it stops for any reason.

# Store the arguments to pass to the Python script.
# This allows us to reuse the same URL and settings on restart.
ARGS=("$@")

echo "Watchdog started. Running boom.py..."
echo "To stop this watchdog completely, press Ctrl+C."

while true; do
    # Run the python script, passing along any arguments it received.
    # The --no-prompt flag is added to ensure it runs non-interactively.
    python3 boom.py "${ARGS[@]}" --no-prompt
    
    # If the script exits, we log it and restart after a short delay.
    EXIT_CODE=$?
    echo "--------------------------------------------------"
    echo "WARNING: boom.py stopped with exit code $EXIT_CODE."
    echo "Restarting in 3 seconds..."
    echo "--------------------------------------------------"
    sleep 3
done
