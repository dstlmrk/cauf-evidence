#!/bin/bash

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <user> <server_ip>"
    exit 1
fi

SERVER_USER="$1"
SERVER_IP="$2"

REMOTE_BACKUP_DIR="/tmp"
LOCAL_BACKUP_DIR="./backups"

BACKUP_FILE="backup_$(date +'%Y%m%d%H%M%S').sql"

mkdir -p "$LOCAL_BACKUP_DIR"

ssh "$SERVER_USER@$SERVER_IP" "docker exec -t db pg_dump -U ultihub ultihub > $REMOTE_BACKUP_DIR/$BACKUP_FILE"
scp "$SERVER_USER@$SERVER_IP:$REMOTE_BACKUP_DIR/$BACKUP_FILE" "$LOCAL_BACKUP_DIR/$BACKUP_FILE"
ssh "$SERVER_USER@$SERVER_IP" "rm $REMOTE_BACKUP_DIR/$BACKUP_FILE"
echo "Backup completed and saved to $LOCAL_BACKUP_DIR/$BACKUP_FILE"
