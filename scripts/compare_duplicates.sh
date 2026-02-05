#!/bin/bash

FILE="frontend/src/locales/en/admin.json"

echo "=== Duplicate Key Analysis ==="
echo ""

# For each duplicate, extract both occurrences and compare
for key in "tenants" "console" "system" "textToSql" "llm" "configDashboard" "configDB"; do
    echo "### $key ###"
    
    # Get line numbers
    lines=$(grep -n "^  \"$key\": {$" "$FILE" | cut -d: -f1)
    line_array=($lines)
    
    if [ ${#line_array[@]} -eq 2 ]; then
        first_line=${line_array[0]}
        second_line=${line_array[1]}
        
        echo "First occurrence: line $first_line"
        echo "Second occurrence: line $second_line"
        
        # Extract first occurrence to temp file
        awk "NR==$first_line,/^  },?\$/ {print}" "$FILE" | head -50 > /tmp/first_$key.txt
        
        # Extract second occurrence to temp file  
        awk "NR==$second_line,/^  },?\$/ {print}" "$FILE" | head -50 > /tmp/second_$key.txt
        
        echo "First 10 lines of first occurrence:"
        head -10 /tmp/first_$key.txt
        echo ""
        echo "First 10 lines of second occurrence:"
        head -10 /tmp/second_$key.txt
        echo ""
    fi
    
    echo "---"
    echo ""
done
