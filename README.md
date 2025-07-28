# Komodo Home Assistant Integration

A Home Assistant custom integration for monitoring [Komodo](https://github.com/mbecker20/komodo) - a self-hosted container and stack management platform. This integration allows you to monitor your Komodo-managed servers, Docker stacks, and alerts directly from your Home Assistant dashboard.

## What is Komodo?

Komodo is a modern, web-based platform for managing Docker containers and stacks across multiple servers. It provides features like:
- Multi-server container management
- Stack deployment and monitoring
- Alert system for infrastructure issues
- Container update notifications
- Resource monitoring

This integration brings Komodo monitoring capabilities into Home Assistant, allowing you to:
- Track server states (online/offline)
- Monitor Docker stack states
- View unresolved alerts
- Get notified about available container updates

## Installation

### Via HACS (Home Assistant Community Store)

1. **Add Custom Repository**
   - Open HACS in your Home Assistant instance
   - Click on **Integrations**
   - Click the three-dot menu in the top right
   - Select **Custom repositories**
   - Add `https://github.com/dkarv/ha-komodo` as repository
   - Select **Integration** as category
   - Click **Add**

2. **Install Integration**
   - Search for "Komodo" in HACS
   - Click **Download**
   - Restart Home Assistant

### Manual Installation

1. Download the `custom_components/komodo` folder from this repository
2. Copy it to your Home Assistant `custom_components` directory
3. Restart Home Assistant

## Setup

### Prerequisites

- A running Komodo instance accessible from your Home Assistant
- API credentials (API key and secret) from your Komodo instance

### Getting API Credentials

1. Log into your Komodo web interface
2. Navigate to **Settings** → **API Keys**
3. Create a new API key with appropriate permissions
4. Note down both the **API Key** and **API Secret**

### Configure Integration

1. In Home Assistant, go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for **Komodo**
4. Enter your configuration:
   - **Host**: The IP address or hostname of your Komodo instance (e.g., `192.168.1.100:9120` or `komodo.local:9120`)
   - **API Key**: Your Komodo API key
   - **API Secret**: Your Komodo API secret
5. Click **Submit**

The integration will test the connection and create entities for all discovered servers, stacks, and alerts.

## Entities

The integration creates several types of entities based on your Komodo configuration:

### Server Sensors

| Entity ID Format | Description | States |
|------------------|-------------|---------|
| `sensor.komodo_server_{server_name}_state` | Shows the current state of each server | `Running`, `Stopped`, `Unknown` |

### Stack Sensors

| Entity ID Format | Description | States |
|------------------|-------------|---------|
| `sensor.komodo_stack_{stack_name}_state` | Shows the current state of each Docker stack | `Running`, `Stopped`, `Unknown`, `Deploying` |

### Alert Sensors

| Entity ID Format | Description | Value |
|------------------|-------------|-------|
| `sensor.komodo_alert_alertcount` | Number of unresolved alerts | Numeric count |
| `sensor.komodo_alert_alerts` | Types of current alerts | Comma-separated list of alert types |

### Update Entities

| Entity ID Format | Description |
|------------------|-------------|
| `update.komodo_{stack_name}_{service_name}` | Shows available updates for container services |

## Usage Examples

### Automations

**Get notified when a server goes offline:**
```yaml
automation:
  - alias: "Komodo Server Offline Alert"
    trigger:
      - platform: state
        entity_id: sensor.komodo_server_production_state
        to: "Stopped"
    action:
      - service: notify.notify
        data:
          message: "Production server is offline!"
```

**Alert on new Komodo alerts:**
```yaml
automation:
  - alias: "Komodo New Alerts"
    trigger:
      - platform: numeric_state
        entity_id: sensor.komodo_alert_alertcount
        above: 0
    action:
      - service: notify.notify
        data:
          message: "Komodo has {{ states('sensor.komodo_alert_alertcount') }} unresolved alerts: {{ states('sensor.komodo_alert_alerts') }}"
```

### Dashboard Cards

**Server Status Card:**
```yaml
type: entities
title: Komodo Servers
entities:
  - sensor.komodo_server_production_state
  - sensor.komodo_server_staging_state
```

**Stack Overview:**
```yaml
type: entities
title: Docker Stacks
entities:
  - sensor.komodo_stack_webapp_state
  - sensor.komodo_stack_database_state
  - sensor.komodo_stack_monitoring_state
```

## Troubleshooting

### Connection Issues

- Verify your Komodo instance is accessible from Home Assistant
- Check that the host includes the correct port (default is usually 9120)
- Ensure API credentials are correct and have sufficient permissions

### Missing Entities

- Restart Home Assistant after adding new servers or stacks in Komodo
- Check the integration logs for any error messages
- Verify that your API key has permissions to read servers, stacks, and alerts

### Logs

Enable debug logging by adding this to your `configuration.yaml`:

```yaml
logger:
  logs:
    custom_components.komodo: debug
    komodo_api: debug
```

## Support

- **Issues**: [GitHub Issues](https://github.com/dkarv/ha-komodo/issues)
- **Komodo Documentation**: [Komodo GitHub](https://github.com/mbecker20/komodo)

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.
