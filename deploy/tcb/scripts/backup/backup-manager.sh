#!/bin/bash
# Enterprise Backup Management Script
# Handles automated backups of PostgreSQL, Redis, and application data with TCB integration

set -e

BACKUP_DIR="/app/backups"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-7}"
LOG_FILE="/app/logs/backup-manager.log"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
COS_BACKUP_ENABLED="${COS_BACKUP_ENABLED:-true}"

log() {
    echo "[$(date -Iseconds)] [backup-manager] $1" | tee -a "$LOG_FILE"
}

# Upload backup to Tencent Cloud Object Storage (COS)
upload_to_cos() {
    local backup_file="$1"
    local cos_path="$2"
    
    if [ "$COS_BACKUP_ENABLED" != "true" ]; then
        log "COS backup disabled, skipping upload"
        return 0
    fi
    
    if [ -z "$COS_SECRET_ID" ] || [ -z "$COS_SECRET_KEY" ] || [ -z "$COS_BUCKET" ]; then
        log "WARNING: COS credentials not configured, skipping upload"
        return 0
    fi
    
    log "Uploading backup to COS: $cos_path"
    
    # Use coscli or curl for COS upload (simplified example)
    # In production, you would use the official COS SDK or CLI
    local cos_url="https://${COS_BUCKET}.cos.${COS_REGION}.myqcloud.com/${cos_path}"
    
    # Create upload request file for external processing
    local upload_request="/app/storage-requests/cos-upload-$(date +%s).json"
    cat > "$upload_request" << EOF
{
    "action": "cos_upload",
    "local_file": "$backup_file",
    "cos_path": "$cos_path",
    "cos_url": "$cos_url",
    "timestamp": "$(date -Iseconds)",
    "status": "pending"
}
EOF
    
    log "COS upload request created: $upload_request"
}

create_postgres_backup() {
    log "Creating PostgreSQL backup..."
    
    local backup_file="$BACKUP_DIR/postgres_${TIMESTAMP}.sql"
    local compressed_file="$backup_file.gz"
    
    # Create backup
    if pg_dump -U "$POSTGRES_USER" -h localhost -d "$POSTGRES_DB" > "$backup_file"; then
        # Compress backup
        gzip "$backup_file"
        log "PostgreSQL backup created: $compressed_file"
        
        # Verify backup integrity
        if gunzip -t "$compressed_file" 2>/dev/null; then
            log "PostgreSQL backup integrity verified"
            echo "$compressed_file" >> "$BACKUP_DIR/postgres_backups.list"
            
            # Upload to COS
            upload_to_cos "$compressed_file" "backups/postgres/postgres_${TIMESTAMP}.sql.gz"
            
            # Update backup metadata
            update_backup_metadata "postgres" "$compressed_file" "$(stat -c%s "$compressed_file")"
        else
            log "ERROR: PostgreSQL backup integrity check failed"
            rm -f "$compressed_file"
            return 1
        fi
    else
        log "ERROR: Failed to create PostgreSQL backup"
        return 1
    fi
}

create_redis_backup() {
    log "Creating Redis backup..."
    
    local backup_file="$BACKUP_DIR/redis_${TIMESTAMP}.rdb"
    
    # Trigger Redis save
    if redis-cli BGSAVE > /dev/null 2>&1; then
        # Wait for save to complete
        local last_save=$(redis-cli LASTSAVE)
        while [ "$(redis-cli LASTSAVE)" = "$last_save" ]; do
            sleep 1
        done
        
        # Copy RDB file
        if cp /var/lib/redis/dump.rdb "$backup_file"; then
            log "Redis backup created: $backup_file"
            echo "$backup_file" >> "$BACKUP_DIR/redis_backups.list"
            
            # Upload to COS
            upload_to_cos "$backup_file" "backups/redis/redis_${TIMESTAMP}.rdb"
            
            # Update backup metadata
            update_backup_metadata "redis" "$backup_file" "$(stat -c%s "$backup_file")"
        else
            log "ERROR: Failed to copy Redis backup"
            return 1
        fi
    else
        log "ERROR: Failed to trigger Redis backup"
        return 1
    fi
}

