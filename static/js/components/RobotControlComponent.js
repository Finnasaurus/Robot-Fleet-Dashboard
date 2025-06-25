// RobotControlComponent.js
// A comprehensive robot control panel component for the dashboard

const RobotControlComponent = {
  props: {
    robotName: {
      type: String,
      required: true
    },
    isOnline: {
      type: Boolean,
      default: false
    },
    robotStatus: {
      type: Object,
      default: () => ({})
    }
  },
  
  data() {
    return {
      loading: false,
      lastCommand: null,
      commandHistory: [],
      cleaningModeSettings: {
        vacuum: 0,
        roller: 0,
        gutter: false
      },
      navigationTarget: {
        x: 0,
        y: 0,
        theta: 0
      },
      processSettings: {
        selectedProcess: '',
        selectedZones: [],
        order: 'ASCENDING'
      },
      showAdvanced: false,
      confirmDialog: {
        show: false,
        action: '',
        title: '',
        message: ''
      }
    };
  },
  
  computed: {
    canControl() {
      return this.isOnline && !this.loading;
    },
    
    isCharging() {
      return this.robotStatus?.is_charging || false;
    },
    
    isEstopEngaged() {
      return this.robotStatus?.soft_estop_engaged || false;
    },
    
    workingStatus() {
      return this.robotStatus?.working_status || 'Unknown';
    },
    
    batteryLevel() {
      return this.robotStatus?.battery_soc || 0;
    },
    
    hasActiveErrors() {
      return this.robotStatus?.watch_doggo_error_rm?.length > 0;
    }
  },
  
  methods: {
    async executeCommand(endpoint, payload = {}, requiresConfirmation = false) {
    if (requiresConfirmation) {
        return this.showConfirmDialog(endpoint, payload);
    }
    
    this.loading = true;
    try {
        const requestPayload = {
        robot_name: this.robotName,
        ...payload
        };
        
        // Use the Flask proxy endpoint (NOT direct robot API)
        const response = await fetch(`/api/robot-control/${endpoint}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
            // No Authorization header needed - Flask proxy handles it
        },
        body: JSON.stringify(requestPayload)
        });
        
        const result = await response.json();
        
        this.lastCommand = {
        command: endpoint,
        timestamp: new Date(),
        success: response.ok,
        result: result
        };
        
        this.commandHistory.unshift(this.lastCommand);
        if (this.commandHistory.length > 10) {
        this.commandHistory = this.commandHistory.slice(0, 10);
        }
        
        if (response.ok) {
        this.$emit('command-success', {
            command: endpoint,
            result: result
        });
        } else {
        this.$emit('command-error', {
            command: endpoint,
            error: result.error || result
        });
        }
        
        return result;
    } catch (error) {
        console.error('Command execution error:', error);
        this.$emit('command-error', {
        command: endpoint,
        error: error.message
        });
    } finally {
        this.loading = false;
    }
    },

    showConfirmDialog(endpoint, payload) {
      const confirmActions = {
        'stop': {
          title: 'Stop Robot',
          message: `Are you sure you want to stop ${this.robotName}?`
        },
        'reset_soft_estop': {
          title: 'Reset E-Stop',
          message: `Are you sure you want to reset the E-Stop for ${this.robotName}?`
        },
        'start_charging': {
          title: 'Start Charging',
          message: `Start charging ${this.robotName}?`
        },
        'docking': {
          title: 'Dock Robot',
          message: `Send ${this.robotName} to dock?`
        }
      };
      
      const action = confirmActions[endpoint] || {
        title: 'Confirm Action',
        message: `Execute ${endpoint} for ${this.robotName}?`
      };
      
      this.confirmDialog = {
        show: true,
        action: endpoint,
        payload: payload,
        title: action.title,
        message: action.message
      };
    },
    
    async confirmAction() {
      await this.executeCommand(this.confirmDialog.action, this.confirmDialog.payload, false);
      this.confirmDialog.show = false;
    },
    
    cancelAction() {
      this.confirmDialog.show = false;
    },
    
    // Function 2: Start Charging
    async startCharging() {
      await this.executeCommand('start_charging');
    },
    
    // Function 3: Stop Charging
    async stopCharging() {
      await this.executeCommand('stop_charging');
    },
    
    // Function 4: Navigate to Dock
    async navigateToDock() {
      await this.executeCommand('navigate_back_to_dock', {}, true);
    },
    
    // Function 5: Start Docking
    async startDocking() {
      await this.executeCommand('docking', { action: 'dock' }, true);
    },
    
    // Function 6: Undock
    async undock() {
      await this.executeCommand('docking', { action: 'undock' });
    },
    
    // Function 7: Pause Robot
    async pauseRobot() {
      await this.executeCommand('pause');
    },
    
    // Function 8: Resume Robot
    async resumeRobot() {
      await this.executeCommand('resume');
    },
    
    // Function 9: Stop Robot
    async stopRobot() {
      await this.executeCommand('stop', {}, true);
    },
    
    // Function 10: Reset E-Stop
    async resetEstop() {
      await this.executeCommand('reset_soft_estop', {}, true);
    },
    
    // Function 11: Start Cleaning Process
    async startCleaningProcess() {
      if (!this.processSettings.selectedProcess) {
        alert('Please select a cleaning process first');
        return;
      }
      
      const payload = {
        process: this.processSettings.selectedProcess,
        order: this.processSettings.order
      };
      
      if (this.processSettings.selectedZones.length > 0) {
        payload.type = 'selection';
        payload.selection = this.processSettings.selectedZones;
      }
      
      await this.executeCommand('start_process', payload);
    },
    
    // Additional Functions
    async setCleaningMode() {
      await this.executeCommand('set_cleaning_mode', this.cleaningModeSettings);
    },
    
    async navigateToPoint() {
      const payload = {
        pose2d: [
          this.navigationTarget.x,
          this.navigationTarget.y,
          this.navigationTarget.theta
        ]
      };
      await this.executeCommand('navigation', payload);
    },
    
    async emergencyStop() {
      // This is different from pause - it's an immediate stop
      await this.executeCommand('manage_goals', {
        exec_code: 5,
        argument: "100"
      }, true);
    },
    
    async checkBattery() {
      await this.executeCommand('battery_soc');
    },
    
    async getCleaningStats() {
      await this.executeCommand('cleaning_stats');
    },
    
    getStatusBadgeClass() {
      if (!this.isOnline) return 'bg-gray-500';
      if (this.isEstopEngaged) return 'bg-red-500';
      if (this.hasActiveErrors) return 'bg-orange-500';
      if (this.isCharging) return 'bg-blue-500';
      if (this.workingStatus.toLowerCase() === 'cleaning') return 'bg-green-500';
      return 'bg-yellow-500';
    },
    
    formatTimestamp(timestamp) {
      return new Date(timestamp).toLocaleTimeString();
    }
  },
  
  template: `
    <div class="bg-white rounded-lg shadow-lg p-6">
      <!-- Header -->
      <div class="flex items-center justify-between mb-6">
        <h3 class="text-lg font-semibold flex items-center gap-2">
          <svg class="h-5 w-5 text-blue-600" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M11.3 1.046A1 1 0 0112 2v5h4a1 1 0 01.82 1.573l-7 10A1 1 0 018 18v-5H4a1 1 0 01-.82-1.573l7-10a1 1 0 011.12-.38z" clip-rule="evenodd" />
          </svg>
          {{ robotName }} Controls
        </h3>
        <div class="flex items-center gap-2">
          <span :class="['px-2 py-1 text-xs font-medium rounded-full text-white', getStatusBadgeClass()]">
            {{ workingStatus }}
          </span>
          <span v-if="batteryLevel" class="text-sm text-gray-600">
            Battery: {{ batteryLevel }}%
          </span>
        </div>
      </div>
      
      <!-- Quick Status Alerts -->
      <div v-if="!isOnline" class="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
        <p class="text-red-800 text-sm">Robot is offline - controls disabled</p>
      </div>
      
      <div v-if="isEstopEngaged" class="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
        <p class="text-red-800 text-sm">E-Stop is engaged</p>
      </div>
      
      <div v-if="hasActiveErrors" class="mb-4 p-3 bg-orange-50 border border-orange-200 rounded-lg">
        <p class="text-orange-800 text-sm">Robot has active errors</p>
      </div>
      
      <!-- Main Control Buttons Grid -->
      <div class="grid grid-cols-2 md:grid-cols-3 gap-3 mb-6">
        <!-- Emergency Controls -->
        <button
          @click="resetEstop"
          :disabled="!canControl || !isEstopEngaged"
          :class="[
            'p-3 rounded-lg font-medium text-sm transition-colors',
            isEstopEngaged && canControl 
              ? 'bg-red-500 hover:bg-red-600 text-white' 
              : 'bg-gray-100 text-gray-400 cursor-not-allowed'
          ]"
        >
          Reset E-Stop
        </button>
        
        <button
          @click="stopRobot"
          :disabled="!canControl"
          :class="[
            'p-3 rounded-lg font-medium text-sm transition-colors',
            canControl 
              ? 'bg-red-500 hover:bg-red-600 text-white' 
              : 'bg-gray-100 text-gray-400 cursor-not-allowed'
          ]"
        >
          Stop
        </button>
        
        <button
          @click="emergencyStop"
          :disabled="!canControl"
          :class="[
            'p-3 rounded-lg font-medium text-sm transition-colors',
            canControl 
              ? 'bg-red-600 hover:bg-red-700 text-white' 
              : 'bg-gray-100 text-gray-400 cursor-not-allowed'
          ]"
        >
          Emergency Stop
        </button>
        
        <!-- Navigation Controls -->
        <button
          @click="pauseRobot"
          :disabled="!canControl"
          :class="[
            'p-3 rounded-lg font-medium text-sm transition-colors',
            canControl 
              ? 'bg-yellow-500 hover:bg-yellow-600 text-white' 
              : 'bg-gray-100 text-gray-400 cursor-not-allowed'
          ]"
        >
          Pause
        </button>
        
        <button
          @click="resumeRobot"
          :disabled="!canControl"
          :class="[
            'p-3 rounded-lg font-medium text-sm transition-colors',
            canControl 
              ? 'bg-green-500 hover:bg-green-600 text-white' 
              : 'bg-gray-100 text-gray-400 cursor-not-allowed'
          ]"
        >
          Resume
        </button>
        
        <button
          @click="navigateToDock"
          :disabled="!canControl"
          :class="[
            'p-3 rounded-lg font-medium text-sm transition-colors',
            canControl 
              ? 'bg-blue-500 hover:bg-blue-600 text-white' 
              : 'bg-gray-100 text-gray-400 cursor-not-allowed'
          ]"
        >
          Go to Dock
        </button>
        
        <!-- Charging Controls -->
        <button
          @click="startCharging"
          :disabled="!canControl || isCharging"
          :class="[
            'p-3 rounded-lg font-medium text-sm transition-colors',
            canControl && !isCharging
              ? 'bg-blue-500 hover:bg-blue-600 text-white' 
              : 'bg-gray-100 text-gray-400 cursor-not-allowed'
          ]"
        >
          Start Charging
        </button>
        
        <button
          @click="stopCharging"
          :disabled="!canControl || !isCharging"
          :class="[
            'p-3 rounded-lg font-medium text-sm transition-colors',
            canControl && isCharging
              ? 'bg-orange-500 hover:bg-orange-600 text-white' 
              : 'bg-gray-100 text-gray-400 cursor-not-allowed'
          ]"
        >
          Stop Charging
        </button>
        
        <!-- Docking Controls -->
        <button
          @click="startDocking"
          :disabled="!canControl"
          :class="[
            'p-3 rounded-lg font-medium text-sm transition-colors',
            canControl 
              ? 'bg-purple-500 hover:bg-purple-600 text-white' 
              : 'bg-gray-100 text-gray-400 cursor-not-allowed'
          ]"
        >
          Dock
        </button>
      </div>
      
      <!-- Advanced Controls Toggle -->
      <div class="border-t pt-4">
        <button
          @click="showAdvanced = !showAdvanced"
          class="w-full p-2 text-sm text-gray-600 hover:text-gray-800 transition-colors"
        >
          {{ showAdvanced ? 'Hide Advanced Controls' : 'Show Advanced Controls' }}
        </button>
      </div>
      
      <!-- Advanced Controls -->
      <div v-if="showAdvanced" class="mt-4 space-y-4">
        <!-- Cleaning Mode Settings -->
        <div class="bg-gray-50 rounded-lg p-4">
          <h4 class="font-medium text-sm mb-3">Cleaning Mode Settings</h4>
          <div class="grid grid-cols-2 gap-3 mb-3">
            <div>
              <label class="block text-xs text-gray-600 mb-1">Vacuum Level (0-3)</label>
              <input
                v-model.number="cleaningModeSettings.vacuum"
                type="number"
                min="0"
                max="3"
                class="w-full px-2 py-1 text-sm border rounded"
              >
            </div>
            <div>
              <label class="block text-xs text-gray-600 mb-1">Roller Level (0-2)</label>
              <input
                v-model.number="cleaningModeSettings.roller"
                type="number"
                min="0"
                max="2"
                class="w-full px-2 py-1 text-sm border rounded"
              >
            </div>
          </div>
          <div class="mb-3">
            <label class="flex items-center text-sm">
              <input
                v-model="cleaningModeSettings.gutter"
                type="checkbox"
                class="mr-2"
              >
              Enable Gutter Brush
            </label>
          </div>
          <button
            @click="setCleaningMode"
            :disabled="!canControl"
            class="w-full p-2 bg-green-500 hover:bg-green-600 text-white text-sm rounded transition-colors disabled:bg-gray-300"
          >
            Apply Cleaning Settings
          </button>
        </div>
        
        <!-- Navigation Controls -->
        <div class="bg-gray-50 rounded-lg p-4">
          <h4 class="font-medium text-sm mb-3">Manual Navigation</h4>
          <div class="grid grid-cols-3 gap-2 mb-3">
            <div>
              <label class="block text-xs text-gray-600 mb-1">X Position</label>
              <input
                v-model.number="navigationTarget.x"
                type="number"
                step="0.1"
                class="w-full px-2 py-1 text-sm border rounded"
              >
            </div>
            <div>
              <label class="block text-xs text-gray-600 mb-1">Y Position</label>
              <input
                v-model.number="navigationTarget.y"
                type="number"
                step="0.1"
                class="w-full px-2 py-1 text-sm border rounded"
              >
            </div>
            <div>
              <label class="block text-xs text-gray-600 mb-1">Rotation (?)</label>
              <input
                v-model.number="navigationTarget.theta"
                type="number"
                step="0.1"
                class="w-full px-2 py-1 text-sm border rounded"
              >
            </div>
          </div>
          <button
            @click="navigateToPoint"
            :disabled="!canControl"
            class="w-full p-2 bg-blue-500 hover:bg-blue-600 text-white text-sm rounded transition-colors disabled:bg-gray-300"
          >
            Navigate to Point
          </button>
        </div>
        
        <!-- Process Control -->
        <div class="bg-gray-50 rounded-lg p-4">
          <h4 class="font-medium text-sm mb-3">Cleaning Process</h4>
          <div class="space-y-3">
            <div>
              <label class="block text-xs text-gray-600 mb-1">Process Name</label>
              <input
                v-model="processSettings.selectedProcess"
                type="text"
                placeholder="e.g., T2L1_Arrival_Belts"
                class="w-full px-2 py-1 text-sm border rounded"
              >
            </div>
            <div>
              <label class="block text-xs text-gray-600 mb-1">Execution Order</label>
              <select v-model="processSettings.order" class="w-full px-2 py-1 text-sm border rounded">
                <option value="ASCENDING">Ascending</option>
                <option value="DESCENDING">Descending</option>
                <option value="combined">Combined</option>
                <option value="reverse">Reverse</option>
              </select>
            </div>
            <button
              @click="startCleaningProcess"
              :disabled="!canControl || !processSettings.selectedProcess"
              class="w-full p-2 bg-green-500 hover:bg-green-600 text-white text-sm rounded transition-colors disabled:bg-gray-300"
            >
              Start Cleaning Process
            </button>
          </div>
        </div>
        
        <!-- Quick Actions -->
        <div class="bg-gray-50 rounded-lg p-4">
          <h4 class="font-medium text-sm mb-3">Quick Actions</h4>
          <div class="grid grid-cols-2 gap-2">
            <button
              @click="checkBattery"
              :disabled="!canControl"
              class="p-2 bg-gray-500 hover:bg-gray-600 text-white text-sm rounded transition-colors disabled:bg-gray-300"
            >
              Check Battery
            </button>
            <button
              @click="getCleaningStats"
              :disabled="!canControl"
              class="p-2 bg-gray-500 hover:bg-gray-600 text-white text-sm rounded transition-colors disabled:bg-gray-300"
            >
              Get Stats
            </button>
          </div>
        </div>
      </div>
      
      <!-- Command History -->
      <div v-if="commandHistory.length > 0" class="mt-6 border-t pt-4">
        <h4 class="font-medium text-sm mb-2">Recent Commands</h4>
        <div class="space-y-2 max-h-32 overflow-y-auto">
          <div
            v-for="cmd in commandHistory.slice(0, 5)"
            :key="cmd.timestamp"
            :class="[
              'text-xs p-2 rounded',
              cmd.success ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'
            ]"
          >
            <div class="flex justify-between">
              <span class="font-medium">{{ cmd.command }}</span>
              <span>{{ formatTimestamp(cmd.timestamp) }}</span>
            </div>
            <div v-if="!cmd.success" class="text-red-600 mt-1">
              Error: {{ cmd.result?.message || 'Unknown error' }}
            </div>
          </div>
        </div>
      </div>
      
      <!-- Loading Indicator -->
      <div v-if="loading" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div class="bg-white rounded-lg p-6 max-w-sm">
          <div class="flex items-center space-x-3">
            <svg class="animate-spin h-5 w-5 text-blue-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <span class="text-gray-700">Executing command...</span>
          </div>
        </div>
      </div>
      
      <!-- Confirmation Dialog -->
      <div v-if="confirmDialog.show" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div class="bg-white rounded-lg p-6 max-w-md">
          <h3 class="text-lg font-medium mb-2">{{ confirmDialog.title }}</h3>
          <p class="text-gray-600 mb-4">{{ confirmDialog.message }}</p>
          <div class="flex justify-end space-x-3">
            <button
              @click="cancelAction"
              class="px-4 py-2 text-gray-600 border border-gray-300 rounded hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              @click="confirmAction"
              class="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600"
            >
              Confirm
            </button>
          </div>
        </div>
      </div>
    </div>
  `
};