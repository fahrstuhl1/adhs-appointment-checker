#!/usr/bin/with-contenv bashio
# ==============================================================================
# ADHS Appointment Checker — startup script
# Reads add-on options via bashio and launches the application.
# ==============================================================================

export LOG_LEVEL="$(bashio::config 'log_level')"
export DEFAULT_INTERVAL_MINUTES="$(bashio::config 'default_interval_minutes')"
export BASE_URL="$(bashio::config 'base_url')"
export CLIENT_ID="$(bashio::config 'client_id')"
export API_KEY="$(bashio::config 'api_key')"
export NOTIFY_SERVICE="$(bashio::config 'notify_service')"

# Persistent storage provided by the add-on (addon_config:rw -> /config)
export DATA_DIR="/config"

bashio::log.info "Starting ADHS Appointment Checker..."
bashio::log.info "Default interval: ${DEFAULT_INTERVAL_MINUTES} min | Base URL: ${BASE_URL}"

cd /app || bashio::exit.nok "Could not change into /app"

exec python3 -m app.main