create_application_backup() {
    log "Creating application data backup..."
    
    local backup_file="$BACKUP_DIR/application_${TIMESTAMP}.tar.gz"
    
    # Backup application data
    if tar -czf "$backup_file" -C /app \
        --exclude=backups \
        --exclude=logs \
        --exclude=__pycache__ \
        --exclude=*.pyc \
        --exclude=.git \
        uploads label-studio-data; then
        log "Application backup created: $backup_file"
        echo "$backup_file" >> "$BACKUP_DIR/application_backups.list"
        
        # Upload to COS
        upload_to_cos "$backup_file" "backups/application/application_${TIMESTAMP}.tar.gz"
        
        # Update backup metadata
        update_backup_metadata "application" "$backup_file" "$(stat -c%s "$backup_file")"
    else
        log "ERROR: Failed to create application backup"
        return 1
    fi
}

create_storage_snapshot() {
    log "Creating storage volume snapshots..."
    
    # Create snapshot requests for TCB volumes
    local volumes=(
        "postgres-data:/var/lib/postgresql/14/main"
        "redis-data:/var/lib/redis"
        "label-studio-data:/app/label-studio-data"
        "uploads:/app/uploads"
    )
    
    for volume_info in "${volumes[@]}"; do
        IFS=':' read -r volume_name mount_path <<< "$volume_info"
        
        local snapshot_request="/app/storage-requests/snapshot-${volume_name}-$(date +%s).json"
        cat > "$snapshot_request" << EOF
{
    "action": "create_snapshot",
    "volume_name": "$volume_name",
    "mount_path": "$mount_path",
    "snapshot_name": "${volume_name}-snapshot-${TIMESTAMP}",
    "timestamp": "$(date -Iseconds)",
    "status": "pending"
}
EOF
        log "Snapshot request created for $volume_name: $snapshot_request"
    done
}

update_backup_metadata() {
    local backup_type="$1"
    local backup_file="$2"
    local file_size="$3"
    
    local metadata_file="$BACKUP_DIR/backup_metadata.json"
    local timestamp=$(date -Iseconds)
    
    # Initialize metadata file if it doesn't exist
    if [ ! -f "$metadata_file" ]; then
        echo '{"backups": []}' > "$metadata_file"
    fi
    
    # Add backup metadata
    if command -v jq >/dev/null 2>&1; then
        local temp_file=$(mktemp)
        jq --arg type "$backup_type" \
           --arg file "$backup_file" \
           --arg size "$file_size" \
           --arg timestamp "$timestamp" \
           '.backups += [{
               "type": $type,
               "file": $file,
               "size_bytes": ($size | tonumber),
               "timestamp": $timestamp,
               "retention_date": (now + (7 * 24 * 3600) | strftime("%Y-%m-%dT%H:%M:%SZ"))
           }]' "$metadata_file" > "$temp_file"
        mv "$temp_file" "$metadata_file"
    fi
}

cleanup_old_backups() {
    log "Cleaning up backups older than $RETENTION_DAYS days..."
    
    # Clean PostgreSQL backups
    if [ -f "$BACKUP_DIR/postgres_backups.list" ]; then
        while IFS= read -r backup_file; do
            if [ -f "$backup_file" ] && [ "$(find "$backup_file" -mtime +$RETENTION_DAYS 2>/dev/null)" ]; then
                rm -f "$backup_file"
                log "Removed old PostgreSQL backup: $backup_file"
            fi
        done < "$BACKUP_DIR/postgres_backups.list"
        
        # Update backup list
        grep -v "$(find $BACKUP_DIR -name "postgres_*.sql.gz" -mtime +$RETENTION_DAYS 2>/dev/null)" \
            "$BACKUP_DIR/postgres_backups.list" > "$BACKUP_DIR/postgres_backups.list.tmp" 2>/dev/null || true
        mv "$BACKUP_DIR/postgres_backups.list.tmp" "$BACKUP_DIR/postgres_backups.list" 2>/dev/null || true
    fi
    
    # Clean Redis backups
    if [ -f "$BACKUP_DIR/redis_backups.list" ]; then
        while IFS= read -r backup_file; do
            if [ -f "$backup_file" ] && [ "$(find "$backup_file" -mtime +$RETENTION_DAYS 2>/dev/null)" ]; then
                rm -f "$backup_file"
                log "Removed old Redis backup: $backup_file"
            fi
        done < "$BACKUP_DIR/redis_backups.list"
        
        # Update backup list
        grep -v "$(find $BACKUP_DIR -name "redis_*.rdb" -mtime +$RETENTION_DAYS 2>/dev/null)" \
            "$BACKUP_DIR/redis_backups.list" > "$BACKUP_DIR/redis_backups.list.tmp" 2>/dev/null || true
        mv "$BACKUP_DIR/redis_backups.list.tmp" "$BACKUP_DIR/redis_backups.list" 2>/dev/null || true
    fi
    
    # Clean application backups
    if [ -f "$BACKUP_DIR/application_backups.list" ]; then
        while IFS= read -r backup_file; do
            if [ -f "$backup_file" ] && [ "$(find "$backup_file" -mtime +$RETENTION_DAYS 2>/dev/null)" ]; then
                rm -f "$backup_file"
                log "Removed old application backup: $backup_file"
            fi
        done < "$BACKUP_DIR/application_backups.list"
        
        # Update backup list
        grep -v "$(find $BACKUP_DIR -name "application_*.tar.gz" -mtime +$RETENTION_DAYS 2>/dev/null)" \
            "$BACKUP_DIR/application_backups.list" > "$BACKUP_DIR/application_backups.list.tmp" 2>/dev/null || true
        mv "$BACKUP_DIR/application_backups.list.tmp" "$BACKUP_DIR/application_backups.list" 2>/dev/null || true
    fi
}

