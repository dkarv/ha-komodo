# HA-Komodo

## 🦎 Monitor Your Komodo Infrastructure in Home Assistant

The **HA-Komodo** integration connects Home Assistant directly to your Komodo instance, pulling live information about your servers and stacks and organizing them into dedicated devices.

For each **server** connected to your Komodo instance, a device is created containing key sensors such as stack count, service count, server status, and alert count. For each **stack**, a dedicated device is created that exposes:

- A **status sensor** for the stack itself.
- A **button entity** to deploy the stack.
- A **switch entity per service** — reflecting the current running state and allowing you to start or stop each service directly from Home Assistant.
- An **update entity per service** — so you can track and trigger image updates from your dashboard.

This gives you full visibility and basic control over your Komodo-managed infrastructure, all from within Home Assistant.

***

## Installation

### 1. Installation via HACS My Home Assistant (Recommended)

The easiest way to install the Komodo integration is via HACS.

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=dkarv&repository=ha-komodo&category=integration)

### 2. Installation via HACS Manually

HACS (Home Assistant Community Store) makes installation and updates simple. Since this is a custom component, you must first add the repository to HACS.

1. In Home Assistant, go to **HACS**.
2. Go to the **Integrations** tab.
3. Click the three dots **(⋮)** in the top right corner and select **Custom repositories**.
4. Enter the URL: `https://github.com/dkarv/ha-komodo`
5. Select **Integration** as the Category.
6. Click **ADD**.
7. After the repository is added, search for **"Komodo"** in the HACS Integrations section and click **Download**.
8. **Restart Home Assistant** to load the new integration.

### 3. Manual Installation

1. Download the latest release zip file from the [GitHub releases page](https://github.com/dkarv/ha-komodo/releases).
2. Extract the contents. You should find a folder named `ha-komodo`.
3. Copy the entire `ha-komodo` folder into your Home Assistant configuration directory under `custom_components/`.
   - **Resulting Path:** `config/custom_components/komodo/`
4. **Restart Home Assistant** to load the new integration.

***

## Configuration

### Home Assistant Setup

1. In Home Assistant, navigate to **Settings** > **Devices & Services**.
2. Click the **+ ADD INTEGRATION** button.
3. Search for **"Komodo"**.
4. You will be prompted to enter the following:
   - **Host:** The URL of your Komodo instance (e.g., `http://192.168.1.100:9120`).
   - **API Key:** Your Komodo API key.
   - **API Secret:** Your Komodo API secret.
5. Click **SUBMIT**. The integration will connect to your Komodo instance and create devices and entities automatically.

***

## Devices & Entities

Once configured, the integration creates one device per server and one device per stack found in your Komodo instance.

### Server Device

Each server gets a device with the following entities:

| Entity | Type | Description |
|---|---|---|
| Server Status | Sensor | The current status of the server (e.g., `Ok`, `NotOk`) |
| Stack Count | Sensor | Total number of stacks on the server |
| Service Count | Sensor | Total number of services across all stacks |
| Alert Count | Sensor | Number of active alerts on the server |

### Stack Device

Each stack gets its own device with entities for every service it contains:

| Entity | Type | Description |
|---|---|---|
| Stack Status | Sensor | The current state of the stack (e.g., `Running`, `Down`) |
| `<Service Name>` | Switch | Reflects the running state of the service; toggle to start or stop it |
| `<Service Name>` Update | Update | Tracks available image updates and allows triggering them |


## Disclaimer

This integration is an **independent, community-maintained project** and is **not affiliated with, endorsed by, or officially associated with the Komodo project** or its developers.

## Contributing

In case you have any suggestion or problem, feel free to open an Issue. I'm open to any pull requests with fixes or new features. For bigger changes please approach me beforehand to coordinate.
