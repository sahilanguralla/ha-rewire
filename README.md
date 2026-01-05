# RewIRe for Home Assistant

**RewIRe** is a generic Home Assistant integration that transforms any "dumb" IR-controlled device into a smart entity. It works by wrapping your existing IR blaster (like Broadlink, ESPHome, or Tuya) into a full-featured Home Assistant entity (Fan, Climate, Light, etc.) with state estimation.

## Features

- **Standard Entities**: Creates proper `fan`, `climate` (AC), and `light` entities.
- **Template Configuration**: Easy setup for standard devices by asking for specific IR codes (Power, Speed, Temperature, etc.).
- **Smart Delays**: Automatically adds delays (e.g., 300ms for AC temperature changes) to ensure commands are received reliably.
- **State Estimation**: Remembers the state of your device (e.g., current speed or temperature) even though the IR communication is one-way.
- **Legacy Support**: A generic "Other" mode allows you to build custom button/switch panels for non-standard devices.

## Installation

### Via HACS
1.  Add this repository to `HACS > Integrations > 3 dots > Custom repositories`.
    ```
    https://github.com/sahilanguralla/hacs.git
    ```
2.  Search for **RewIRe** and install.
3.  Restart Home Assistant.

## Configuration

1.  Go to **Settings > Devices & Services**.
2.  Click **Add Integration** and search for **RewIRe**.
3.  **Step 1**: Select your IR Blaster entity (e.g., `remote.broadlink_living_room`) and the command service (usually `remote.send_command`).
4.  **Step 2**: Select your **Device Type**:

### Fan
-   **Required**: Power On, Power Off.
-   **Optional**: Oscillate, Speed Increase, Speed Decrease.
-   *Result*: A `fan` entity with speed and oscillation controls.

### AC (Climate)
-   **Required**: Power On, Power Off, Temperature Increase, Temperature Decrease.
-   *Result*: A `climate` entity. Temperature adjustments are sent with a 300ms delay between codes to ensure reliability.

### Light
-   **Required**: Power On, Power Off.
-   **Optional**: Brightness Increase, Brightness Decrease.
-   *Result*: A `light` entity.

### Other / Legacy
-   Choose "Other" to manually add individual Actions (Power Button, Speed Button, etc.).
-   This creates individual `switch`, `button`, or `number` entities for each action.

## Usage

Once configured, your device appears as a standard Home Assistant entity. You can control it using Dashboard cards, Voice Assistants (Google/Alexa), or Automation.

### Syncing State
Since IR is one-way, Home Assistant guesses the state based on the commands it sent. If the device state gets out of sync (e.g., someone used the physical remote):
-   Use the Home Assistant UI to toggle the device Off and On again to reset the assumed state.

## Development

### Setup
1. Install development dependencies:
   ```bash
   pip install -r requirements_tests.txt
   ```

2. Setup git hooks:
   ```bash
   ./scripts/setup-hooks.sh
   ```

### Committing Changes
- **Interactive Mode**: Run `git commit` (without `-m`) to launch the interactive commit wizard
- **Manual Mode**: Run `git commit -m "feat(scope): description"` to write your own message
- All commits are validated against [Conventional Commits](https://www.conventionalcommits.org/) format
