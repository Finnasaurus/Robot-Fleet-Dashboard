// main.js - Updated for 1Hz motor updates

// Function to set up motor data updates at 1Hz
const setupMotorDataUpdateRate = (robotData, lastUpdate, error, loading) => {
  // Create a reactive ref for motor updates
  const motorUpdateKey = ref(0);
  
  // Main data fetch interval (can be kept at 5 seconds for general data)
  const mainUpdateInterval = 1000; // 5 seconds
  
  // Motor data update interval (exactly 1Hz = 1000ms)
  const motorUpdateInterval = 50;   // 50 ms = 0.05 s = 20 Hz
  
  // Store the intervals for cleanup
  let mainDataInterval;
  let motorDataInterval;
  
  // Function to fetch all data
  const fetchAllData = async () => {
    try {
      console.log('Fetching complete robot data...');
      const response = await fetch(
        `/api/robot-status?type=motor&t=${Date.now()}`
        );
      
      if (!response.ok) {
        throw new Error(`Server responded with status: ${response.status}`);
      }
      
      const data = await response.json();
      
      robotData.value = {
        pingStatus: data.ping_status || {},
        robotStatus: data.robot_status || {},
        cleaningDeviceStatus: data.cleaning_device_status || {},
        motorData: data.motor_data || {}
      };
      
      lastUpdate.value = new Date().toLocaleString();
      error.value = null;
    } catch (err) {
      console.error('Error fetching data:', err);
      error.value = `Failed to load data: ${err.message}`;
    } finally {
      loading.value = false;
    }
  };
  
  // Function to fetch only motor data (lighter weight, faster)
  const fetchMotorDataOnly = async () => {
    try {
      // Use the existing endpoint until the dedicated endpoint is added
      const response = await fetch(`/api/robot-status?t=${Date.now()}`);
      
      if (!response.ok) return; // Silently fail for motor-only updates
      
      const data = await response.json();
      
      // Only update the motor data portion
      if (data.motor_data) {
        robotData.value.motorData = data.motor_data;
        // Increment update key to trigger component updates
        motorUpdateKey.value++;
        console.log('Motor data updated at 1Hz, updateKey:', motorUpdateKey.value);
      }
    } catch (err) {
      console.warn('Error fetching motor data:', err);
      // Don't set error state for motor-only updates
    }
  };
  
  // Initial fetch
  fetchAllData();
  
  // Set up intervals
  mainDataInterval = setInterval(fetchAllData, mainUpdateInterval);
  
  // Start motor data updates with a slight delay to avoid collision
  setTimeout(() => {
    motorDataInterval = setInterval(fetchMotorDataOnly, motorUpdateInterval);
  }, 1000);
  
  // Return both cleanup function and the update key
  return {
    cleanup: () => {
      clearInterval(mainDataInterval);
      clearInterval(motorDataInterval);
    },
    motorUpdateKey
  };
};

// Function to set up motor data updates using a Web Worker
const setupMotorDataWorker = (robotData, lastUpdate, error, loading) => {
  // Create a reactive ref for motor updates
  const motorUpdateKey = ref(0);
  let worker = null;
  
  // Main data fetch interval (5 seconds for general data)
  const mainUpdateInterval = 5000; // 5 seconds
  let mainDataInterval;
  
  // Function to fetch general data (excluding motor data)
  const fetchGeneralData = async () => {
    try {
      console.log('Fetching general robot data...');
      // Request general data only
      const response = await fetch(`/api/robot-status?type=general&t=${Date.now()}`);
      
      if (!response.ok) {
        throw new Error(`Server responded with status: ${response.status}`);
      }
      
      const data = await response.json();
      
      // Update everything except motor data
      robotData.value = {
        ...robotData.value, // Keep existing data including motor data
        pingStatus: data.ping_status || robotData.value.pingStatus || {},
        robotStatus: data.robot_status || robotData.value.robotStatus || {},
        cleaningDeviceStatus: data.cleaning_device_status || robotData.value.cleaningDeviceStatus || {}
      };
      
      lastUpdate.value = new Date().toLocaleString();
      error.value = null;
    } catch (err) {
      console.error('Error fetching general data:', err);
      error.value = `Failed to load data: ${err.message}`;
    } finally {
      loading.value = false;
    }
  };
  
  // Initialize and set up the Web Worker
  const initWorker = () => {
    try {
      // Create a new worker
      worker = new Worker('/static/js/motorDataWorker.js');
      
      // Listen for messages from the worker
      worker.addEventListener('message', (event) => {
        const message = event.data;
        
        // Handle different message types
        switch (message.type) {
          case 'motorData':
            // Update motor data from worker
            if (message.data.motorData) {
              robotData.value.motorData = message.data.motorData;
              // Update ping status if available
              if (message.data.pingStatus) {
                robotData.value.pingStatus = {
                  ...robotData.value.pingStatus,
                  ...message.data.pingStatus
                };
              }
              // Increment update key to trigger component updates
              motorUpdateKey.value++;
              console.log('Motor data updated via worker, updateKey:', motorUpdateKey.value);
            }
            break;
            
          case 'error':
            console.warn('Motor data worker error:', message.error);
            break;
            
          default:
            console.log('Received message from worker:', message);
        }
      });
      
      // Handle worker errors
      worker.addEventListener('error', (error) => {
        console.error('Motor data worker error:', error);
      });
      
      console.log('Motor data worker initialized');
    } catch (err) {
      console.error('Failed to initialize Web Worker:', err);
      console.warn('Falling back to main thread polling');
      
      // Fallback to main thread polling if worker creation fails
      setupFallbackPolling();
    }
  };
  
  // Fallback polling method if Web Worker fails
  const setupFallbackPolling = () => {
    console.log('Using fallback polling for motor data');
    const motorInterval = setInterval(async () => {
      try {
        const response = await fetch(`/api/robot-status?type=motor&t=${Date.now()}`);
        
        if (!response.ok) return;
        
        const data = await response.json();
        
        if (data.motor_data) {
          robotData.value.motorData = data.motor_data;
          motorUpdateKey.value++;
          console.log('Motor data updated via fallback, updateKey:', motorUpdateKey.value);
        }
      } catch (err) {
        console.warn('Error in fallback motor data polling:', err);
      }
    }, 1000);
    
    // Add the motor interval to the cleanup function
    const originalCleanup = cleanup;
    cleanup = () => {
      originalCleanup();
      clearInterval(motorInterval);
    };
  };
  
  // Initial data fetch
  fetchGeneralData();
  
  // Set up main data interval
  mainDataInterval = setInterval(fetchGeneralData, mainUpdateInterval);
  
  // Initialize the worker
  initWorker();
  
  // Cleanup function
  let cleanup = () => {
    // Clear intervals
    clearInterval(mainDataInterval);
    
    // Terminate worker if it exists
    if (worker) {
      // Send stop command to worker
      worker.postMessage({ command: 'stop' });
      // Terminate the worker
      worker.terminate();
      worker = null;
    }
  };
  
  // Return both cleanup function and the update key
  return {
    cleanup,
    motorUpdateKey
  };
};