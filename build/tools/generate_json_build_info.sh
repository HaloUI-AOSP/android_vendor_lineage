#!/bin/bash

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <TARGET_DEVICE> <PRODUCT_OUT>"
    exit 1
fi

TARGET_DEVICE=$1
PRODUCT_OUT=$2

ZIP_PATH=$(ls -t "$PRODUCT_OUT"/[hH]aloUI-*.zip 2>/dev/null | head -n1)
if [ -z "$ZIP_PATH" ]; then
    echo "Error: No haloUI-*.zip found in $PRODUCT_OUT"
    exit 1
fi
FILENAME=$(basename "$ZIP_PATH")

if [[ "$FILENAME" =~ ^[hH]aloUI-([0-9]+(\.[0-9]+)*)-([a-zA-Z0-9_-]+)-[0-9]+-(OFFICIAL|UNOFFICIAL|EXPERIMENTAL)-.*\.zip$ ]]; then
    VERSION="${BASH_REMATCH[1]}"
    ROMTYPE="${BASH_REMATCH[4]}"
else
    echo "Error: Unable to parse filename: $FILENAME"
    exit 1
fi

FILE_PATH="$ZIP_PATH"

BUILDPROP_PATH="$PRODUCT_OUT/system/build.prop"
DATETIME=$(grep "ro.build.date.utc" "$BUILDPROP_PATH" | cut -d'=' -f2 | tr -d '\r\n')

if [ -z "$DATETIME" ]; then
    echo "Error: Could not extract timestamp from build.prop"
    exit 1
fi

SIZE=$(stat -c%s "$FILE_PATH")
ID=$(md5sum "$FILE_PATH" | awk '{print $1}')

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

echo -e "${CYAN}"
cat "$JSON_FILE"
echo -e "${NC}"

echo "=========================================="
echo -e "         ${RED}Welcome to haloUI${NC}             "
echo "=========================================="
echo -e "        ${GREEN}BUILD COMPLETED SUCCESSFULLY${NC}      "
echo "------------------------------------------"
echo "Datetime : $DATETIME"
echo "Size     : $(awk "BEGIN {printf \"%.2f MB\", $SIZE/1048576}") ($SIZE bytes)"
echo -e "Output   : ${BLUE}$FILE_PATH${NC}"
echo "JSON     : $JSON_FILE"
echo "=========================================="

exit 0
