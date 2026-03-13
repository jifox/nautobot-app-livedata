#!/bin/bash


# This script will restore the latest backup from RESTORE_SOURCE_DIR

# It will stop the Nautobot services, delete the database and media files,
# and restore the database and media files from the latest backup file.
# It will also create the necessary directories and set the permissions.
#
# Usage: ./restore-database.sh
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
BACKUP_FILENAME="${BACKUP_FILENAME:-"nautobot-production"}"
BACKUP_DEST_DIR="${BACKUP_DEST_DIR:-"/mnt/swarm_shared/service/backups/nautobot-app-livedata/"}"
RESTORE_FILENAME="${RESTORE_FILENAME:-"${BACKUP_FILENAME}"}"
RESTORE_SOURCE_DIR="${RESTORE_SOURCE_DIR:-"/mnt/swarm_shared/service/backups/nautobot-app-livedata/"}"

##############################################################################
# Overwrite environment variables with local settings here

# RESTORE_FILENAME=nautobot-3-production
# RESTORE_SOURCE_DIR=/mnt/swarm_shared/service/backups/nautobot-3-production/

# BACKUP_WITH_CHANGLOG=
# BACKUP_FILENAME=
# BACKUP_DEST_DIR=


##############################################################################
# Nothing to change below

echo ""
echo "---- Restore Nautobot Database ----"
echo "RESTORE_FILENAME=${RESTORE_FILENAME}"
echo "RESTORE_SOURCE_DIR=${RESTORE_SOURCE_DIR}"

# Utility helpers -----------------------------------------------------------
find_newest_backup_file() {
  local dir="$1"
  local prefix="$2"
  local newest_file
  newest_file=$(find "$dir" -maxdepth 1 -type f -name "${prefix}*.tgz" -printf '%T@ %p\n' | sort -n | tail -1 | cut -d' ' -f2-)
  if [ -z "$newest_file" ]; then
    echo "No backup files found in '${dir}' with prefix '${prefix}'."
    echo "Please check the RESTORE_SOURCE_DIR and BACKUP_FILENAME settings."
    return 1
  fi
  printf '%s' "$newest_file"
}

latest_backup=$(find_newest_backup_file "$RESTORE_SOURCE_DIR" "$RESTORE_FILENAME")
if [ -z "$latest_backup" ]; then
  echo "Exiting restore script."
  popd > /dev/null || exit 1
  exit 1
fi
echo "Latest backup file found: $latest_backup"

echo ""
read -p "Do you realy want do RESTORE the DATABASE? Continue (y/n)?" CONT
if [ "$CONT" != "y" ] && [ "$CONT" != "yes" ] && [ "$CONT" != "j" ] && [ "$CONT" != "a"  ]; then
  echo "Abort"
  exit 1;
fi

# Directory used during restore
LOCAL_BASE_DIR_DEFAULT="${SCRIPT_DIR}"
LOCAL_BASE_DIR=${RESTORE_LOCAL_BASE_DIR:-"${LOCAL_BASE_DIR_DEFAULT}"}
LOCAL_TMP_DIR="${LOCAL_BASE_DIR}/.backups/Downloads"

# Backup filename starts with (e.g. nautobot-production, nautobot-shut-no-shut)
RESTORE_FILENAME_STARTSWITH=${RESTORE_FILENAME}


# Cleanup database and media files by destroying the services and volumes
echo "---- Stopping services, delete Volumes and pause 3 sec ..."
# docker compose --project-name ${COMPOSE_PROJECT_NAME} $COMPOSE_FILES_OPTION down -v
invoke destroy --no-confirm
sleep 3s

# Create restore directory
sudo mkdir -p "${LOCAL_TMP_DIR}"
sudo chmod -R 777 "${LOCAL_TMP_DIR}"
# Copy the latest backup file to the local temporary directory
sudo /bin/cp "${latest_backup}" "${LOCAL_TMP_DIR}/"
sudo chmod -R 777 "${LOCAL_TMP_DIR}"
latest_backup="${LOCAL_TMP_DIR}/$(basename "${latest_backup}")"


# Allow restore of backup files with different Sources (e.g. nautobot-porduction, nautobot-shut-no-shut)
# RESTORE_FILENAME_STARTSWITH=$(basename "${latest_backup}" | cut -d"." -f1 )
restore_subdir=$(basename "${latest_backup}" | cut -d"." -f2)
echo "    Restoring backup file:       '${latest_backup}'"
echo "    Subdir:                      '${restore_subdir}'"
echo "    Backup filename starts with: '${RESTORE_FILENAME_STARTSWITH}'"


# Extract backup (.sql and media)
echo "---- Extracting backup files to '${LOCAL_TMP_DIR}'"
tar -xzf "${latest_backup}" -C "${LOCAL_TMP_DIR}/"
sudo chmod -R 777 "${LOCAL_TMP_DIR}"
tree "${LOCAL_TMP_DIR}"

sudo rm -f "${SCRIPT_DIR}/dump.sql"
sudo rm -f "${SCRIPT_DIR}/media.tgz"

if [ -d "${LOCAL_TMP_DIR}/backups/${restore_subdir}" ]; then
  cp -f "${LOCAL_TMP_DIR}/backups/${restore_subdir}/${RESTORE_FILENAME_STARTSWITH}.sql" "${SCRIPT_DIR}/dump.sql"
  cp -f "${LOCAL_TMP_DIR}/backups/${restore_subdir}/${RESTORE_FILENAME_STARTSWITH}.media.tgz" "${SCRIPT_DIR}/media.tgz"
else
  echo "---- Restore from root directory"
  cp -f "${LOCAL_TMP_DIR}/${restore_subdir}/${RESTORE_FILENAME_STARTSWITH}.sql" "${SCRIPT_DIR}/dump.sql"
  cp -f "${LOCAL_TMP_DIR}/${restore_subdir}/${RESTORE_FILENAME_STARTSWITH}.media.tgz" "${SCRIPT_DIR}/media.tgz"
fi

invoke start --service db
# Allow database initialization
echo "---- Pause 15s to allow database initialization"
sleep 15s

invoke db-import --input-file="dump.sql"
invoke media-import --input-file="media.tgz"
sleep 5s

# Cleanup backup files
sudo rm -rf ${LOCAL_TMP_DIR}/*

popd || exit
echo "Finished restore, Restarting Nautobot services ..."
invoke stop post-upgrade start
