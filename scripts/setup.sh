script_dir="$(dirname "$(realpath "$0")")"
optdesc(){
    echo -n "    $1: $2|$3 " >&2
    local def="$4"
    if [[ "$5" == "@" ]]; then
        echo -n "value" >&2
    else
        echo -n "(\"$5\" if set)" >&2
    fi
    echo ": $6 (default: \"$4\")" >&2
}
argdesc(){
    local is_auto=false; local is_pass=false; local mandatory=false
    while true; do case "$(echo "$1")" in
        -y) is_auto=true; shift;; # -y is auto
        -p) is_pass=true; shift;;   # -p is password
        -m) mandatory=true; shift;;
        *) break;; esac; done
    echo -n "    $1: $3 (default: '$2'" >&2
    $is_auto && echo -n ", do not prompt" >&2
    $is_pass && echo -n ", password" >&2
    $mandatory && echo -n ", mandatory" >&2
    echo ")" >&2
}
usage(){
    echo "$(basename $0): $(grep -E "^# USAGE " $0 | sed 's/# USAGE //')" >&2
    echo "  Options:" >&2
    local opts="$(grep -E "^opt " ${BASH_SOURCE[0]} | sed -e 's/opt/optdesc/' -e 's/\\$/@/g')"
    while IFS= read -r l; do eval "$l"; done <<< "$opts"
    local opts="$(grep -E "^opt " $0 | sed -e 's/opt/optdesc/' -e 's/\\$/@/g')"
    while IFS= read -r l; do eval "$l"; done <<< "$opts"
    local args="$(grep -E "^arg " $0 | sed -e 's/arg/argdesc/' -e 's/\$/@/g' -e 's/@yes//g')"
    if [[ "$args" != "" ]]; then echo "  Parameters:" >&2; fi
    while IFS= read -r l; do eval "$l"; done <<< "$args"
    exit $1
}
fatal_error() {
    echo "Error: $1" >&2
    echo >&2
    echo "Fatal error" >&2
    exit 1
}
handle_error() {
    fatal_error "[$1] occured on command [$2: $3]"
}
askParam() {
    local not_auto=true; local is_pass=false
    while true; do case "$1" in
        -y) not_auto=false; shift;; # -y is auto
        -p) is_pass=true; shift;;   # -p is password
        *) break;; esac; done
    local var_name=$1;shift         # Parameter name
    local def="$1";shift            # Default value
    local prompt="$1";shift||:      # Parameter description (optionnal)
    local read_silent=""; $is_pass && read_silent="-s"
    local -n var=$var_name
    [[ "${var}" != "" ]] && def="${var}"
    [[ "$prompt" == "" ]] && prompt="Enter $var_name"
    if [[ "$def" == "" ]]; then prompt="$prompt"
    elif $is_pass; then prompt="$prompt [********]"
    else prompt="$prompt [$def]"; fi
    if $not_auto || [[ "$def" == "" ]]; then read -r -e $read_silent -p "$prompt : " var; else echo "$prompt"; fi
    if [[ "$var" == "" ]]; then var="$def"; fi
}
shift_args() { script_args=("${script_args[@]:1}"); }
arg() {
    local auto=""
    local pass=""
    local mandatory=false
    while true; do case "$1" in
        -y) auto="-y"; shift;;      # option -y for askParam (auto)
        -p) pass="-p"; shift;;      # option -p for askParam (password)
        -m) mandatory=true; shift;; # mandatory argument
        *) break;; esac; done
    local arg_name=$1; shift
    local def="$1"; shift
    local desc="$1"; shift||:
    local -n arg=$arg_name;
    local curarg=${script_args[0]}; shift_args
    [[ "$curarg" == "" ]] && askParam $yes $pass $arg_name "$def" "$desc" || arg=$curarg
    if $mandatory && [[ "${arg}" == "" ]]; then echo "Argument $arg_name is mandatory" >&2; usage 1; fi
}
opt() {
    local opt_name=$1; shift # Name of the option variable
    local opt_short=$1; shift # short option
    local opt_long=$1; shift # long option
    local opt_def=$1; shift # default value
    local opt_val=$1; shift # value if present; special value '@' indicate that option need an argument
    local -n opt=$opt_name
    opt=$opt_def
    for ((i=0;i<${#script_args[@]};i++)); do
        if [[ "${script_args[i]}" == "$opt_short" || "${script_args[i]}" == "$opt_long" ]]; then
            if [[ "${opt_val}" == "@" ]]; then
                opt=${script_args[i+1]}
                script_args=("${script_args[@]::i}" "${script_args[@]:i+2}")
            else
                opt=$opt_val
                script_args=("${script_args[@]::i}" "${script_args[@]:i+1}")
            fi
            break;
        fi
    done
}

#---------------------------------------------------------------
set -E # the ERR trap is inherited by shell functions
trap 'handle_error "$?" "$LINENO" "$(eval echo "$BASH_COMMAND")"' ERR

cur_dir=$(pwd)
script_args=("$@")

opt yes -y --yes '' -y 'Uses default values'
opt help -h --help '' -h 'Display this help'
if [[ "$help" == "-h" ]] then usage 0; fi

# USAGE Setup osc2mqtt with docker compose
arg $yes INSTALL_DIR /opt/osc2mqtt "Installation directory"
if [[ -e "$INSTALL_DIR" ]]; then
    echo "$INSTALL_DIR already exists"
else
    echo "Creating $INSTALL_DIR"
    mkdir -p "$INSTALL_DIR"
fi
cd "$INSTALL_DIR"
if [[ ! -f docker-compose.yaml ]]; then
    echo "Copying docker-compose.yaml to $INSTALL_DIR"
    if [[ -f "$script_dir/../docker/docker-compose.yaml" ]]; then
        cp "$script_dir/../docker/docker-compose.yaml" "$INSTALL_DIR"
    else
        echo "docker-compose.yaml not found locally, downloading from the repository"
arg $yes REPO https://github.com/ldebs/osc2mqtt/raw/refs/heads/master "Repository URL to download files from"
        wget -q $REPO/docker/docker-compose.yaml -O "$INSTALL_DIR/docker-compose.yaml"
    fi
else
    echo "docker-compose.yaml already exists in $INSTALL_DIR"
fi
if [[ ! -e $INSTALL_DIR/config ]]; then
    echo "Creating config directory in $INSTALL_DIR"
    mkdir -p "$INSTALL_DIR/config"
else
    echo "Config directory already exists in $INSTALL_DIR"
fi
if [[ ! -e $INSTALL_DIR/config/config.yaml ]]; then
    echo "Creating default config.yaml in $INSTALL_DIR/config"
    if [[ -f "$script_dir/../src/config.yaml.example" ]]; then
        echo "Copying config.yaml from $script_dir/../src/config.yaml.example"
        cp "$script_dir/../src/config.yaml.example" "$INSTALL_DIR/config/config.yaml"
    else
        echo "config.yaml not found locally"
        echo "Downloading default config.yaml from the repository"
        [[ "$REPO" == "" ]] && askParam REPO https://github.com/ldebs/osc2mqtt/raw/refs/heads/master "Repository URL to download files from"
        wget -q $REPO/src/config.yaml.example -O "$INSTALL_DIR/config/config.yaml"
    fi
    echo "Updating config.yaml"
    echo "## MQTT connection settings"
arg $yes BROKER localhost "MQTT broker address"
arg $yes MQTT_PORT 8883 "MQTT broker port (mqtt default: non-TLS=1883 TLS=8883)"
arg $yes CLIENT_ID osc-to-mqtt "MQTT client ID"
arg $yes USERNAME "mqtt_user" "MQTT username"
arg $yes -p PASSWORD "" "MQTT password"
arg $yes CA "" "CA certificate file (optional, for TLS connections)"
    sed -i \
        -e "s|broker:.*|broker: \"$BROKER\"|" \
        -e "s|port:.*|port: $MQTT_PORT|" \
        -e "s|client_id:.*|client_id: \"$CLIENT_ID\"|" \
        -e "s|username:.*|username: \"$USERNAME\"|" \
        -e "s|password:.*|password: \"$PASSWORD\"|" \
        -e "s|ca_certs:.*|ca_certs: \"$CA\"|" \
        "$INSTALL_DIR/config/config.yaml"
    echo "## MQTT topics settings"
arg $yes TOPIC_PUBLISH "osc/stat" "MQTT topic to publish OSC messages"
arg $yes TOPIC_SUBSCRIBE "osc/cmnd/openSC" "MQTT topic to subscribe"
    sed -i \
        -e "s|publish:.*|publish: \"$TOPIC_PUBLISH\"|" \
        -e "s|subscribe:.*|subscribe: \"$TOPIC_SUBSCRIBE\"|" \
        "$INSTALL_DIR/config/config.yaml"
    echo "## OSC listener settings"
arg $yes OSC_NET "0.0.0.0" "OSC listener incoming network address"
arg $yes OSC_PORT 57272 "OSC listener port"
arg $yes OSC_MAX_CONNECTIONS 10 "Maximum number of connections to the OSC listener"
arg $yes OSC_UNIX_SOCKET "/tmp/osc.sock" "OSC listener Unix socket path"
    awk -v n="$OSC_NET" \
       -v p="$OSC_PORT" \
       -v m="$OSC_MAX_CONNECTIONS" \
       -v u="$OSC_UNIX_SOCKET" '\
       /net:/              {sub(/net:.*/, "net: \"" n "\"")}
       /osc:/              {osc=1}
       /port:/             {if(osc) {sub(/port:.*/, "port: " p)}} 
       /max_connections:/  {sub(/max_connections:.*/, "max_connections: " m)}
       /unix_socket_path:/ {sub(/unix_socket_path:.*/, "unix_socket_path: \"" u "\"")}
       {print $0}' "$INSTALL_DIR/config/config.yaml" > "$INSTALL_DIR/config/config.yaml.tmp"
    mv "$INSTALL_DIR/config/config.yaml.tmp" "$INSTALL_DIR/config/config.yaml"
    echo "config.yaml updated with user settings"
    echo "You can edit $INSTALL_DIR/config/config.yaml to change settings"
    echo "To start osc2mqtt, run 'docker compose up -d' in $INSTALL_DIR"
else
    fatal_error "config.yaml already exists in $INSTALL_DIR/config"
fi