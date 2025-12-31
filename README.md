# Komodo Home Assistant Integration

A Home Assistant custom integration for monitoring your [Komodo](https://github.com/mbecker20/komodo) instance. It allows you to monitor your Komodo-managed servers, Docker stacks, and alerts directly from Home Assistant.

## Capabilities

This integration allows you to:
- Track server states
- Monitor Docker stack states
- Get notified about available container updates and install them
- View unresolved alerts (WiP)

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

### Entities

| Entity ID Format | Description | States |
|------------------|-------------|---------|
| `sensor.komodo_server_{server_name}_state` | Shows the current state of each server | `Running`, `Stopped`, `Unknown` |
| `sensor.komodo_stack_{stack_name}_state` | Shows the current state of each Docker stack | `Running`, `Stopped`, `Unknown`, `Deploying` |
| `sensor.komodo_alert_alertcount` | Number of unresolved alerts | Numeric count |
| `sensor.komodo_alert_alerts` | Types of current alerts | Comma-separated list of alert types |
|------------------|-------------|
| `update.komodo_{stack_name}_{service_name}` | Shows available updates for container services |

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

Enable debug logging on the integrations page before creating an issue.

## Support

- **Issues**: [GitHub Issues](https://github.com/dkarv/ha-komodo/issues)
- **Komodo Documentation**: [Komodo GitHub](https://github.com/mbecker20/komodo)

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.
