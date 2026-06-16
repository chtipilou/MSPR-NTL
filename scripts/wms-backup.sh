#!/bin/bash
# /usr/local/bin/wms-backup.sh <full|diff|incr>  - sauvegarde pgBackRest WMS
set -uo pipefail
TYPE="${1:-incr}"
STANZA=wms
LOG=/var/log/pgbackrest/wms-backup.log
ts(){ date '+%F %T'; }
notify(){ # notification : journal + wall + (mail si configuré)
  echo "$(ts) [$1] $2" >> "$LOG"
  logger -t wms-backup "[$1] $2"
  command -v mail >/dev/null && echo "$2" | mail -s "WMS backup [$1] $(hostname)" root 2>/dev/null || true
}
echo "$(ts) === Démarrage backup type=$TYPE ===" >> "$LOG"
if sudo -u pgbackrest pgbackrest --stanza=$STANZA --type=$TYPE backup >>"$LOG" 2>&1; then
  # vérification d'intégrité du dépôt après backup
  if sudo -u pgbackrest pgbackrest --stanza=$STANZA verify >>"$LOG" 2>&1; then
     notify OK "backup $TYPE + verify réussis"
     exit 0
  else
     notify WARN "backup $TYPE OK mais verify en échec"; exit 2
  fi
else
  notify ERREUR "ÉCHEC backup $TYPE - intervention requise"; exit 1
fi
