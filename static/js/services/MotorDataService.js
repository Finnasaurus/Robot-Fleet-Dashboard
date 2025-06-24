// MotorDataService.js
// A service module for handling motor data logic

const MotorDataService = {
  // Check if a robot has motor data capability - always return true to enable UI
  robotHasMotorData(robotName) {
    if (!robotName) return false;
    
    // Always return true to show motor indicators in UI
    return true;
  },
  
  // Check if motor data exists and has non-zero values
  hasMotorData(robotName, motorData) {
    if (!motorData || !motorData[robotName]) {
      console.log(`${robotName} has no motor data available`);
      return false;
    }
    
    // Check if there's any data structure
    const motor1 = motorData[robotName].motor1 || {};
    const motor2 = motorData[robotName].motor2 || {};
    
    return Object.keys(motor1).length > 0 || Object.keys(motor2).length > 0;
  },
  
  // Modified to detect smaller non-zero values and large absolute values
  // Modified to detect smaller non-zero values
  // Modified to detect smaller non-zero values
  areAllValuesZero(robotName, motorData) {
    if (!motorData || !motorData[robotName]) return true;
    
    const motor1 = motorData[robotName].motor1 || {};
    const motor2 = motorData[robotName].motor2 || {};
    
    // Even very small non-zero values should be detected (0.0001 threshold)
    return !(
      (motor1.pos_rad && Math.abs(motor1.pos_rad) >= 0.0001) || 
      (motor1.vel_rpm && Math.abs(motor1.vel_rpm) >= 0.0001) || 
      (motor1.current && Math.abs(motor1.current) >= 0.0001) ||
      (motor2.pos_rad && Math.abs(motor2.pos_rad) >= 0.0001) || 
      (motor2.vel_rpm && Math.abs(motor2.vel_rpm) >= 0.0001) || 
      (motor2.current && Math.abs(motor2.current) >= 0.0001)
    );
  },
  
  // Check if a motor value is zero
  isZeroValue(value) {
    return value === undefined || value === null || Math.abs(value) < 0.0001;
  },
  
  // Check if a motor value is zero
  isZeroValue(value) {
    return value === undefined || value === null || Math.abs(value) < 0.0001;
  },
  
  // Format a motor value for display - improved to handle large values
  formatMotorValue(value) {
    if (value === undefined || value === null) {
      return 'N/A';
    }
    
    if (typeof value !== 'number') {
      return 'Invalid';
    }
    
    // Handle very large position values (like 96000+)
    if (Math.abs(value) > 1000) {
      // For very large values, show in scientific notation
      return value.toExponential(2);
    }
    
    // Format regular values to 3 decimal places to catch small non-zero values
    return value.toFixed(3);
  },
  
  // Modified to detect smaller values
  isZeroValue(value) {
    // More sensitive detection for near-zero values
    return value === undefined || value === null || Math.abs(value) < 0.0001;
  },
  
  // The rest of the methods remain unchanged
  isMotorValueAbnormal(value, type) {
    if (value === undefined || value === null) {
      return false;
    }
    
    switch (type) {
      case 'current':
        // Current values over 5A might be abnormal, but show high values
        return value > 5;
      case 'velocity':
        // RPM over 1000 might be abnormal
        return Math.abs(value) > 1000;
      case 'position':
        // Extremely high position values might indicate an issue
        return Math.abs(value) > 100000;
      default:
        return false;
    }
  },
  
  // Get motor status display text and color based on robot status
  getMotorStatusDisplay(robotStatus) {
    if (!robotStatus || typeof robotStatus !== 'object') {
      return { text: 'No Data', color: 'text-gray-500' };
    }

    const watchDoggoErrors = robotStatus.watch_doggo_error_rm || [];
    const hasMotorError = watchDoggoErrors.some(error => 
      error && error.error_code === '1201'
    );

    if (hasMotorError) {
      return { text: 'Error', color: 'text-red-500' };
    }

    if (robotStatus.is_cleaning) {
      return { text: 'Running', color: 'text-green-500' };
    }

    if (robotStatus.is_navigating) {
      return { text: 'Moving', color: 'text-blue-500' };
    }

    return { text: 'Idle', color: 'text-gray-500' };
  },
  
  // Get motor errors from robot status
  getMotorErrors(robotStatus) {
    if (!robotStatus || !robotStatus.watch_doggo_error_rm) {
      return [];
    }

    return robotStatus.watch_doggo_error_rm.filter(error => 
      error && error.error_code === '1201'
    );
  }
};