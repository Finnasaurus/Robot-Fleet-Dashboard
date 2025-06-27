// RobotManagementComponent.js
// A comprehensive robot fleet management component for the dashboard

const RobotManagementComponent = {
  data() {
    return {
      robots: [],
      loading: false,
      error: null,
      editingRobot: null,
      showAddForm: false,
      newRobot: {
        id: '',
        name: '',
        ip: '',
        has_motors: false
      },
      successMessage: null
    };
  },
  
  computed: {
    canSaveNewRobot() {
      return this.newRobot.id && 
             this.newRobot.name && 
             this.newRobot.ip && 
             this.validateIP(this.newRobot.ip);
    }
  },
  
  mounted() {
    this.loadRobots();
  },
  
  methods: {
    async loadRobots() {
      this.loading = true;
      this.error = null;
      try {
        const response = await fetch('/api/robots');
        if (!response.ok) throw new Error('Failed to load robots');
        const data = await response.json();
        this.robots = data.robots || [];
      } catch (err) {
        this.error = err.message;
      } finally {
        this.loading = false;
      }
    },

    async addRobot() {
      if (!this.canSaveNewRobot) {
        this.error = 'All fields are required and IP must be valid';
        return;
      }

      this.loading = true;
      try {
        const response = await fetch('/api/robots', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(this.newRobot)
        });
        
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.error || 'Failed to add robot');
        }

        this.resetNewRobotForm();
        this.showAddForm = false;
        await this.loadRobots();
        this.showSuccess(`Robot ${this.newRobot.name} added successfully!`);
        this.error = null;
      } catch (err) {
        this.error = err.message;
      } finally {
        this.loading = false;
      }
    },

    async updateRobot(robotId, updatedData) {
      this.loading = true;
      try {
        const response = await fetch(`/api/robots/${robotId}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(updatedData)
        });
        
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.error || 'Failed to update robot');
        }

        this.editingRobot = null;
        await this.loadRobots();
        this.showSuccess(`Robot ${robotId} updated successfully!`);
        this.error = null;
      } catch (err) {
        this.error = err.message;
      } finally {
        this.loading = false;
      }
    },

    async deleteRobot(robotId) {
      if (!confirm(`Are you sure you want to delete robot ${robotId}? This action cannot be undone.`)) {
        return;
      }

      this.loading = true;
      try {
        const response = await fetch(`/api/robots/${robotId}`, {
          method: 'DELETE'
        });
        
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.error || 'Failed to delete robot');
        }

        await this.loadRobots();
        this.showSuccess(`Robot ${robotId} deleted successfully!`);
        this.error = null;
      } catch (err) {
        this.error = err.message;
      } finally {
        this.loading = false;
      }
    },

    validateIP(ip) {
      const ipRegex = /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/;
      return ipRegex.test(ip);
    },

    resetNewRobotForm() {
      this.newRobot = {
        id: '',
        name: '',
        ip: '',
        has_motors: false
      };
    },

    showSuccess(message) {
      this.successMessage = message;
      setTimeout(() => {
        this.successMessage = null;
      }, 5000);
    },

    sanitizeRobotId(value) {
      return value.toLowerCase().replace(/[^a-z0-9-]/g, '');
    },

    dismissError() {
      this.error = null;
    },

    dismissSuccess() {
      this.successMessage = null;
    }
  },
  
  template: `
    <div class="bg-white rounded-lg shadow-lg p-6">
      <!-- Header -->
      <div class="flex items-center justify-between mb-6">
        <h2 class="text-xl font-bold text-gray-800 flex items-center gap-2">
          <svg class="h-6 w-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-4m-5 0H3m2 0h3M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
          </svg>
          Robot Fleet Management
        </h2>
        <div class="flex gap-2">
          <button
            @click="loadRobots"
            :disabled="loading"
            class="flex items-center gap-2 px-3 py-2 bg-gray-500 text-white rounded hover:bg-gray-600 disabled:opacity-50 text-sm"
          >
            <svg :class="['h-4 w-4', loading ? 'animate-spin' : '']" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Refresh
          </button>
          <button
            @click="showAddForm = true"
            class="flex items-center gap-2 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 text-sm"
          >
            <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
            </svg>
            Add Robot
          </button>
        </div>
      </div>

      <!-- Success Alert -->
      <div v-if="successMessage" class="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg flex items-center gap-2">
        <svg class="h-5 w-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <span class="text-green-800 text-sm">{{ successMessage }}</span>
        <button
          @click="dismissSuccess"
          class="ml-auto text-green-600 hover:text-green-800"
        >
          <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <!-- Error Alert -->
      <div v-if="error" class="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2">
        <svg class="h-5 w-5 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <span class="text-red-800 text-sm">{{ error }}</span>
        <button
          @click="dismissError"
          class="ml-auto text-red-600 hover:text-red-800"
        >
          <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <!-- Add Robot Form -->
      <div v-if="showAddForm" class="mb-6 p-4 border border-blue-200 rounded-lg bg-blue-50">
        <h3 class="text-lg font-semibold mb-3">Add New Robot</h3>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium mb-1">Robot ID</label>
            <input
              type="text"
              v-model="newRobot.id"
              @input="newRobot.id = sanitizeRobotId($event.target.value)"
              placeholder="e.g., robot 1, robot-new"
              class="w-full px-3 py-2 border rounded text-sm"
            />
          </div>
          <div>
            <label class="block text-sm font-medium mb-1">Display Name</label>
            <input
              type="text"
              v-model="newRobot.name"
              placeholder="e.g., Robot 1"
              class="w-full px-3 py-2 border rounded text-sm"
            />
          </div>
          <div>
            <label class="block text-sm font-medium mb-1">IP Address</label>
            <input
              type="text"
              v-model="newRobot.ip"
              placeholder="192.168.1.100"
              :class="['w-full px-3 py-2 border rounded text-sm', 
                      newRobot.ip && !validateIP(newRobot.ip) ? 'border-red-300 bg-red-50' : '']"
            />
            <p v-if="newRobot.ip && !validateIP(newRobot.ip)" class="text-red-600 text-xs mt-1">
              Invalid IP address format
            </p>
          </div>
          <div class="flex items-center">
            <label class="flex items-center text-sm">
              <input
                type="checkbox"
                v-model="newRobot.has_motors"
                class="mr-2"
              />
              Has Motor Data
            </label>
          </div>
        </div>
        <div class="flex gap-2 mt-4">
          <button
            @click="addRobot"
            :disabled="loading || !canSaveNewRobot"
            class="flex items-center gap-2 px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600 disabled:opacity-50 text-sm"
          >
            <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
            </svg>
            Add Robot
          </button>
          <button
            @click="showAddForm = false; resetNewRobotForm(); error = null;"
            class="flex items-center gap-2 px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-600 text-sm"
          >
            <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
            Cancel
          </button>
        </div>
      </div>

      <!-- Robots Table -->
      <div class="overflow-x-auto">
        <table class="w-full border-collapse border border-gray-200">
          <thead>
            <tr class="bg-gray-50">
              <th class="border border-gray-200 px-4 py-2 text-left text-sm font-medium">Robot ID</th>
              <th class="border border-gray-200 px-4 py-2 text-left text-sm font-medium">Display Name</th>
              <th class="border border-gray-200 px-4 py-2 text-left text-sm font-medium">IP Address</th>
              <th class="border border-gray-200 px-4 py-2 text-left text-sm font-medium">Motor Data</th>
              <th class="border border-gray-200 px-4 py-2 text-center text-sm font-medium">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading && robots.length === 0">
              <td colspan="5" class="border border-gray-200 px-4 py-8 text-center text-gray-500">
                <svg class="h-6 w-6 animate-spin mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Loading robots...
              </td>
            </tr>
            <tr v-else-if="robots.length === 0">
              <td colspan="5" class="border border-gray-200 px-4 py-8 text-center text-gray-500">
                No robots configured
              </td>
            </tr>
            <robot-row
              v-for="robot in robots"
              :key="robot.id"
              :robot="robot"
              :is-editing="editingRobot === robot.id"
              :disabled="loading"
              @edit="editingRobot = robot.id"
              @cancel="editingRobot = null"
              @save="updateRobot"
              @delete="deleteRobot"
            ></robot-row>
          </tbody>
        </table>
      </div>

      <!-- Info Footer -->
      <div class="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded text-sm text-yellow-800">
        <strong>Note:</strong> Changes require a dashboard restart to take effect. Use the restart button or restart the server manually.
      </div>
    </div>
  `
};

// Individual Robot Row Component
const RobotRow = {
  props: {
    robot: {
      type: Object,
      required: true
    },
    isEditing: {
      type: Boolean,
      default: false
    },
    disabled: {
      type: Boolean,
      default: false
    }
  },
  
  data() {
    return {
      editData: {
        name: this.robot.name,
        ip: this.robot.ip,
        has_motors: this.robot.has_motors
      }
    };
  },
  
  watch: {
    robot: {
      handler(newRobot) {
        this.editData = {
          name: newRobot.name,
          ip: newRobot.ip,
          has_motors: newRobot.has_motors
        };
      },
      deep: true
    }
  },
  
  computed: {
    canSave() {
      return this.editData.name && 
             this.editData.ip && 
             this.validateIP(this.editData.ip);
    }
  },
  
  methods: {
    validateIP(ip) {
      const ipRegex = /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/;
      return ipRegex.test(ip);
    },
    
    handleSave() {
      if (this.canSave) {
        this.$emit('save', this.robot.id, this.editData);
      }
    },
    
    handleEdit() {
      this.$emit('edit');
    },
    
    handleCancel() {
      // Reset edit data
      this.editData = {
        name: this.robot.name,
        ip: this.robot.ip,
        has_motors: this.robot.has_motors
      };
      this.$emit('cancel');
    },
    
    handleDelete() {
      this.$emit('delete', this.robot.id);
    }
  },
  
  template: `
    <tr :class="isEditing ? 'bg-blue-50' : 'hover:bg-gray-50'">
      <td class="border border-gray-200 px-4 py-2 text-sm font-medium">{{ robot.id }}</td>
      
      <td class="border border-gray-200 px-4 py-2">
        <input
          v-if="isEditing"
          type="text"
          v-model="editData.name"
          class="w-full px-2 py-1 border rounded text-sm"
        />
        <span v-else class="text-sm">{{ robot.name }}</span>
      </td>
      
      <td class="border border-gray-200 px-4 py-2">
        <input
          v-if="isEditing"
          type="text"
          v-model="editData.ip"
          :class="['w-full px-2 py-1 border rounded text-sm font-mono', 
                  editData.ip && !validateIP(editData.ip) ? 'border-red-300 bg-red-50' : '']"
        />
        <span v-else class="text-sm font-mono">{{ robot.ip }}</span>
      </td>
      
      <td class="border border-gray-200 px-4 py-2">
        <label v-if="isEditing" class="flex items-center text-sm">
          <input
            type="checkbox"
            v-model="editData.has_motors"
            class="mr-2"
          />
          Enabled
        </label>
        <span v-else :class="['px-2 py-1 rounded text-xs', 
                            robot.has_motors ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600']">
          {{ robot.has_motors ? 'Enabled' : 'Disabled' }}
        </span>
      </td>
      
      <td class="border border-gray-200 px-4 py-2">
        <div v-if="isEditing" class="flex gap-1 justify-center">
          <button
            @click="handleSave"
            :disabled="disabled || !canSave"
            class="p-1 bg-green-500 text-white rounded hover:bg-green-600 disabled:opacity-50"
            title="Save"
          >
            <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
            </svg>
          </button>
          <button
            @click="handleCancel"
            :disabled="disabled"
            class="p-1 bg-gray-500 text-white rounded hover:bg-gray-600"
            title="Cancel"
          >
            <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <div v-else class="flex gap-1 justify-center">
          <button
            @click="handleEdit"
            :disabled="disabled"
            class="p-1 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50"
            title="Edit"
          >
            <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
            </svg>
          </button>
          <button
            @click="handleDelete"
            :disabled="disabled"
            class="p-1 bg-red-500 text-white rounded hover:bg-red-600 disabled:opacity-50"
            title="Delete"
          >
            <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        </div>
      </td>
    </tr>
  `
};