#!/bin/bash
# Enterprise Storage Management Script
# Manages persistent volumes, monitoring, and alerting for TCB cloud storage

set -e

STORAGE_CONFIG_FILE="/app/config/storage.conf"
LOG_FILE="/app/logs/storage-manager.log"
METRICS_FILE="/app/metrics/storage_metrics.json"

# Storage thresholds
DISK_WARNING_THRESHOLD=${DISK_WARNING_THRESHOLD:-80}
DISK_CRITICAL_THRESHOLD=${DISK_CRITICAL_THRESHOLD:-90}
BACKUP_WARNING_THRESHOLD=${BACKUP_WARNING_THRESHOLD:-85}

log() {
    echo "[$(date -Iseconds)] [storage-manager] $1" | tee -a "$LOG_FILE"
}

# Check storage usage for all mounted volumes
check_storage_usage() {
    log "Checking storage usage for all volumes..."
    
    local volumes=(
        "/var/lib/postgresql/14/main:PostgreSQL Data"
        "/var/lib/redis:Redis Data"
        "/app/label-studio-data:Label Studio Data"
        "/app/uploads:Uploads"
        "/app/logs:Logs"
        "/app/backups:Backups"
        "/app/metrics:Metrics"
    )
    
    local overall_status="healthy"
    local warnings=0
    local criticals=0
    
    for volume_info in "${volumes[@]}"; do
        IFS=':' read -r mount_point description <<< "$volume_info"
        
        if [ -d "$mount_point" ]; then
            local usage=$(df "$mount_point" | awk 'NR==2 {print $5}' | sed 's/%//')
            local available=$(df -h "$mount_point" | awk 'NR==2 {print $4}')
            local total=$(df -h "$mount_point" | awk 'NR==2 {print $2}')
            
            if [ "$usage" -ge "$DISK_CRITICAL_THRESHOLD" ]; then
                log "CRITICAL: $description ($mount_point) usage: ${usage}% (Available: $available)"
                overall_status="critical"
                ((criticals++))
            elif [ "$usage" -ge "$DISK_WARNING_THRESHOLD" ]; then
                log "WARNING: $description ($mount_point) usage: ${usage}% (Available: $available)"
                if [ "$overall_status" != "critical" ]; then
                    overall_status="warning"
                fi
                ((warnings++))
            else
                log "OK: $description ($mount_point) usage: ${usage}% (Available: $available)"
            fi
            
            # Update metrics
            update_storage_metrics "$mount_point" "$description" "$usage" "$available" "$total"
        else
            log "WARNING: Mount point $mount_point not found"
            ((warnings++))
        fi
    done
    
    log "Storage check complete - Status: $overall_status (Warnings: $warnings, Critical: $criticals)"
    return $([ "$overall_status" = "healthy" ] && echo 0 || ([ "$overall_status" = "warning" ] && echo 1 || echo 2))
}

# Update storage metrics in JSON format
update_storage_metrics() {
    local mount_point="$1"
    local description="$2"
    local usage="$3"
    local available="$4"
    local total="$5"
    local timestamp=$(date -Iseconds)
    
    # Create metrics directory if it doesn't exist
    mkdir -p "$(dirname "$METRICS_FILE")"
    
    # Initialize metrics file if it doesn't exist
    if [ ! -f "$METRICS_FILE" ]; then
        echo '{"timestamp": "", "volumes": {}}' > "$METRICS_FILE"
    fi
    
    # Update metrics using jq (if available) or simple JSON manipulation
    if command -v jq >/dev/null 2>&1; then
        local temp_file=$(mktemp)
        jq --arg timestamp "$timestamp" \
           --arg mount "$mount_point" \
           --arg desc "$description" \
           --arg usage "$usage" \
           --arg avail "$available" \
           --arg total "$total" \
           '.timestamp = $timestamp | .volumes[$mount] = {
               "description": $desc,
               "usage_percent": ($usage | tonumber),
               "available": $avail,
               "total": $total,
               "status": (if ($usage | tonumber) >= 90 then "critical" elif ($usage | tonumber) >= 80 then "warning" else "healthy" end)
           }' "$METRICS_FILE" > "$temp_file"
        mv "$temp_file" "$METRICS_FILE"
    else
        # Fallback: simple JSON update without jq
        cat > "$METRICS_FILE" << EOF
{
    "timestamp": "$timestamp",
    "volumes": {
        "$mount_point": {
            "description": "$description",
            "usage_percent": $usage,
            "available": "$available",
            "total": "$total",
            "status": "$([ "$usage" -ge 90 ] && echo "critical" || ([ "$usage" -ge 80 ] && echo "warning" || echo "healthy"))"
        }
    }
}
EOF
    fi
}

