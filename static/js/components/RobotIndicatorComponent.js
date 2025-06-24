// RobotIndicatorComponent.js
// A reusable component for displaying robot indicators with battery and error indicators

const RobotIndicatorComponent = {
  props: {
    robotName: {
      type: String,
      required: true
    },
    isSelected: {
      type: Boolean,
      default: false
    },
    isOnline: {
      type: Boolean,
      default: false
    },
    robotStatus: {
      type: Object,
      default: () => ({})
    },
    motorData: {
      type: Object,
      default: () => ({})
    },
    // Add updateKey prop to force updates only when needed
    updateKey: {
      type: Number,
      default: 0
    }
  },
  
  inject: ['motorDataService'],
  
  computed: {
    hasMotorData() {
      // Use cached data from the motor data service for better performance
      return this.motorDataService.hasMotorData(this.robotName, this.motorData);
    },
    
    areAllValuesZero() {
      return this.motorDataService.areAllValuesZero(this.robotName, this.motorData);
    },
    
    statusColor() {
      return this.getStatusColor();
    },
    
    displayName() {
      return this.robotName.replace('base', '').replace('-', '');
    },
    
    // Get battery percentage
    batteryLevel() {
      if (this.robotStatus && typeof this.robotStatus.battery_soc === 'number') {
        return this.robotStatus.battery_soc;
      }
      return null;
    },
    
    // Get battery bar color based on level
    batteryBarColor() {
      if (this.batteryLevel === null) return 'bg-gray-400';
      if (this.batteryLevel < 20) return 'bg-red-500';
      if (this.batteryLevel < 50) return 'bg-yellow-500';
      return 'bg-green-500';
    },
    
    // Get battery text color based on level
    batteryTextColor() {
      if (this.batteryLevel === null) return 'text-white';
      if (this.batteryLevel < 20) return 'text-red-200';
      if (this.batteryLevel < 50) return 'text-yellow-200';
      return 'text-green-200';
    },
    
    // Get active errors
    activeErrors() {
      if (!this.robotStatus || !this.robotStatus.watch_doggo_error_rm) {
        return [];
      }
      return this.robotStatus.watch_doggo_error_rm || [];
    },
    
    // Get error count
    errorCount() {
      return this.activeErrors.length;
    },
    
    // Check if robot has critical errors
    hasCriticalError() {
      return this.activeErrors.some(error => 
        ['1416', '1417', '3605'].includes(error.error_code)
      );
    },
    
    // Get error badge color based on error severity
    errorBadgeColor() {
      if (this.errorCount === 0) return '';
      
      // Check for critical errors (overtemperature)
      const hasCriticalError = this.activeErrors.some(error => 
        ['1416', '1417'].includes(error.error_code)
      );
      
      if (hasCriticalError) {
        return 'bg-red-600 text-white';
      }
      
      // Check for motor errors
      const hasMotorError = this.activeErrors.some(error => 
        error.error_code === '1201'
      );
      
      if (hasMotorError) {
        return 'bg-orange-500 text-white';
      }
      
      // Default error color
      return 'bg-yellow-500 text-black';
    },
    
    // Get the most severe error code for display
    mostSevereError() {
      if (this.errorCount === 0) return null;
      
      // Priority: critical errors first
      const criticalError = this.activeErrors.find(error => 
        ['1416', '1417', '3605'].includes(error.error_code)
      );
      if (criticalError) return criticalError.error_code;
      
      // Then return any other error
      return this.activeErrors[0]?.error_code;
    },
    
    // Cache the classes to reduce re-rendering
    buttonClasses() {
      const classes = [
        'robot-button w-14 h-14 md:w-16 md:h-16 rounded-lg flex items-center justify-center text-white transition-colors relative'
      ];
      
      // Add status color
      classes.push(this.statusColor);
      
      // Add motor data border
      if (this.hasMotorData && !this.areAllValuesZero) {
        classes.push('border-4 border-blue-300');
      } else if (this.hasMotorData && this.areAllValuesZero) {
        classes.push('border-4 border-yellow-300');
      }
      
      // Add selection ring
      if (this.isSelected) {
        classes.push('ring-2 ring-black');
      }
      
      // Removed all error rings - button colors already indicate status
      
      return classes;
    }
  },
  
  methods: {
    getStatusColor() {
      // If robot is offline (not pingable), show as gray
      if (!this.isOnline) {
        return 'bg-gray-400';
      }
      
      const status = this.robotStatus || {};
      const workingStatus = (status.working_status || '').toLowerCase();
      
      // If estop engaged, show as red
      if (status.soft_estop_engaged) {
        return 'bg-red-500';
      }
      
      // Check multiple possible ways charging might be indicated
      if (status.is_charging || workingStatus === 'charging') {
        return 'bg-blue-900';
      }
      
      // If cleaning or navigating, show as green
      if (workingStatus === 'cleaning' || workingStatus === 'navigation') {
        return 'bg-green-500';
      }
      
      // If idle, show as blue
      if (workingStatus === 'idle') {
        return 'bg-blue-900';
      }
      
      // Default color for other online states
      return 'bg-yellow-500';
    },
    
    onClick() {
      this.$emit('select-robot', this.robotName);
    }
  },
  
  template: `
    <button
      @click="onClick"
      :class="buttonClasses"
      :title="errorCount > 0 ? 'Errors: ' + activeErrors.map(e => e.error_code).join(', ') : robotName"
    >
      <span class="robot-name" v-text="displayName"></span>
      
      <!-- Battery level bar -->
      <div 
        v-if="isOnline && batteryLevel !== null"
        :class="['battery-bar', batteryBarColor]"
        :style="{width: batteryLevel + '%'}"
      ></div>
      
      <!-- Battery percentage text -->
      <span 
        v-if="isOnline && batteryLevel !== null"
        :class="['battery-text', batteryTextColor]"
        v-text="batteryLevel + '%'"
      ></span>
      
      <!-- Error count badge - positioned inside button boundaries with guaranteed orange background -->
      <span 
        v-if="isOnline && errorCount > 0" 
        class="absolute top-1 right-1 z-20 text-xs font-bold rounded-full h-4 w-4 flex items-center justify-center shadow-lg text-white"
        style="background-color: #f97316;"
        v-text="errorCount > 9 ? '9+' : errorCount">
      </span>
      
      <!-- Show motor indicator based on data status -->
      <span v-if="hasMotorData && !areAllValuesZero" 
          class="absolute top-0 right-0 transform translate-x-1/3 -translate-y-1/3 z-20">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 text-blue-500 bg-white rounded-full" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M11.3 1.046A1 1 0 0112 2v5h4a1 1 0 01.82 1.573l-7 10A1 1 0 018 18v-5H4a1 1 0 01-.82-1.573l7-10a1 1 0 011.12-.38z" clip-rule="evenodd" />
        </svg>
      </span>
      
      <!-- Show waiting indicator for zero-value motor data -->
      <span v-else-if="hasMotorData && areAllValuesZero" 
          class="absolute top-0 right-0 transform translate-x-1/3 -translate-y-1/3 z-20">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 text-yellow-500 bg-white rounded-full" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clip-rule="evenodd" />
        </svg>
      </span>
    </button>
  `
};