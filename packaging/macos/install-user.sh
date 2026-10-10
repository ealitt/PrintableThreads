#!/bin/sh
# Used by the package and by isolated installation tests. No Python dependency.
set -eu
source_dir=$1
user_home=$2
user_name=$3
parent="$user_home/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns"
target="$parent/PrintableThreads"
backup=""
stage=""
committed=false
cleanup() {
    if [ "$committed" = false ]; then
        [ -z "$stage" ] || /bin/rm -rf "$stage"
        if [ -n "$backup" ] && [ ! -e "$target" ]; then /bin/mv "$backup" "$target"; fi
    fi
}
trap cleanup EXIT
[ -f "$source_dir/PrintableThreads.manifest" ] || exit 1
case "$user_home" in /*) ;; *) echo 'Invalid home directory' >&2; exit 1 ;; esac
[ "$user_home" != / ] && [ "$user_home" != /var/root ] || exit 1
# Never follow an add-in destination symlink while installing as root.
for path in "$user_home/Library" "$user_home/Library/Application Support" \
    "$user_home/Library/Application Support/Autodesk" \
    "$user_home/Library/Application Support/Autodesk/Autodesk Fusion 360" \
    "$parent/.." "$parent" "$target" "$parent/../PrintableThreads-backups"; do
    [ ! -L "$path" ] || { echo "Refusing symbolic link: $path" >&2; exit 1; }
done
mkdir -p "$parent"
stage=$(/usr/bin/mktemp -d "$parent/.PrintableThreads-install.XXXXXX")
/usr/bin/ditto "$source_dir" "$stage"
if [ "$(id -u)" = 0 ]; then
    /usr/sbin/chown -R "$user_name" "$stage"
    # Ensure first-time API folders are writable by the Fusion user.
    for path in "$parent" "$parent/.." "$parent/../.." "$user_home/Library/Application Support/Autodesk"; do
        /usr/sbin/chown "$user_name" "$path"
    done
fi
if [ -e "$target" ]; then
    backup_parent="$parent/../PrintableThreads-backups"
    mkdir -p "$backup_parent"
    backup=$(/usr/bin/mktemp -d "$backup_parent/$(date +%Y%m%d-%H%M%S).XXXXXX")
    /bin/rmdir "$backup"
    /bin/mv "$target" "$backup"
    if [ "$(id -u)" = 0 ]; then /usr/sbin/chown "$user_name" "$backup_parent"; fi
fi
/bin/mv "$stage" "$target"
committed=true
echo "Installed PrintableThreads in $target"
[ -z "$backup" ] || echo "Previous version saved in $backup"