# Expand storage volume (TCB-specific)
expand_volume() {
    local mount_point="$1"
    local new_size="$2"
    
    log "Expanding volume $mount_point to $new_size..."
    
    # This would typically involve TCB API calls
    # For now, we'll log the action and create a request file
    local request_file="/app/storage-requests/expand-$(basename "$mount_point")-$(date +%s).json"
    mkdir -p "$(dirname "$request_file")"
    
    cat > "$request_file" << EOF
{
    "action": "expand_volume",
    "mount_point": "$mount_point",
    "current_size": "$(df -h "$mount_point" | awk 'NR==2 {print $2}')",
    "requested_size": "$new_size",
    "timestamp": "$(date -Iseconds)",
    "status": "pending"
}
EOF
    
    log "Volume expansion request created: $request_file"
    log "Manual intervention required to complete volume expansion via TCB console"
}

# Cleanup old files to free space
cleanup_old_files() {
    local mount_point="$1"
    local days_old="${2:-30}"
    
    log "Cleaning up files older than $days_old days in $mount_point..."
    
    case "$mount_point" in
        "/app/logs")
            # Clean old log files
            find "$mount_point" -name "*.log" -type f -mtime +$days_old -delete 2>/dev/null || true
            find "$mount_point" -name "*.log.*" -type f -mtime +$days_old -delete 2>/dev/null || true
            ;;
        "/app/backups")
            # Clean old backup files (keep based on retention policy)
            local retention_days="${BACKUP_RETENTION_DAYS:-7}"
            find "$mount_point" -name "*.sql.gz" -type f -mtime +$retention_days -delete 2>/dev/null || true
            find "$mount_point" -name "*.rdb" -type f -mtime +$retention_days -delete 2>/dev/null || true
            find "$mount_point" -name "*.tar.gz" -type f -mtime +$retention_days -delete 2>/dev/null || true
            ;;
        "/app/uploads")
            # Clean temporary upload files
            find "$mount_point" -name "tmp_*" -type f -mtime +1 -delete 2>/dev/null || true
            find "$mount_point" -name "*.tmp" -type f -mtime +1 -delete 2>/dev/null || true
            ;;
        "/app/metrics")
            # Clean old metrics files
            find "$mount_point" -name "*.json" -type f -mtime +$days_old -delete 2>/dev/null || true
            ;;
    esac
    
    log "Cleanup completed for $mount_point"
}

# Monitor storage and trigger alerts
monitor_storage() {
    log "Starting storage monitoring..."
    
    check_storage_usage
    local status=$?
    
    case $status in
        0)
            log "All storage volumes are healthy"
            ;;
        1)
            log "Storage warning detected - triggering cleanup"
            # Trigger cleanup for volumes with warnings
            cleanup_old_files "/app/logs" 7
            cleanup_old_files "/app/backups"
            cleanup_old_files "/app/uploads" 3
            cleanup_old_files "/app/metrics" 14
            ;;
        2)
            log "CRITICAL: Storage space critically low"
            # Emergency cleanup
            cleanup_old_files "/app/logs" 3
            cleanup_old_files "/app/backups"
            cleanup_old_files "/app/uploads" 1
            cleanup_old_files "/app/metrics" 7
            
            # Send alert (would integrate with TCB monitoring)
            send_storage_alert "critical"
            ;;
    esac
}

