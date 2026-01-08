#!/bin/bash
# Enterprise Process Monitor
# Monitors supervisor events and logs process state changes

set -e

LOG_FILE="/app/logs/process-monitor.log"

log() {
    echo "[$(date -Iseconds)] [process-monitor] $1" | tee -a "$LOG_FILE"
}

process_event() {
    local event_data="$1"
    
    # Parse event data
    local process_name=$(echo "$event_data" | grep -o 'processname:[^ ]*' | cut -d: -f2)
    local event_type=$(echo "$event_data" | grep -o 'eventname:[^ ]*' | cut -d: -f2)
    local from_state=$(echo "$event_data" | grep -o 'from_state:[^ ]*' | cut -d: -f2)
    
    log "Process event: $process_name - $event_type (from $from_state)"
    
    # Handle critical process failures
    case "$process_name" in
        postgres)
            if [[ "$event_type" == "PROCESS_STATE_FATAL" ]]; then
                log "CRITICAL: PostgreSQL process failed - attempting restart"
                supervisorctl restart postgres || log "ERROR: Failed to restart PostgreSQL"
            fi
            ;;
        redis)
            if [[ "$event_type" == "PROCESS_STATE_FATAL" ]]; then
                log "CRITICAL: Redis process failed - attempting restart"
                supervisorctl restart redis || log "ERROR: Failed to restart Redis"
            fi
            ;;
        fastapi)
            if [[ "$event_type" == "PROCESS_STATE_FATAL" ]]; then
                log "CRITICAL: FastAPI process failed - attempting restart"
                supervisorctl restart fastapi || log "ERROR: Failed to restart FastAPI"
            fi
            ;;
        label-studio)
            if [[ "$event_type" == "PROCESS_STATE_FATAL" ]]; then
                log "WARNING: Label Studio process failed - attempting restart"
                supervisorctl restart label-studio || log "ERROR: Failed to restart Label Studio"
            fi
            ;;
    esac
}

main() {
    log "Process monitor started"
    
    # Read events from stdin (supervisor event listener protocol)
    while read -r line; do
        case "$line" in
            "READY")
                echo "READY"
                ;;
            "OK")
                echo "OK"
                ;;
            *)
                if [[ "$line" =~ ^ver: ]]; then
                    # Event header - read the event data
                    read -r event_data
                    process_event "$event_data"
                    echo "RESULT 2\nOK"
                fi
                ;;
        esac
    done
}

# Run if called directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi