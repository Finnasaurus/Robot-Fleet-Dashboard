# How to Add New Robots to the Dashboard

Adding a new robot is now as simple as updating a single configuration file!

## Quick Steps

1. **Edit `config.yaml`**
2. **Add your robot entry**
3. **Restart the dashboard**
4. **Done!**

## Detailed Instructions

### 1. Open `config.yaml`

```yaml
flexa:
  # Your robots are defined here
```

### 2. Add Your New Robot

Copy this template and add it under the `flexa:` section:

```yaml
  # Replace 'newrobot1' with your robot's ID (lowercase, no spaces)
  newrobot1:
    name: "newrobot1"           # Display name for the dashboard
    ip: "192.168.69.150"        # Robot's IP address
    has_motors: false           # Set to true if robot has motor data
```

### Example: Adding a New Robot

Let's say you want to add a robot called "base15" at IP 192.168.69.135 with motor capabilities:

```yaml
flexa:
  # ... existing robots ...
  
  base15:
    name: "base15"
    ip: "192.168.69.135"
    has_motors: true
```

### 3. Restart the Dashboard

After saving `config.yaml`:

```bash
# Stop the dashboard (Ctrl+C)
# Start it again
python web.py
```

### 4. Verify

- Your new robot should appear in the dropdown menu
- It should show up in the robot grid
- If `has_motors: true`, motor data will be collected

## Configuration Options

### Robot Settings

| Field | Required | Description | Example |
|-------|----------|-------------|---------|
| name | Yes | Display name in dashboard | "base15" |
| ip | Yes | IP address of the robot | "192.168.69.135" |
| has_motors | No | Enable motor data collection | true/false |

### System Settings (Optional)

You can also adjust system-wide settings in `config.yaml`:

```yaml
system:
  update_interval: 1.0          # Ping/status update rate (seconds)
  motor_update_interval: 1.0    # Motor data update rate (seconds)
  ssh_user: "${ROS_MASTER_USER}"     # From .env file
  ssh_password: "${ROS_MASTER_PASSWD}" # From .env file
```

## Common Issues

### Robot Not Appearing
- Check YAML formatting (indentation matters!)
- Make sure you restarted the dashboard
- Check the logs for errors

### Motor Data Not Working
- Verify `has_motors: true` is set
- Check SSH credentials in `.env` file
- Ensure robot has motor topics published

### Robot Shows as Offline
- Verify IP address is correct
- Check network connectivity
- Ensure robot is powered on

## Tips

1. **Test First**: Ping the robot's IP before adding it
   ```bash
   ping 192.168.69.150
   ```

2. **Check Logs**: Look at `dashboard.log` for configuration errors

3. **Reload Config**: Use the reload button (↻) in the dashboard to reload configuration without restarting

4. **Naming Convention**: Keep robot names consistent (e.g., base1, base2, base-b1)

## That's It!

You no longer need to:
- ❌ Edit multiple Python files
- ❌ Update hardcoded lists
- ❌ Modify HTML/JavaScript
- ❌ Worry about missing a file

Just update `config.yaml` and you're done! 🎉