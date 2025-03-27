#!/bin/bash
# shellcheck disable=SC1090,SC1091

## resolve folder of this script, following all symlinks,
## http://stackoverflow.com/questions/59895/can-a-bash-script-tell-what-directory-its-stored-in
SCRIPT_SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SCRIPT_SOURCE" ]; do # resolve $SOURCE until the file is no longer a symlink
  SCRIPT_DIR="$(cd -P "$(dirname "$SCRIPT_SOURCE")" && pwd)"
  SCRIPT_SOURCE="$(readlink "$SCRIPT_SOURCE")"
  # if $SOURCE was a relative symlink, we need to resolve it relative to the path where the symlink file was located
  [[ $SCRIPT_SOURCE != /* ]] && SCRIPT_SOURCE="$SCRIPT_DIR/$SCRIPT_SOURCE"
done
SCRIPT_DIR="$(cd -P "$(dirname "$SCRIPT_SOURCE")" && pwd)"
readonly SCRIPT_DIR

set -x
set -e
set -o pipefail

sudo dnf install -y rpm-build python3 python3-setuptools mock

sudo dnf -y upgrade distribution-gpg-keys mock
sudo dnf install -y pip
sudo pip install virtualenv
sudo pip install urllib3

sudo usermod -aG mock tester

echo "config_opts['plugin_conf']['overlayfs_enable'] = True" | sudo tee --append /etc/mock/site-defaults.cfg
echo "config_opts['plugin_conf']['root_cache_enable'] = False" | sudo tee --append /etc/mock/site-defaults.cfg
echo "config_opts['plugin_conf']['overlayfs_opts']['base_dir'] = '/var/lib/MOCK_OVERLAYFS'" | sudo tee --append /etc/mock/site-defaults.cfg

sudo mock --dnf -r fedora-rawhide-x86_64 --scrub all

PARAM=73

if [ "x$INPUT" != "x" ]; then
	mv $INPUT/* $SCRIPT_DIR/../rpms
fi

cd $SCRIPT_DIR/.. && python3 $SCRIPT_DIR/../main.py --diewith $PARAM | tee $SCRIPT_DIR/../stdout.log

if [ "x$OUTPUT" != "x" ]; then
	mv $SCRIPT_DIR/../jtregLogs/* $OUTPUT
fi
