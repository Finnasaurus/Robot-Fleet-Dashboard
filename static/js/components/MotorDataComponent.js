// MotorDataComponent.js
// A reusable component for displaying robot motor data

const MotorDataComponent = {
  props: {
    robotName: {
      type: String,
      required: true
    },
    motorData: {
      type: Object,
      default: () => ({})
    },
    isOnline: {
      type: Boolean,
      default: false
    },
    robotStatus: {
      type: Object,
      default: () => ({})
    },
    // Add updateKey prop to force updates only when needed
    updateKey: {
      type: Number,
      default: 0
    }
  },
  
  // Tell Vue to avoid unnecessary re-renders
  computed: {
    hasMotorData() {
      const robotName = this.robotName;
      
      // Check if motor data exists in structure
      const motorData = this.motorData[robotName];
      if (!motorData) {
        return false;
      }
      
      // Even if all values are zero, we want to show the UI
      const motor1 = motorData.motor1 || {};
      const motor2 = motorData.motor2 || {};
      
      // Check if any structure exists for motor1 or motor2
      return Object.keys(motor1).length > 0 || Object.keys(motor2).length > 0;
    },
    
    hasNonZeroValues() {
      const robotName = this.robotName;
      const motorData = this.motorData[robotName];
      
      if (!motorData) return false;
      
      const motor1 = motorData.motor1 || {};
      const motor2 = motorData.motor2 || {};
      
      // Check if ANY important value is non-zero (more sensitive)
      return (
        (motor1.pos_rad && Math.abs(motor1.pos_rad) > 0.001) || 
        (motor1.vel_rpm && Math.abs(motor1.vel_rpm) > 0.001) || 
        (motor1.current && Math.abs(motor1.current) > 0.001) ||
        (motor2.pos_rad && Math.abs(motor2.pos_rad) > 0.001) || 
        (motor2.vel_rpm && Math.abs(motor2.vel_rpm) > 0.001) || 
        (motor2.current && Math.abs(motor2.current) > 0.001)
      );
    },
    
    getMotorStatusDisplay() {
      const status = this.robotStatus;
      
      if (!status || typeof status !== 'object') {
        return { text: 'No Data', color: 'text-gray-500' };
      }

      const watchDoggoErrors = status.watch_doggo_error_rm || [];
      const hasMotorError = watchDoggoErrors.some(error => 
        error && error.error_code === '1201'
      );

      if (hasMotorError) {
        return { text: 'Error', color: 'text-red-500' };
      }

      if (status.is_cleaning) {
        return { text: 'Running', color: 'text-green-500' };
      }

      if (status.is_navigating) {
        return { text: 'Moving', color: 'text-blue-500' };
      }

      return { text: 'Idle', color: 'text-gray-500' };
    },
    
    getMotorErrors() {
      const status = this.robotStatus;
      if (!status || !status.watch_doggo_error_rm) {
        return [];
      }

      return status.watch_doggo_error_rm.filter(error => 
        error && error.error_code === '1201'
      );
    },
    
    stringifyMotorData() {
      if (!this.motorData || !this.motorData[this.robotName]) {
        return "{}";
      }
      
      try {
        return JSON.stringify(this.motorData[this.robotName], null, 2);
      } catch (err) {
        return "Error stringifying motor data: " + err.message;
      }
    },
    
    // Create cached references to motor data for better performance
    motor1Data() {
      return this.motorData[this.robotName]?.motor1 || {};
    },
    
    motor2Data() {
      return this.motorData[this.robotName]?.motor2 || {};
    }
  },
  
  methods: {
    formatMotorValue(value) {
      if (value === undefined || value === null) {
        return 'N/A';
      }
      
      if (typeof value !== 'number') {
        return 'Invalid';
      }
      
      // Format large values (like position values over 1000) in scientific notation
      if (Math.abs(value) > 1000) {
        return value.toExponential(2);
      }
      
      // Format regular values with more precision to catch small non-zero values
      return value.toFixed(3);
    },
    
    isZeroValue(value) {
      // More sensitive threshold for zero detection
      return value === undefined || value === null || Math.abs(value) < 0.001;
    },
    
    hasValue(value) {
      // Returns true if value is meaningfully non-zero
      return value !== undefined && value !== null && Math.abs(value) >= 0.001;
    },
    
    getValueClass(value, type) {
      // Get CSS classes based on value and type
      const classes = ['motor-value'];
      
      if (!this.isZeroValue(value)) {
        classes.push('motor-value-active');
        
        // Add type-specific classes
        if (type === 'current') classes.push('motor-value-current');
        if (type === 'velocity') classes.push('motor-value-velocity');
        if (type === 'position') classes.push('motor-value-position');
      }
      
      return classes.join(' ');
    },
    
    isMotorValueAbnormal(value, type) {
      if (value === undefined || value === null) {
        return false;
      }
      
      switch (type) {
        case 'current':
          // Current values over 5A might be abnormal
          return value > 5;
        case 'velocity':
          // RPM over 1000 might be abnormal
          return Math.abs(value) > 1000;
        case 'position':
          // Extremely high positions might indicate an issue
          return Math.abs(value) > 100000;
        default:
          return false;
      }
    }
  },
  
  template: `
    <div>
      <template v-if="isOnline">
        <div v-if="hasMotorData">
          <div :class="['font-semibold', getMotorStatusDisplay.color]">
            Status: <span v-text="getMotorStatusDisplay.text"></span>
          </div>
          
          <!-- Motor Data Collection Status -->
          <div v-if="!hasNonZeroValues" class="mt-2 p-2 bg-yellow-50 border border-yellow-200 rounded text-sm text-yellow-800">
            <div class="flex items-center">
              <svg class="h-4 w-4 text-yellow-400 mr-1" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" clip-rule="evenodd" />
              </svg>
              Motor data detected but values near zero - motors may be idle
            </div>
          </div>
          
          <!-- Active Motor Data Indicator -->
          <div v-else class="mt-2 p-2 bg-green-50 border border-green-200 rounded text-sm text-green-800">
            <div class="flex items-center">
              <svg class="h-4 w-4 text-green-500 mr-1" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
              </svg>
              Active motor data detected!
            </div>
          </div>
          
          <!-- Motor Errors -->
          <div 
            v-for="(error, index) in getMotorErrors" 
            :key="index" 
            class="text-red-500 mt-2"
          >
            Error Code: <span v-text="error.error_code"></span>
          </div>
          
          <!-- Motor Data -->
          <div class="mt-4">
            <h3 class="font-semibold mb-2">Motor Data</h3>
            <div class="grid grid-cols-2 gap-4">
              <div>
                <h4 class="font-medium">Motor 1</h4>
                <div class="text-sm space-y-1">
                  <p :class="{'has-value': hasValue(motor1Data.pos_rad)}">
                    Position (rad): <span :class="getValueClass(motor1Data.pos_rad, 'position')" v-text="formatMotorValue(motor1Data.pos_rad)"></span>
                  </p>
                  <p :class="{'has-value': hasValue(motor1Data.pos_offset)}">
                    Position Offset: <span :class="getValueClass(motor1Data.pos_offset, 'position')" v-text="formatMotorValue(motor1Data.pos_offset)"></span>
                  </p>
                  <p :class="{'has-value': hasValue(motor1Data.vel_rpm)}">
                    Velocity (rpm): <span :class="getValueClass(motor1Data.vel_rpm, 'velocity')" v-text="formatMotorValue(motor1Data.vel_rpm)"></span>
                  </p>
                  <p :class="{'has-value': hasValue(motor1Data.vel_rad)}">
                    Velocity (rad/s): <span :class="getValueClass(motor1Data.vel_rad, 'velocity')" v-text="formatMotorValue(motor1Data.vel_rad)"></span>
                  </p>
                  <p :class="{'has-value': hasValue(motor1Data.current)}">
                    Current (A): <span :class="getValueClass(motor1Data.current, 'current')" v-text="formatMotorValue(motor1Data.current)"></span>
                  </p>
                </div>
              </div>
              <div>
                <h4 class="font-medium">Motor 2</h4>
                <div class="text-sm space-y-1">
                  <p :class="{'has-value': hasValue(motor2Data.pos_rad)}">
                    Position (rad): <span :class="getValueClass(motor2Data.pos_rad, 'position')" v-text="formatMotorValue(motor2Data.pos_rad)"></span>
                  </p>
                  <p :class="{'has-value': hasValue(motor2Data.pos_offset)}">
                    Position Offset: <span :class="getValueClass(motor2Data.pos_offset, 'position')" v-text="formatMotorValue(motor2Data.pos_offset)"></span>
                  </p>
                  <p :class="{'has-value': hasValue(motor2Data.vel_rpm)}">
                    Velocity (rpm): <span :class="getValueClass(motor2Data.vel_rpm, 'velocity')" v-text="formatMotorValue(motor2Data.vel_rpm)"></span>
                  </p>
                  <p :class="{'has-value': hasValue(motor2Data.vel_rad)}">
                    Velocity (rad/s): <span :class="getValueClass(motor2Data.vel_rad, 'velocity')" v-text="formatMotorValue(motor2Data.vel_rad)"></span>
                  </p>
                  <p :class="{'has-value': hasValue(motor2Data.current)}">
                    Current (A): <span :class="getValueClass(motor2Data.current, 'current')" v-text="formatMotorValue(motor2Data.current)"></span>
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div v-else class="text-gray-500">
          <p>Attempting to connect to motor data service...</p>
          <p class="text-xs mt-2">This robot may need additional configuration to enable motor data.</p>
        </div>
      </template>
      <div v-else class="text-gray-500">Offline</div>
    </div>
  `
};