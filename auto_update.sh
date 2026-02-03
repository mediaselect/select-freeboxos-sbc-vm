#!/bin/bash
set -euo pipefail

INSTALL_DIR="$HOME/select-freeboxos"
CONFIG_DIR="$HOME/.config/select_freeboxos"
LAST_RELEASE_FILE="$CONFIG_DIR/.last_release"

REPO="mediaselect/select-freeboxos-sbc-vm"
GPG_KEY_PATH="$CONFIG_DIR/public.key"

mkdir -p "$CONFIG_DIR"

# ----------------------------------------------------------------------
# 1. Import and trust public GPG key (ONLY if not already imported)
# ----------------------------------------------------------------------
if ! gpg --list-keys | grep -q "tvselect update key"; then
    echo "[INFO] Importing trusted release-signing key..."
    gpg --import "$GPG_KEY_PATH"
fi

# ----------------------------------------------------------------------
# 2. Fetch latest release metadata from GitHub
# ----------------------------------------------------------------------
echo "[INFO] Checking latest release..."
api_json=$(curl -s "https://api.github.com/repos/$REPO/releases/latest")

latest_tag=$(echo "$api_json" | jq -r '.tag_name')
if [ "$latest_tag" = "null" ] || [ -z "$latest_tag" ]; then
    echo "[ERROR] Failed to fetch the latest release tag."
    exit 1
fi
VERSION="${latest_tag#v}"
echo "[INFO] Latest release is: $latest_tag"

# ----------------------------------------------------------------------
# 3. Check if already updated
# ----------------------------------------------------------------------
if [ -f "$LAST_RELEASE_FILE" ]; then
    installed_tag=$(cat "$LAST_RELEASE_FILE")
    if [ "$installed_tag" = "$latest_tag" ]; then
        echo "[INFO] Already up to date."
        exit 0
    fi
fi

# ----------------------------------------------------------------------
# 4. Determine asset URLs
# ----------------------------------------------------------------------
zip_url=$(echo "$api_json" | jq -r '.assets[] | select(.name | endswith(".zip")) | .browser_download_url')
asc_url="$zip_url.asc"

if [ -z "$zip_url" ] || [ -z "$asc_url" ]; then
    echo "[ERROR] Could not determine release URLs."
    exit 1
fi

echo "[INFO] ZIP URL: $zip_url"
echo "[INFO] ASC URL: $asc_url"

tmp_dir=$(mktemp -d)
zip_file="$tmp_dir/app.zip"
asc_file="$tmp_dir/app.zip.asc"

# ----------------------------------------------------------------------
# 5. Download release files
# ----------------------------------------------------------------------
echo "[INFO] Downloading release archive..."
curl -sL "$zip_url" -o "$zip_file"

echo "[INFO] Downloading signature..."
curl -sL "$asc_url" -o "$asc_file"

# ----------------------------------------------------------------------
# 6. Verify GPG signature
# ----------------------------------------------------------------------
echo "[INFO] Verifying signature..."
if ! gpg --verify "$asc_file" "$zip_file" 2>/dev/null; then
    echo "[ERROR] GPG verification failed! Aborting update."
    exit 1
fi

echo "[INFO] Signature verified successfully."

# ----------------------------------------------------------------------
# 7. Install new version
# ----------------------------------------------------------------------
echo "[INFO] Installing update..."

EXTRACTED_DIR="$tmp_dir/select-freeboxos-sbc-vm-${VERSION}"

unzip -q "$zip_file" -d "$tmp_dir"

if [ -d "$INSTALL_DIR" ]; then
    mv "$INSTALL_DIR" "$INSTALL_DIR.old"
fi

echo "[INFO] Installing new version..."
mv "$EXTRACTED_DIR" "$INSTALL_DIR"

rm -rf "$INSTALL_DIR.old"

# ----------------------------------------------------------------------
# 8. Save installed version
# ----------------------------------------------------------------------
echo "$latest_tag" > "$LAST_RELEASE_FILE"

echo "[INFO] Update to $latest_tag completed successfully."

rm -rf "$tmp_dir"
exit 0
