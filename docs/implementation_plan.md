# Godown Vehicle Tracking System Plan

This document outlines the plan to upgrade your ALPR system to track vehicle Entry and Exit times, and to display this data in a React Native mobile application.

## Current State Analysis
- **ALPR Script (`detect.py`)**: Currently detects license plates and writes *every* valid detection to `detections.csv`. It has a basic 30-second delay logic to avoid spamming the CSV, but it lacks the stateful logic required to distinguish between an "Entry" and an "Exit".
- **Integration**: The React Native app needs a way to communicate with your Python script to retrieve data. A mobile app cannot read a local CSV file directly from your computer without a web server.

## Proposed Architecture

1. **Stateful Database (SQLite)**: We will replace the CSV logging with a lightweight SQLite database. This allows us to track the *state* of a vehicle (whether it is currently inside the godown or has exited).
2. **REST API (FastAPI)**: We will create a simple Python API server. This server will read from the SQLite database and provide the data to the React Native app over your local Wi-Fi network.
3. **React Native App (Expo)**: A mobile application that fetches the data from the API and displays a beautiful dashboard of vehicles, showing their entry time, exit time, and current status (Inside/Exited).

---

## Open Questions

> [!WARNING]
> Please review and provide feedback on the following before we begin execution:
> 1. **Exit Logic**: How long should a vehicle be "inside" before a new detection is considered an "Exit"? For example, if the camera sees the plate, it's an "Entry". If it sees the same plate 5 minutes later, is that the "Exit"? 
> 2. **Camera Setup**: Are you using a single camera for both the entry and exit gate? If yes, the time-delay logic (e.g., ignoring detections for 2 minutes after entry, and counting the next detection as an exit) is the best approach.
> 3. **Mobile App**: We will use Expo for the React Native app as it's the standard for quick and reliable setup. Is that acceptable?

---

## Proposed Changes

### 1. ALPR Logic & Database Upgrade

#### [MODIFY] `detect.py` (or create a new `tracker.py`)
- Integrate SQLite instead of CSV.
- Create a `vehicles` table: `id`, `plate_number`, `entry_time`, `exit_time`, `status`.
- **Logic Update**:
  - **Entry**: When a plate is detected, query the DB. If the plate is not currently "Inside", create a new record with the current time as `entry_time` and status as "Inside".
  - **Exit**: If the plate is detected and its status is "Inside", check the time difference. If sufficient time has passed (e.g., > 2 minutes, to avoid false double-triggers at the gate), update the record with `exit_time` and status as "Exited".

### 2. Backend API

#### [NEW] `api.py`
- Create a FastAPI web server.
- Expose an endpoint: `GET /vehicles` that returns a JSON list of all vehicles, their entry/exit times, and status.
- Allow Cross-Origin Resource Sharing (CORS) so the React Native app can communicate with it.

### 3. React Native Mobile App

#### [NEW] `react-native-app/` (Expo Project)
- Initialize a new React Native project using Expo.
- **UI Design**: 
  - A clean, modern dashboard.
  - A list or table view displaying: Vehicle Plate | Entry Time | Exit Time | Status (Green for Inside, Gray for Exited).
  - Auto-refresh functionality (polling the API every 3-5 seconds) so the app updates in real-time as vehicles enter/exit.

## Verification Plan

### Automated/Manual Testing
1. **Script Verification**: Run `detect.py` manually and point the camera at a test license plate. Verify it registers as "Entry" in the database. Wait for the cooldown period, show the plate again, and verify it registers as "Exit".
2. **API Testing**: Navigate to the FastAPI endpoint in the browser to ensure JSON data is being served correctly.
3. **Mobile App Testing**: Run the Expo app on an emulator or physical device. Ensure the dashboard successfully fetches data from the API and displays the correct entry/exit times.
