# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Commands

### Running the Application
```bash
python web.py               # Start the main dashboard server (port 8000)
python ros_api_server.py    # Start ROS API bridge server (port 8091)
```

### Configuration Management
```bash
cp config.yaml.example config.yaml    # Initialize configuration
cp .env.example .env                   # Initialize environment variables
python add_robot.py add                # Interactive robot addition
python add_robot.py list               # List configured robots
```

### Dependencies
```bash
pip install -e .                      # Install package in development mode
pip install -e ".[dev]"               # Install with development dependencies
```

### Code Quality
```bash
black .                               # Format code
isort .                               # Sort imports  
flake8 .                              # Lint code
bandit -r .                           # Security scan
mypy .                                # Type checking
```

### Testing
```bash
pytest                                # Run tests
pytest --cov                         # Run tests with coverage
```

## Architecture Overview

### Backend Structure
- **web.py**: Main Flask server providing the dashboard interface and REST API
- **ping_addresses.py**: Robot connectivity monitoring with MultiPingChecker
- **motorReader.py**: ROS-based motor data collection from robots via SSH
- **ros_api_server.py**: ROS API bridge for robot control commands
- **rmHelper.py**: Utility functions for robot management

### Frontend Structure
- **static/index.html**: Single-page application entry point
- **static/js/main.js**: Vue.js application setup with 1Hz motor data updates
- **static/js/components/**: Modular Vue components for different dashboard sections
- **static/js/services/**: Data service layer for API communication

### Configuration System
- **config.yaml**: Central robot configuration file (YAML format)
- **RobotConfig class**: Centralized configuration loader in ping_addresses.py
- **.env**: Environment variables for API keys and credentials

### Key Data Flow
1. **Robot Status**: MultiPingChecker monitors connectivity via ping
2. **Motor Data**: MotorController collects data via SSH + ROS topics at 1Hz
3. **API Layer**: Flask REST API serves data to frontend
4. **Real-time Updates**: Frontend polls at 1Hz for motor data, 5s for general status

### Robot Control Architecture
- **ROS Commands**: Sent via ros_api_server.py bridge (pause, resume, stop, etc.)
- **Existing API Commands**: Direct HTTP calls to robot APIs (charging, navigation, etc.)
- **Command Routing**: web.py routes commands based on type (ROS_COMMANDS vs EXISTING_API_COMMANDS)

### Motor Data Collection
- Uses SSH to connect to robots and run ROS commands
- Collects position, velocity, and current data from motor topics
- Data aggregated and served via /api/robot-status endpoint
- Requires has_motors: true in robot configuration

## Configuration Requirements

### Robot Configuration (config.yaml)
```yaml
flexa:
  robot_name:
    name: "robot_name"
    ip: "192.168.1.100"
    has_motors: true  # Enable motor data collection
```

### Environment Variables (.env)
- API_BASE_URL: Robot API base URL
- API_AUTH_KEY: Authorization key for robot APIs
- SSH credentials for motor data collection

## Important Notes

- Motor data updates run at exactly 1Hz (1000ms intervals)
- Robot configuration supports hot-reload without server restart
- All robot management can be done via YAML config, CLI tool, or REST API
- ROS Noetic required for motor data collection functionality
- SSH access to robots required for motor data features