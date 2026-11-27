"""Constants for the Laadpaal.io integration."""

DOMAIN = "laadpaal_io"

# Legacy key retained on automatically migrated entries for unique ID compatibility.
CONF_LOCATION_ID = "location_id"

# DOT-NL entry data keys.
CONF_FEATURE_ID = "feature_id"
CONF_ADDRESS = "address"
CONF_CPO_ID = "cpo_id"
CONF_MANUFACTURER = "manufacturer"

# Search radius in meters
SEARCH_RADIUS_METERS = 100.0
POLL_RADIUS_METERS = 10.0
MIGRATION_RADIUS_METERS = 2.0

# Repair issue ID prefix
MIGRATION_ISSUE_PREFIX = "migration_reconfigure"
