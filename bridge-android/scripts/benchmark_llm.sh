#!/bin/bash
PORT=8081
URL="http://localhost:$PORT/v1/chat/completions"
PROMPT="Explain the theory of relativity in one short paragraph."

echo "🚀 Starting Benchmark on win via port $PORT..."
echo "Prompt: $PROMPT"
echo "------------------------------------------"

for i in {1..3}
do
    echo -n "Round $i/3... "
    START=$(date +%s%3N)
    RESPONSE=$(curl -s -X POST $URL \
        -H "Content-Type: application/json" \
        -d "{\"model\": \"Gemma-4-E2B-it\", \"messages\": [{\"role\": \"user\", \"content\": \"$PROMPT\"}]}")
    END=$(date +%s%3N)
    
    ELAPSED_MS=$((END - START))
    ELAPSED_SEC=$(echo "scale=3; $ELAPSED_MS / 1000" | bc)
    
    # Extract content and count characters
    CONTENT=$(echo $RESPONSE | grep -o '"content":"[^"]*"' | cut -d'"' -f4)
    CHAR_COUNT=${#CONTENT}
    # Approx tokens (4 chars/token)
    TOKENS=$((CHAR_COUNT / 4))
    TPS=$(echo "scale=2; $TOKENS / $ELAPSED_SEC" | bc)
    
    echo "Done! $TPS tokens/sec ($ELAPSED_SEC seconds)"
    echo "Response Snippet: ${CONTENT:0:50}..."
done
