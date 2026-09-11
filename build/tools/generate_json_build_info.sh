#!/bin/bash
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <TARGET_DEVICE> <PRODUCT_OUT>"
    exit 1
fi

TARGET_DEVICE=$1
PRODUCT_OUT=$2

ZIP_PATH=$(find "$PRODUCT_OUT" -maxdepth 1 -type f -iname 'haloUI-*.zip' \
    -printf '%T@ %p\n' 2>/dev/null | sort -nr | head -n1 | cut -d' ' -f2-)
if [ -z "${ZIP_PATH:-}" ] || [ ! -r "$ZIP_PATH" ]; then
    echo "Error: No readable haloUI-*.zip found in $PRODUCT_OUT" >&2
    exit 1
fi
FILENAME=$(basename "$ZIP_PATH")

if [[ "$FILENAME" =~ ^[hH]aloUI-([0-9]+(\.[0-9]+)*)-([a-zA-Z0-9_-]+)-[0-9]+-(OFFICIAL|UNOFFICIAL|EXPERIMENTAL)-.*\.zip$ ]]; then
    VERSION="${BASH_REMATCH[1]}"
    ROMTYPE="${BASH_REMATCH[4]}"
else
    echo "Error: Unable to parse filename: $FILENAME" >&2
    exit 1
fi

BUILDPROP_PATH="$PRODUCT_OUT/system/build.prop"
DATETIME=$(awk -F= '/^ro\.build\.date\.utc=/{print $2; exit}' "$BUILDPROP_PATH" | tr -d '\r\n')
if [ -z "$DATETIME" ]; then
    echo "Error: Could not extract ro.build.date.utc from $BUILDPROP_PATH" >&2
    exit 1
fi

SIZE=$(stat -c%s "$ZIP_PATH")
ID=$(md5sum "$ZIP_PATH" | awk '{print $1}')
SIZE_MB=$(awk -v s="$SIZE" 'BEGIN{printf "%.2f", s/1048576}')

JSON_FILE="${TARGET_DEVICE}.json"

cat > "$JSON_FILE" <<EOF
{
    "response": [
        {
            "datetime": $DATETIME,
            "filename": "$FILENAME",
            "id": "$ID",
            "romtype": "$ROMTYPE",
            "size": $SIZE,
            "url": "https://sourceforge.net/projects/PROJECT_NAME/files/$TARGET_DEVICE/$FILENAME/download",
            "version": "$VERSION"
        }
    ]
}
EOF

printf '%b' "$CYAN"; cat "$JSON_FILE"; printf '%b\n' "$NC"

echo "=========================================="
printf '         %bWelcome to haloUI%b\n' "$MAGENTA" "$NC"
echo "=========================================="
printf '        %bBUILD COMPLETED SUCCESSFULLY%b\n' "$GREEN" "$NC"
echo "------------------------------------------"
printf 'Datetime : %b%s%b\n' "$YELLOW" "$DATETIME" "$NC"
printf 'Size     : %b%s MB (%s bytes)%b\n' "$YELLOW" "$SIZE_MB" "$SIZE" "$NC"
printf 'Output   : %b%s%b\n' "$CYAN" "$ZIP_PATH" "$NC"
printf 'JSON     : %b%s%b\n' "$YELLOW" "$JSON_FILE" "$NC"
echo "=========================================="
