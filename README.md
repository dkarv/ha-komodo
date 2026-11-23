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

The easiest way to install the Komodo integration is via the **Home Assistant Marketplace** (Home Assistant 2026.11 or newer).

[![Open your Home Assistant instance and open this repository in the Marketplace.](https://my.home-assistant.io/badges/marketplace_repository.svg)](https://my.home-assistant.io/redirect/marketplace_repository/?owner=dkarv&repository=ha-komodo&category=integration)

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
   - **Enable container CPU / memory / network / disk I/O sensors** (optional): Enables the per-container diagnostic sensors of that category (see below).
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
| Deploy `<Stack Name>` stack | Button | Deploys the stack |
| `<Service Name>` | Switch | Reflects the running state of the service; toggle to start or stop it |
| `<Service Name>` Update | Update | Tracks available image updates and allows triggering them |

### Container Sensors

For every service the stack device additionally gets diagnostic sensors with the container's resource usage, as reported by `docker stats`:

| Entity | Description |
|---|---|
| `<Service Name>` CPU Usage | CPU usage of the container in % (can exceed 100% on multi-core hosts) |
| `<Service Name>` Memory | Memory used by the container |
| `<Service Name>` Network Received / Sent | Total network traffic of the container |
| `<Service Name>` Disk Read / Written | Total block I/O of the container |

These sensors are **disabled by default**. Enable them for all containers at once per category (CPU, memory, network, disk I/O) with the **Enable container ... sensors** options (during setup, or later via **Configure** on the integration), or enable single sensors in the entity settings. They have no state class, so Home Assistant does not keep long-term statistics for them.


## Disclaimer

This integration is an **independent, community-maintained project** and is **not affiliated with, endorsed by, or officially associated with the Komodo project** or its developers.

## Contributing

In case you have any suggestion or problem, feel free to open an Issue. I'm open to any pull requests with fixes or new features. For bigger changes please approach me beforehand to coordinate.
