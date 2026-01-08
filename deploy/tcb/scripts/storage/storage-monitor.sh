#!/bin/bash
# Storage Monitoring Daemon
# Continuously monitors storage usage and triggers alerts

set -e

STORAGE_MANAGER="/app/scripts/storage/storage-manager.sh"
LOG_FILE="/app/logs/storage-monitor.log"
MONITOR_INTERVAL="${STORAGE_MONITOR_INTERVAL:-300}"  # 5 minutes

log() {
    echo "[$(date -Iseconds)] [storage-monitor] $1" | tee -a "$LOG_FILE"
}

# Initialize storage monitoring
init_monitoring() {
    log "Initializing storage monitoring..."
    
    # Initialize storage configuration
    "$STORAGE_MANAGER" init
    
    # Create required directories
    mkdir -p /app/storage-requests /app/alerts
    chown superinsight:superinsight /app/storage-requests /app/alerts
    
    log "Storage monitoring initialized"
}

# Main monitoring loop
monitor_loop() {
    log "Starting storage monitoring loop (interval: ${MONITOR_INTERVAL}s)"
    
    while true; do
        log "Running storage check..."
        
        # Run storage monitoring
        if "$STORAGE_MANAGER" monitor; then
            log "Storage monitoring completed successfully"
        else
            log "Storage monitoring detected issues"
        fi
        
        # Sleep until next check
        sleep "$MONITOR_INTERVAL"
    done
}

# Handle shutdown signals
cleanup() {
    log "Storage monitor shutting down..."
    exit 0
}

# Set up signal handlers
trap cleanup SIGTERM SIGINT

# Main execution
main() {
    init_monitoring
    monitor_loop
}

# Run if called directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi