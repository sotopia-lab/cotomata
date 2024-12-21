#!/bin/bash

# Start timing
start_time=$(date +%s.%N)

# Start the Flask server using poetry in the background
echo "Starting Flask server..."
poetry run python aact_openhands/app.py &
SERVER_PID=$!

# Wait for server to start
echo "Waiting for server to initialize..."
sleep 2

# Run the test file
echo "Running tests..."
poetry run python aact_openhands/tests/test_app.py

# Store the test exit status
TEST_STATUS=$?

# Kill the Flask server
echo -e "\n\nStopping Flask server..."
kill $SERVER_PID

# Calculate execution time
end_time=$(date +%s.%N)
execution_time=$(echo "$end_time - $start_time" | bc)

echo -e "\nTotal execution time: ${execution_time} seconds"

# Exit with the test status
if [ $TEST_STATUS -eq 0 ]; then
    echo "Tests completed successfully"
    exit 0
else
    echo "Tests failed"
    exit 1
fi