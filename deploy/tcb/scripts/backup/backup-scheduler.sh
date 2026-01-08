#!/bin/bash
# Enterprise Backup Scheduler
# Runs automated backups on schedule

set -e

LOG_FILE="/app/logs/backup-scheduler.log"
BACKUP_SCRIPT="/app/scripts/backup/backup-manager.sh"

log() {
    echo "[$(date -Iseconds)] [backup-scheduler] $1" | tee -a "$LOG_FILE"
}

run_backup() {
    log "Starting scheduled backup..."
    
    if "$BACKUP_SCRIPT" backup; then
        log "Scheduled backup completed successfully"
    else
        log "ERROR: Scheduled backup failed"
    fi
}

main() {
    log "Backup scheduler started"
    
    # Run backup every 6 hours (21600 seconds)
    BACKUP_INTERVAL=${BACKUP_INTERVAL:-21600}
    
    while true; do
        run_backup
        log "Next backup in $BACKUP_INTERVAL seconds"
        sleep "$BACKUP_INTERVAL"
    done
}

# Handle signals for graceful shutdown
trap 'log "Backup scheduler shutting down..."; exit 0' SIGTERM SIGINT

# Run if called directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi