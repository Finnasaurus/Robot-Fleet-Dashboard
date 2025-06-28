# 🤖 Robot Fleet Dashboard

*A comprehensive monitoring dashboard for robot fleet management*

[![CI](https://github.com/yourusername/robot-fleet-dashboard/workflows/CI/badge.svg)](https://github.com/yourusername/robot-fleet-dashboard/actions)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)


## 🤖 Development Story

**This entire project was built as a personal experiment to test Claude's capabilities while creating something practical for my company.**

Every aspect was developed through human-AI collaboration:
- 🏗️ **Architecture & Design** - Collaborative system design
- 💻 **Full-Stack Development** - Python backend, modern web frontend  
- 🔧 **DevOps & Configuration** - Dynamic config, security, deployment
- 📚 **Documentation** - Comprehensive guides and API docs
- 🛡️ **Security** - Data sanitization, proper .gitignore, credential management

**Result**: A production-ready robot fleet monitoring dashboard that evolved from a simple ping checker into a comprehensive management system.

*This showcases what's possible when human creativity meets AI capabilities.*

## ✨ Features

### 🎯 **Real-Time Monitoring**
- **Live robot status** with automatic updates
- **Battery level indicators** with visual bars and percentages
- **Connection status tracking** for all fleet robots
- **Error detection and alerting** with detailed error codes

### 📊 **Advanced Visualizations**
- **Motor data collection** at 1Hz for enabled robots
- **Real-time motor metrics** (position, velocity, current)
- **Interactive error summary** with expandable details
- **Battery health monitoring** with color-coded indicators

### ⚙️ **Dynamic Configuration**
- **YAML-based robot configuration** - no more hardcoded lists!
- **Hot-reload capability** - add robots without restarting
- **Flexible motor data enabling** per robot
- **RESTful API** for programmatic robot management

### 🎨 **Modern UI/UX**
- **Clean, professional interface** with intuitive color coding
- **Mobile-responsive design** for monitoring on any device
- **Self-explanatory visual language** - no legends needed
- **Error badges and status indicators** for quick problem identification

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- ROS Noetic (for motor data collection)
- SSH access to robot systems

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/robot-fleet-dashboard.git
   cd robot-fleet-dashboard
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure your robots**
   ```bash
   cp config.yaml.example config.yaml
   # Edit config.yaml with your robot details
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

5. **Start the dashboard**
   ```bash
   python web.py
   ```

6. **Access the dashboard**
   Open `http://localhost:8000` in your browser

## ⚙️ Configuration

### Adding Robots

Simply edit `config.yaml`:

```yaml
flexa:
  robot_name:
    name: "robot_name"
    ip: "192.168.1.100"
    has_motors: true  # Enable motor data collection
```

**That's it!** The dashboard will automatically detect the new robot on the next reload.

### Method 2: Command Line Tool

```bash
# Interactive mode (recommended)
python add_robot.py add

# Quick add
python add_robot.py add base1 --ip 192.168.1.100 --motors

# List all robots
python add_robot.py list

# Remove a robot
python add_robot.py remove base15
```

### Method 3: Web API

```bash
# Add robot
curl -X POST http://localhost:8000/api/robots \
  -H "Content-Type: application/json" \
  -d '{"id":"base1","name":"base1","ip":"192.168.1.100","has_motors":true}'

# List robots
curl http://localhost:8000/api/robots

# Update robot
curl -X PUT http://localhost:8000/api/robots/base15 \
  -H "Content-Type: application/json" \
  -d '{"has_motors":false}'

# Remove robot
curl -X DELETE http://localhost:8000/api/robots/base15
```

## 📁 Project Structure

```
.
├── version.py                # Version and project information
├── config.yaml              # ⭐ MAIN CONFIGURATION FILE - Edit this!
├── web.py                   # Flask web server
├── ping_addresses.py        # Robot ping management
├── motorReader.py           # Motor data collection
├── rmHelper.py              # Helper utilities
├── static/                  # Web assets
│   ├── css/
│   └── js/
├── msg/                     # ROS message definitions
├── logs/                    # Application logs
└── requirements.txt         # Python dependencies
```

## 🔧 Advanced Troubleshooting

### Configuration Issues
1. Check YAML syntax: `python validate_config.py`
2. Verify indentation (use spaces, not tabs)
3. Restart the dashboard

### Motor Data Not Working
1. Set `has_motors: true` in config.yaml
2. Check SSH credentials in .env
3. Verify robot has motor topics:
   ```bash
   ssh user@robot_ip "rostopic list | grep motor"
   ```

### Connection Issues
1. Ping the robot: `ping 192.168.1.xxx`
2. Check firewall settings
3. Verify robot is on the same network

### Port Already in Use
```bash
# Find process using port 8000
lsof -i :8000

# Kill the process
kill -9 <PID>
```

## 📝 API Documentation

### Get All Robots
```
GET /api/robots
```

### Get Robot Status
```
GET /api/robot-status
```

### Get Version Info
```
GET /api/about
```

### Add Robot
```
POST /api/robots
Body: {"id":"base1","name":"Base 1","ip":"192.168.1.100","has_motors":true}
```

### Update Robot
```
PUT /api/robots/<robot_id>
Body: {"name":"New Name","has_motors":false}
```

### Delete Robot
```
DELETE /api/robots/<robot_id>
```

## 🤝 Contributing

We welcome contributions! Please:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes
4. Add tests if applicable
5. Commit: `git commit -m "Add feature"`
6. Push: `git push origin feature-name`
7. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Built with Claude (Anthropic)** - Complete human-AI collaborative development
- **Original PingTo system** - Foundation for the robot monitoring concept
- **Modern web technologies** - Vue.js, Tailwind CSS, and Flask
- **ROS ecosystem** - Robot communication and data collection
- **Open source community** - Libraries and tools that made this possible

**Special thanks to the robotics team** for providing the real-world requirements that shaped this system.

## 📞 Support

- **Documentation**: This README is your main reference
- **Issues**: Open an issue on GitHub for bug reports
- **Questions**: Use GitHub Discussions for general questions
- **Logs**: Check `logs/` directory for detailed logging

---

**⭐ Star this repository if you find it useful!**

*Built through human-AI collaboration - demonstrating what's possible when creativity meets capability* 🤖❤️👨‍💻
