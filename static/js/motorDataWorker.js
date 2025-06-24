// motorDataWorker.js - This runs in a separate thread

// Configuration
const POLLING_INTERVAL = 500; // 1Hz polling rate
let isRunning = true;
let pollTimer = null;
let consecutiveErrors = 0;
const MAX_CONSECUTIVE_ERRORS = 3;

// Start polling when the worker is created
startPolling();

// Listen for messages from the main thread
self.addEventListener('message', function(e) {
  const command = e.data.command;
  
  switch(command) {
    case 'start':
      isRunning = true;
      startPolling();
      break;
    case 'stop':
      isRunning = false;
      if (pollTimer) {
        clearTimeout(pollTimer);
      }
      break;
    case 'poll':
      // Force immediate polling
      if (pollTimer) {
        clearTimeout(pollTimer);
      }
      pollMotorData();
      break;
    case 'setInterval':
      const newInterval = e.data.interval;
      if (newInterval && typeof newInterval === 'number') {
        POLLING_INTERVAL = newInterval;
        // Restart polling with new interval
        if (isRunning) {
          if (pollTimer) {
            clearTimeout(pollTimer);
          }
          startPolling();
        }
      }
      break;
    default:
      console.warn('Worker received unknown command:', command);
  }
});

// Function to poll for motor data
async function pollMotorData() {
  try {
    // Add a timestamp and specific type
    const timestamp = Date.now();
    
    // Fetch motor data - specifying motor-only endpoint
    const response = await fetch(`/api/robot-status?type=motor&t=${timestamp}`);
    
    if (!response.ok) {
      throw new Error(`Server responded with status: ${response.status}`);
    }
    
    const data = await response.json();
    
    // Validate received data
    if (!data.motor_data) {
      console.warn('Motor data missing in response');
      throw new Error('Motor data missing in response');
    }
    
    // Log data structure (helps with debugging)
    const robotCount = Object.keys(data.motor_data).length;
    console.log(`Received motor data for ${robotCount} robots at ${new Date().toLocaleTimeString()}`);
    
    // Check if we have valid data structure for any robot
    let hasValidData = false;
    
    for (const robotName in data.motor_data) {
      const robotData = data.motor_data[robotName];
      
      // Check for expected structure
      if (robotData && (robotData.motor1 || robotData.motor2)) {
        hasValidData = true;
        
        // Check for non-zero values
        const motor1 = robotData.motor1 || {};
        const motor2 = robotData.motor2 || {};
        
        const hasNonZeroValues = 
          (motor1.pos_rad && Math.abs(motor1.pos_rad) > 0.01) ||
          (motor1.vel_rpm && Math.abs(motor1.vel_rpm) > 0.01) ||
          (motor1.current && Math.abs(motor1.current) > 0.01) ||
          (motor2.pos_rad && Math.abs(motor2.pos_rad) > 0.01) ||
          (motor2.vel_rpm && Math.abs(motor2.vel_rpm) > 0.01) ||
          (motor2.current && Math.abs(motor2.current) > 0.01);
        
        if (hasNonZeroValues) {
          console.log(`Robot ${robotName} has non-zero motor values`);
        }
      }
    }
    
    if (!hasValidData) {
      console.warn('No valid motor data structure found for any robot');
    }
    
    // Reset consecutive errors counter on success
    consecutiveErrors = 0;
    
    // Send data back to the main thread
    self.postMessage({
      type: 'motorData',
      data: {
        motorData: data.motor_data || {},
        pingStatus: data.ping_status || {},
        timestamp: timestamp
      }
    });
    
  } catch (error) {
    // Increment consecutive errors counter
    consecutiveErrors++;
    
    // Send error to main thread
    self.postMessage({
      type: 'error',
      error: error.message
    });
    
    // If too many errors, slow down polling to avoid overwhelming the server
    if (consecutiveErrors > MAX_CONSECUTIVE_ERRORS) {
      console.warn(`${consecutiveErrors} consecutive errors, slowing down polling rate`);
    }
  }
  
  // Schedule next poll if still running
  if (isRunning) {
    // Use a slower interval if we're having consecutive errors
    const nextInterval = (consecutiveErrors > MAX_CONSECUTIVE_ERRORS) 
      ? POLLING_INTERVAL * 2 
      : POLLING_INTERVAL;
      
    pollTimer = setTimeout(pollMotorData, nextInterval);
  }
}

// Start the polling process
function startPolling() {
  console.log('Motor data worker: Starting polling at', POLLING_INTERVAL, 'ms intervals');
  // Start immediately
  pollMotorData();
}

// Log that the worker is initialized
console.log('Motor data worker initialized');