restore_postgres_backup() {
    local backup_file="$1"
    
    if [ -z "$backup_file" ]; then
        log "ERROR: No backup file specified for PostgreSQL restore"
        return 1
    fi
    
    if [ ! -f "$backup_file" ]; then
        log "ERROR: Backup file not found: $backup_file"
        return 1
    fi
    
    log "Restoring PostgreSQL from backup: $backup_file"
    
    # Stop services that depend on PostgreSQL
    supervisorctl stop fastapi label-studio || true
    
    # Drop and recreate database
    dropdb -U "$POSTGRES_USER" -h localhost "$POSTGRES_DB" --if-exists
    createdb -U "$POSTGRES_USER" -h localhost "$POSTGRES_DB"
    
    # Restore from backup
    if gunzip -c "$backup_file" | psql -U "$POSTGRES_USER" -h localhost -d "$POSTGRES_DB"; then
        log "PostgreSQL restore completed successfully"
        
        # Restart services
        supervisorctl start fastapi label-studio
        return 0
    else
        log "ERROR: PostgreSQL restore failed"
        return 1
    fi
}

verify_backup_integrity() {
    log "Verifying backup integrity..."
    
    local errors=0
    
    # Verify PostgreSQL backups
    if [ -f "$BACKUP_DIR/postgres_backups.list" ]; then
        while IFS= read -r backup_file; do
            if [ -f "$backup_file" ]; then
                if ! gunzip -t "$backup_file" 2>/dev/null; then
                    log "ERROR: Corrupted PostgreSQL backup: $backup_file"
                    ((errors++))
                fi
            fi
        done < "$BACKUP_DIR/postgres_backups.list"
    fi
    
    # Verify application backups
    if [ -f "$BACKUP_DIR/application_backups.list" ]; then
        while IFS= read -r backup_file; do
            if [ -f "$backup_file" ]; then
                if ! tar -tzf "$backup_file" >/dev/null 2>&1; then
                    log "ERROR: Corrupted application backup: $backup_file"
                    ((errors++))
                fi
            fi
        done < "$BACKUP_DIR/application_backups.list"
    fi
    
    if [ $errors -eq 0 ]; then
        log "All backups verified successfully"
        return 0
    else
        log "ERROR: $errors corrupted backups found"
        return 1
    fi
}

main() {
    # Create backup directory if it doesn't exist
    mkdir -p "$BACKUP_DIR"
    
    case "${1:-backup}" in
        backup)
            log "Starting comprehensive backup process..."
            
            create_postgres_backup
            create_redis_backup
            create_application_backup
            create_storage_snapshot
            cleanup_old_backups
            
            log "Backup process completed"
            ;;
        restore-postgres)
            restore_postgres_backup "$2"
            ;;
        cleanup)
            cleanup_old_backups
            ;;
        verify)
            verify_backup_integrity
            ;;
        snapshot)
            create_storage_snapshot
            ;;
        *)
            echo "Usage: $0 [backup|restore-postgres <file>|cleanup|verify|snapshot]"
            exit 1
            ;;
    esac
}

# Run if called directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi