#!/bin/bash
# heybud shell wrapper for bash
# This function enables same-shell command execution

heybud() {
    local HEYBUD_TEMP="/tmp/heybud_output_$$.sh"
    
    # Call the CLI binary and capture output
    heybud "$@" > "$HEYBUD_TEMP" 2>&1
    local exit_code=$?
    
    # Check if output contains execution marker
    if [ -f "$HEYBUD_TEMP" ] && grep -q "^#EXEC_NOW" "$HEYBUD_TEMP"; then
        # Execute in current shell
        source "$HEYBUD_TEMP"
        rm -f "$HEYBUD_TEMP"
    else
        # Just display output
        cat "$HEYBUD_TEMP"
        rm -f "$HEYBUD_TEMP"
    fi
    
    return $exit_code
}

# Alias for convenience
alias hb='heybud'
