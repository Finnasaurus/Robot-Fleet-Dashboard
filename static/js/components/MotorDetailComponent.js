const MotorDetailComponent = {
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
    // Add updateKey prop to force updates only when needed
    updateKey: {
      type: Number,
      default: 0
    }
  },
  
  computed: {
    // Create cached references to motor data for better performance
    motor1Data() {
      return this.motorData[this.robotName]?.motor1 || {};
    },
    
    motor2Data() {
      return this.motorData[this.robotName]?.motor2 || {};
    },
    
    hasMotorData() {
      const robotName = this.robotName;
      const motorData = this.motorData[robotName];
      
      if (!motorData) return false;
      
      const motor1 = motorData.motor1 || {};
      const motor2 = motorData.motor2 || {};
      
      return Object.keys(motor1).length > 0 || Object.keys(motor2).length > 0;
    },
    
    areAllValuesZero() {
      const robotName = this.robotName;
      const motorData = this.motorData[robotName];
      
      if (!motorData) return true;
      
      const motor1 = motorData.motor1 || {};
      const motor2 = motorData.motor2 || {};
      
      // Check if all important values are zero or don't exist
      const allZero = 
        (!motor1.pos_rad || Math.abs(motor1.pos_rad) < 0.01) && 
        (!motor1.vel_rpm || Math.abs(motor1.vel_rpm) < 0.01) && 
        (!motor1.current || Math.abs(motor1.current) < 0.01) &&
        (!motor2.pos_rad || Math.abs(motor2.pos_rad) < 0.01) && 
        (!motor2.vel_rpm || Math.abs(motor2.vel_rpm) < 0.01) && 
        (!motor2.current || Math.abs(motor2.current) < 0.01);
      
      return allZero;
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
    
    // Precompute gauge widths for better performance
    motor1PosWidth() {
      return `${Math.min(Math.abs(this.motor1Data.pos_rad || 0) / 6.28 * 100, 100)}%`;
    },
    
    motor1CurrentWidth() {
      return `${Math.min(Math.abs(this.motor1Data.current || 0) / 10 * 100, 100)}%`;
    },
    
    motor1VelWidth() {
      return `${Math.min(Math.abs(this.motor1Data.vel_rpm || 0) / 1000 * 100, 100)}%`;
    },
    
    motor2PosWidth() {
      return `${Math.min(Math.abs(this.motor2Data.pos_rad || 0) / 6.28 * 100, 100)}%`;
    },
    
    motor2CurrentWidth() {
      return `${Math.min(Math.abs(this.motor2Data.current || 0) / 10 * 100, 100)}%`;
    },
    
    motor2VelWidth() {
      return `${Math.min(Math.abs(this.motor2Data.vel_rpm || 0) / 1000 * 100, 100)}%`;
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
      
      // Format to 2 decimal places
      return value.toFixed(2);
    },
    
    isZeroValue(value) {
      return value === undefined || value === null || Math.abs(value) < 0.01;
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
          // RPM over 1000 might be abnormal (adjust based on your motors)
          return Math.abs(value) > 1000;
        default:
          return false;
      }
    }
  },
  
  template: `
    <div class="bg-white shadow rounded-lg">
      <div class="px-6 py-4 border-b">
        <h2 class="text-lg font-semibold">Motor Data Details</h2>
      </div>
      <div class="px-6 py-4">
        <template v-if="hasMotorData">
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div class="border rounded p-4">
              <h3 class="font-medium mb-2">Motor 1 Status</h3>
              
              <!-- Position Chart or Gauge could go here -->
              <div class="mb-4">
                <div class="flex justify-between mb-1">
                  <span class="text-sm font-medium">Position (rad)</span>
                  <span :class="[
                    'text-sm motor-value', 
                    isZeroValue(motor1Data.pos_rad) ? 
                    'text-yellow-500 font-bold' : '']" 
                    v-text="formatMotorValue(motor1Data.pos_rad)"></span>
                </div>
                <div class="w-full bg-gray-200 rounded-full h-2.5">
                  <div :class="[
                    'h-2.5 rounded-full motor-gauge-bar',
                    isZeroValue(motor1Data.pos_rad) ? 
                    'bg-yellow-400' : 'bg-blue-600']" 
                    :style="{width: motor1PosWidth}"></div>
                </div>
                <div :class="['text-xs mt-1', 
                           isZeroValue(motor1Data.pos_rad) ? 
                           'text-yellow-500' : 'text-gray-500']">
                  {{ isZeroValue(motor1Data.pos_rad) ? 
                     'Zero value detected - motor data may not be available' : 
                     'Range: 0 - 2?' }}
                </div>
              </div>
              
              <!-- Current Indicator -->
              <div class="mb-4">
                <div class="flex justify-between mb-1">
                  <span class="text-sm font-medium">Current (A)</span>
                  <span :class="[
                    'text-sm motor-value', 
                    isMotorValueAbnormal(motor1Data.current, 'current') ? 
                    'text-red-500 font-bold' : 
                    isZeroValue(motor1Data.current) ?
                    'text-yellow-500 font-bold' : '']" 
                    v-text="formatMotorValue(motor1Data.current)"></span>
                </div>
                <div class="w-full bg-gray-200 rounded-full h-2.5">
                  <div :class="[
                    'h-2.5 rounded-full motor-gauge-bar', 
                    isMotorValueAbnormal(motor1Data.current, 'current') ? 
                    'bg-red-500' : 
                    isZeroValue(motor1Data.current) ?
                    'bg-yellow-400' : 'bg-green-500']" 
                    :style="{width: motor1CurrentWidth}"></div>
                </div>
                <div :class="['text-xs mt-1', 
                           isZeroValue(motor1Data.current) ? 
                           'text-yellow-500' : 'text-gray-500']">
                  {{ isZeroValue(motor1Data.current) ? 
                     'Zero value detected - motor data may not be available' : 
                     'Normal range: 0 - 5A' }}
                </div>
              </div>
              
              <!-- Velocity Indicator -->
              <div>
                <div class="flex justify-between mb-1">
                  <span class="text-sm font-medium">Velocity (RPM)</span>
                  <span :class="[
                    'text-sm motor-value', 
                    isMotorValueAbnormal(motor1Data.vel_rpm, 'velocity') ? 
                    'text-red-500 font-bold' : 
                    isZeroValue(motor1Data.vel_rpm) ?
                    'text-yellow-500 font-bold' : '']" 
                    v-text="formatMotorValue(motor1Data.vel_rpm)"></span>
                </div>
                <div class="w-full bg-gray-200 rounded-full h-2.5">
                  <div :class="[
                    'h-2.5 rounded-full motor-gauge-bar', 
                    isMotorValueAbnormal(motor1Data.vel_rpm, 'velocity') ? 
                    'bg-red-500' : 
                    isZeroValue(motor1Data.vel_rpm) ?
                    'bg-yellow-400' : 'bg-blue-500']" 
                    :style="{width: motor1VelWidth}"></div>
                </div>
                <div :class="['text-xs mt-1', 
                           isZeroValue(motor1Data.vel_rpm) ? 
                           'text-yellow-500' : 'text-gray-500']">
                  {{ isZeroValue(motor1Data.vel_rpm) ? 
                     'Zero value detected - motor data may not be available' : 
                     'Normal range: 0 - 1000 RPM' }}
                </div>
              </div>
            </div>
            
            <!-- Motor 2 Section -->
            <div class="border rounded p-4">
              <h3 class="font-medium mb-2">Motor 2 Status</h3>
              
              <!-- Position Chart or Gauge -->
              <div class="mb-4">
                <div class="flex justify-between mb-1">
                  <span class="text-sm font-medium">Position (rad)</span>
                  <span :class="[
                    'text-sm motor-value', 
                    isZeroValue(motor2Data.pos_rad) ? 
                    'text-yellow-500 font-bold' : '']" 
                    v-text="formatMotorValue(motor2Data.pos_rad)"></span>
                </div>
                <div class="w-full bg-gray-200 rounded-full h-2.5">
                  <div :class="[
                    'h-2.5 rounded-full motor-gauge-bar',
                    isZeroValue(motor2Data.pos_rad) ? 
                    'bg-yellow-400' : 'bg-blue-600']" 
                    :style="{width: motor2PosWidth}"></div>
                </div>
                <div :class="['text-xs mt-1', 
                           isZeroValue(motor2Data.pos_rad) ? 
                           'text-yellow-500' : 'text-gray-500']">
                  {{ isZeroValue(motor2Data.pos_rad) ? 
                     'Zero value detected - motor data may not be available' : 
                     'Range: 0 - 2?' }}
                </div>
              </div>
              
              <!-- Current Indicator -->
              <div class="mb-4">
                <div class="flex justify-between mb-1">
                  <span class="text-sm font-medium">Current (A)</span>
                  <span :class="[
                    'text-sm motor-value', 
                    isMotorValueAbnormal(motor2Data.current, 'current') ? 
                    'text-red-500 font-bold' : 
                    isZeroValue(motor2Data.current) ?
                    'text-yellow-500 font-bold' : '']" 
                    v-text="formatMotorValue(motor2Data.current)"></span>
                </div>
                <div class="w-full bg-gray-200 rounded-full h-2.5">
                  <div :class="[
                    'h-2.5 rounded-full motor-gauge-bar', 
                    isMotorValueAbnormal(motor2Data.current, 'current') ? 
                    'bg-red-500' : 
                    isZeroValue(motor2Data.current) ?
                    'bg-yellow-400' : 'bg-green-500']" 
                    :style="{width: motor2CurrentWidth}"></div>
                </div>
                <div :class="['text-xs mt-1', 
                           isZeroValue(motor2Data.current) ? 
                           'text-yellow-500' : 'text-gray-500']">
                  {{ isZeroValue(motor2Data.current) ? 
                     'Zero value detected - motor data may not be available' : 
                     'Normal range: 0 - 5A' }}
                </div>
              </div>
              
              <!-- Velocity Indicator -->
              <div>
                <div class="flex justify-between mb-1">
                  <span class="text-sm font-medium">Velocity (RPM)</span>
                  <span :class="[
                    'text-sm motor-value', 
                    isMotorValueAbnormal(motor2Data.vel_rpm, 'velocity') ? 
                    'text-red-500 font-bold' : 
                    isZeroValue(motor2Data.vel_rpm) ?
                    'text-yellow-500 font-bold' : '']" 
                    v-text="formatMotorValue(motor2Data.vel_rpm)"></span>
                </div>
                <div class="w-full bg-gray-200 rounded-full h-2.5">
                  <div :class="[
                    'h-2.5 rounded-full motor-gauge-bar', 
                    isMotorValueAbnormal(motor2Data.vel_rpm, 'velocity') ? 
                    'bg-red-500' : 
                    isZeroValue(motor2Data.vel_rpm) ?
                    'bg-yellow-400' : 'bg-blue-500']" 
                    :style="{width: motor2VelWidth}"></div>
                </div>
                <div :class="['text-xs mt-1', 
                           isZeroValue(motor2Data.vel_rpm) ? 
                           'text-yellow-500' : 'text-gray-500']">
                  {{ isZeroValue(motor2Data.vel_rpm) ? 
                     'Zero value detected - motor data may not be available' : 
                     'Normal range: 0 - 1000 RPM' }}
                </div>
              </div>
            </div>
          </div>
          
          <!-- Data Collection Status -->
          <div v-if="areAllValuesZero" class="mt-4 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
            <div class="flex">
              <div class="flex-shrink-0">
                <svg class="h-5 w-5 text-yellow-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                  <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
                </svg>
              </div>
              <div class="ml-3">
                <h3 class="text-sm font-medium text-yellow-800">Motor Data Status</h3>
                <div class="mt-2 text-sm text-yellow-700">
                  <p>All motor values are currently zero. This could indicate:</p>
                  <ul class="list-disc pl-5 mt-1 space-y-1">
                    <li>The robot may not support motor data collection</li>
                    <li>The connection to the robot's motor controller may be failing</li>
                    <li>The motors may be currently inactive or powered off</li>
                  </ul>
                  <p class="mt-2">The system will continue attempting to collect real-time motor data.</p>
                </div>
              </div>
            </div>
          </div>
          
          <!-- Motor Data JSON -->
          <div class="mt-4">
            <h3 class="font-medium mb-2">Raw Motor Data</h3>
            <pre class="bg-gray-100 p-3 rounded text-xs overflow-auto max-h-48" v-text="stringifyMotorData"></pre>
          </div>
        </template>
        <div v-else class="text-gray-500">
          No motor data available for this robot.
        </div>
      </div>
    </div>
  `
};