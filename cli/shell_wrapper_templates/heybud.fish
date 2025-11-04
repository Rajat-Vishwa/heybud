# heybud shell wrapper for fish
# This function enables same-shell command execution

function heybud
    set -l HEYBUD_TEMP "/tmp/heybud_output_"(echo %self)".sh"
    
    # Call the CLI binary and capture stdout
    command heybud-cli $argv > $HEYBUD_TEMP
    set -l exit_code $status
    
    # Check if output contains execution marker
    if test -f $HEYBUD_TEMP; and grep -q "^#EXEC_NOW" $HEYBUD_TEMP
        # Execute in current shell
        source $HEYBUD_TEMP
        rm -f $HEYBUD_TEMP
    else
        # Just display output
        cat $HEYBUD_TEMP
        rm -f $HEYBUD_TEMP
    end
    
    return $exit_code
end

# Alias for convenience
alias hb='heybud'
