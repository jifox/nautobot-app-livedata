#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

# This script will create a backup of the running Nautobot instance.
#
# It will export the Nautobot database and media files, create a tarball of the backup files,
# and copy the backup tarball to the specified destination directory.
# It will also create the necessary directories and set the permissions.
# It will also clean up the local temporary directory after the backup is created.
# 
# Usage: ./backup-database.sh
#
# Environment Settings:
#      BACKUP_WITH_CHANGLOG="true"
#      BACKUP_FILENAME=nautobot-24-production
#      BACKUP_DEST_DIR=/mnt/swarm_shared/service/nornir-backup/nautobot-24-production/
#
#      # Directory where the Nautobot backup files are stored.
#      RESTORE_SOURCE_DIR=/mnt/swarm_shared/service/nornir-backup/nautobot-production/
#
#      =/mnt/db/nautobot-24-production/backups

# Set the environment files to be sourced in order. The highest priority file should be listed last.
ENVIRONMENT_FILENAMES=(dev.env development.env local.env .env .creds.env creds.env)

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
pushd $SCRIPT_DIR > /dev/null || exit 1

# Get the binary directory of the python virtual environment
VIRTUAL_ENV_DIR="$(~/.local/bin/poetry env info -p)"

# Activate the virtual environment.
source ${VIRTUAL_ENV_DIR}/bin/activate

# Add Poetry to PATH (append to end) so tasks.py can call poetry commands
export PATH="${PATH}:/home/ansible/.local/bin"

# Load environment variables from the specified files
for envfile in "${ENVIRONMENT_FILENAMES[@]}"
do
  for dir in "." "environments" "development"
  do
    if [ -f "${dir}/${envfile}" ]; then
      echo "Sourcing environment file: ${dir}/${envfile}"
      source "${dir}/${envfile}"
      break
    fi
  done
done


# Initialize Defaults form environment variables
BACKUP_WITH_CHANGLOG="${BACKUP_WITH_CHANGLOG:-"false"}"
BACKUP_FILENAME="${BACKUP_FILENAME:-"nautobot-3-prod"}"
BACKUP_DEST_DIR="${BACKUP_DEST_DIR:-"/mnt/swarm_shared/service/backups/nautobot-app-livedata/"}"
# Remove trailing slash if it exists
BACKUP_DEST_DIR="${BACKUP_DEST_DIR%/}"



##############################################################################
# Overwrite environment variables with local settings here

# BACKUP_WITH_CHANGLOG=
# BACKUP_FILENAME=
# BACKUP_DEST_DIR=


##############################################################################
# Nothing to change below 

# Directory used during restore
DATESTR=$(date "+%Y%m%d-%H%M%S")

LOCAL_BASE_DIR_DEFAULT="${SCRIPT_DIR}"
LOCAL_TMP_DIR="${LOCAL_BASE_DIR_DEFAULT}/.backups/${DATESTR}"
BACKUP_TAR_FILNAME="${BACKUP_FILENAME}.${DATESTR}.tgz"


# Create Backup directory  (.backups/20250611-083028)
sudo mkdir -p "${LOCAL_TMP_DIR}"
sudo chmod -R 777 "${LOCAL_BASE_DIR_DEFAULT}/.backups"
# Copy the latest backup file to the local temporary directory

# Export Nautobot Data to SCRIPT_DIR (dump.sql and media.tgz)
invoke backup-db  --no-readable
invoke backup-media

sleep 2

# Move the data to the local temporary directory (.backups/20250611-083028)
mv dump.sql "${LOCAL_TMP_DIR}/${BACKUP_FILENAME}.sql"
mv media.tgz "${LOCAL_TMP_DIR}/${BACKUP_FILENAME}.media.tgz"


# Wait for both files to exist and their sizes to stabilize (to ensure the export is complete)
prev_size_sql=0
prev_size_media=0

while true; do
  if [ -f "${LOCAL_TMP_DIR}/${BACKUP_FILENAME}.sql" ] && [ -f "${LOCAL_TMP_DIR}/${BACKUP_FILENAME}.media.tgz" ]; then
    curr_size_sql=$(stat -c%s "${LOCAL_TMP_DIR}/${BACKUP_FILENAME}.sql")
    curr_size_media=$(stat -c%s "${LOCAL_TMP_DIR}/${BACKUP_FILENAME}.media.tgz")
    if [ "$curr_size_sql" -eq "$prev_size_sql" ] && [ "$curr_size_media" -eq "$prev_size_media" ]; then
      break
    fi
    prev_size_sql=$curr_size_sql
    prev_size_media=$curr_size_media
  else
    echo "Waiting for Nautobot data export to complete..."
  fi
  sleep 2
done


# Create a tarball of the backup files (.backups/nautobot-24-production.20250611-083028.tgz)
tar -czf "${LOCAL_BASE_DIR_DEFAULT}/.backups/${BACKUP_TAR_FILNAME}" -C "${LOCAL_BASE_DIR_DEFAULT}/.backups" ${DATESTR}
sudo chmod -R 777 "${LOCAL_BASE_DIR_DEFAULT}/.backups/"

# Copy the backup tarball to the destination directory
sudo mkdir -p "${BACKUP_DEST_DIR}"
sudo cp "${LOCAL_BASE_DIR_DEFAULT}/.backups/${BACKUP_TAR_FILNAME}" "${BACKUP_DEST_DIR}"
# Set permissions for the backup directory
sudo chmod -R 777 "${BACKUP_DEST_DIR}"

# Clean up the local temporary directory
echo "Cleaning up temporary backup files 'sudo rm -rf ${LOCAL_BASE_DIR_DEFAULT}/.backups/*' ..."
sudo rm -rf ${LOCAL_BASE_DIR_DEFAULT}/.backups/*
# Print the backup file location
echo ""
echo "Backup created successfully: ${BACKUP_DEST_DIR}/${BACKUP_TAR_FILNAME}"