# Send storage alert (placeholder for TCB integration)
send_storage_alert() {
    local severity="$1"
    local timestamp=$(date -Iseconds)
    
    log "Sending $severity storage alert..."
    
    # Create alert file for external monitoring systems
    local alert_file="/app/alerts/storage-alert-$(date +%s).json"
    mkdir -p "$(dirname "$alert_file")"
    
    cat > "$alert_file" << EOF
{
    "alert_type": "storage_usage",
    "severity": "$severity",
    "timestamp": "$timestamp",
    "message": "Storage usage has reached $severity levels",
    "metrics_file": "$METRICS_FILE",
    "recommended_actions": [
        "Review and clean up old files",
        "Consider expanding storage volumes",
        "Check backup retention policies"
    ]
}
EOF
    
    log "Alert created: $alert_file"
}

# Initialize storage configuration
init_storage_config() {
    log "Initializing storage configuration..."
    
    mkdir -p "$(dirname "$STORAGE_CONFIG_FILE")"
    
    if [ ! -f "$STORAGE_CONFIG_FILE" ]; then
        cat > "$STORAGE_CONFIG_FILE" << EOF
# SuperInsight Storage Configuration

# Monitoring thresholds (percentage)
DISK_WARNING_THRESHOLD=80
DISK_CRITICAL_THRESHOLD=90
BACKUP_WARNING_THRESHOLD=85

# Cleanup policies (days)
LOG_RETENTION_DAYS=30
METRICS_RETENTION_DAYS=14
TEMP_FILE_RETENTION_DAYS=1

# Auto-expansion settings
AUTO_EXPAND_ENABLED=false
AUTO_EXPAND_THRESHOLD=95
AUTO_EXPAND_INCREMENT=20Gi

# Backup settings
BACKUP_RETENTION_DAYS=7
BACKUP_COMPRESSION=true
BACKUP_VERIFICATION=true
EOF
        log "Storage configuration created: $STORAGE_CONFIG_FILE"
    fi
}

# Backup storage configuration and metrics
backup_storage_data() {
    log "Backing up storage configuration and metrics..."
    
    local backup_dir="/app/backups/storage"
    local timestamp=$(date +%Y%m%d_%H%M%S)
    
    mkdir -p "$backup_dir"
    
    # Backup configuration
    if [ -f "$STORAGE_CONFIG_FILE" ]; then
        cp "$STORAGE_CONFIG_FILE" "$backup_dir/storage.conf.$timestamp"
    fi
    
    # Backup metrics
    if [ -f "$METRICS_FILE" ]; then
        cp "$METRICS_FILE" "$backup_dir/storage_metrics.json.$timestamp"
    fi
    
    # Backup storage requests
    if [ -d "/app/storage-requests" ]; then
        tar -czf "$backup_dir/storage_requests.$timestamp.tar.gz" -C /app storage-requests/ 2>/dev/null || true
    fi
    
    log "Storage data backup completed"
}

# Main function
main() {
    case "${1:-monitor}" in
        init)
            init_storage_config
            ;;
        monitor)
            monitor_storage
            ;;
        check)
            check_storage_usage
            ;;
        cleanup)
            local mount_point="${2:-/app/logs}"
            local days="${3:-30}"
            cleanup_old_files "$mount_point" "$days"
            ;;
        expand)
            local mount_point="$2"
            local new_size="$3"
            if [ -z "$mount_point" ] || [ -z "$new_size" ]; then
                echo "Usage: $0 expand <mount_point> <new_size>"
                exit 1
            fi
            expand_volume "$mount_point" "$new_size"
            ;;
        backup)
            backup_storage_data
            ;;
        alert)
            local severity="${2:-warning}"
            send_storage_alert "$severity"
            ;;
        *)
            echo "Usage: $0 [init|monitor|check|cleanup|expand|backup|alert]"
            echo ""
            echo "Commands:"
            echo "  init                     - Initialize storage configuration"
            echo "  monitor                  - Monitor storage and trigger actions"
            echo "  check                    - Check storage usage only"
            echo "  cleanup <path> [days]    - Clean up old files"
            echo "  expand <path> <size>     - Request volume expansion"
            echo "  backup                   - Backup storage configuration"
            echo "  alert [severity]         - Send storage alert"
            exit 1
            ;;
    esac
}

# Load configuration if it exists
if [ -f "$STORAGE_CONFIG_FILE" ]; then
    source "$STORAGE_CONFIG_FILE"
fi

# Run if called directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi