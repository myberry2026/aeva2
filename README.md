# AEVA2: Android Edge Vision Agent

AEVA2 is a unified framework for on-device Android automation, combining a low-latency communication bridge with an intelligent agent powered by vision-language models.

## Project Structure

- `bridge-android/`: The Android-side relay and bridge infrastructure. Handles communication between the device and the agent.
- `termux-agent/`: The intelligent agent designed to run in Termux (or remotely) to control the Android device via the bridge.

## Prerequisites

### Hardware Requirements
- **RAM**: Your Android device **must have at least 8GB of RAM**. The on-device AI models (LiteRT-LM) require significant memory to load and run efficiently. Devices with less than 8GB will likely crash or fail to load the model.

### Software Prerequisites
- **Android Device**: With Developer Options and USB Debugging enabled.
- **Termux**: **CRITICAL**. You must install Termux to run the agent on your phone.
    - **DO NOT** use the Google Play Store version (it is outdated and broken).
    - **Install from F-Droid**: Download the F-Droid APK from [f-droid.org](https://f-droid.org/), search for "Termux", and install it. This is the official, open-source, and up-to-date version.
- **ADB**: Installed on your host machine.
- **Java 21 (OpenJDK)**: Required for compiling the bridge.
- **Python 3.10+**: Required for the agent and relay scripts.

## Quick Start: Launching Both Components

To launch the full AEVA2 stack, follow these steps:

### 1. Setup and Deploy the Android Bridge

Navigate to the `bridge-android` directory, build the project, and deploy it to your device:

```bash
cd bridge-android
./scripts/build_local.sh && ./scripts/deploy_local.sh
```

### 2. Launch the Termux Agent Server

In a separate terminal, navigate to the `termux-agent` directory and start the server:

```bash
cd termux-agent
./scripts/run_termux_server.sh
```

### 3. Verification

Check the terminal outputs. The bridge should be deployed and running on the device, and the Termux server should be listening for connections. The agent will then be able to control the device through this unified channel.

## How It Works: Under the Hood

For developers and curious users, here is what happens when you run those commands.

### 1. The Build Process (`build_local.sh`)
When you run the build script, your computer acts as a **factory**:
- **Dependencies**: You need **JDK 21** (Java) and the **Android SDK**. Java runs the compiler, and the SDK provides the "blueprints" for Android apps.
- **Gradle**: We use a tool called Gradle to fetch libraries and compile the Kotlin code into an **APK** (Android Package) file.
- **Result**: A file named `app-debug.apk` is created. This is the "Bridge" that will live on your phone.

### 2. The Deployment (`deploy_local.sh`)
This script handles the "delivery" of the app to your device:
- **The Jump Host**: Often, your development machine isn't the one physically connected to the phone. We use `scp` to send the APK to a "Jump Host" (a machine named `win` in our scripts) that has the USB connection.
- **ADB (Android Debug Bridge)**: This is the most critical tool. It communicates over USB to the phone.
- **Smart Installation**: We use `adb install -r -t -g`.
    - `-r`: Replaces the old version but keeps your settings.
    - `-t`: Allows "Test" apps to be installed.
    - `-g`: **Crucial!** It automatically grants all permissions (Camera, Files, Accessibility) so you don't have to click "Allow" dozens of times on the phone.

### 3. The Tunnels (The Secret to Connectivity)
The phone and the computer need to talk to each other. Since they are on different networks or behind firewalls, we use **ADB Tunnels**:
- **ADB Forward**: Allows your computer to "call" the phone (e.g., to ask for a screenshot).
- **ADB Reverse**: Allows the phone to "call" your computer (e.g., to send an alert or event).
- This creates a **two-way bridge** over a simple USB cable.

### 4. The Agent Server (`run_termux_server.sh`)
Finally, we start the "Brain":
- It deploys Python scripts into the **Termux** environment on your phone.
- It starts a **Daemon** (a background worker) that stays alive even if you close the terminal.
- **On-Device AI**: It loads a machine learning model (LiteRT-LM) onto the phone's GPU. This allows the phone to "see" and "think" locally without sending your data to the cloud.

## Summary of Dependencies

To be a developer on this project, you need:
1. **Java 21 (OpenJDK)**: For compiling the Android code.
2. **Android SDK & Build Tools**: For packaging the APK.
3. **ADB (Android Debug Bridge)**: For USB communication.
4. **Python 3.10+**: For running the Agent and Relay scripts.
5. **SSH & SCP**: For remote deployment if your phone is connected to a different machine.

## License

See the `LICENSE` file for details.
