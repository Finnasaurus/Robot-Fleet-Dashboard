// Built with Claude Badge Component
// Add this to your dashboard

const ClaudeBadge = {
    template: `
        <div class="claude-badge" 
             @click="showModal = true"
             :class="{ 'animate-pulse': isHovered }"
             @mouseenter="isHovered = true" 
             @mouseleave="isHovered = false">
            
            <!-- Badge -->
            <div class="inline-flex items-center bg-gradient-to-r from-blue-500 to-purple-600 text-white px-3 py-1 rounded-full text-xs font-medium cursor-pointer shadow-lg hover:shadow-xl transition-all duration-300">
                <span class="mr-1">🤖</span>
                <span>Built with Claude</span>
                <span class="ml-1">✨</span>
            </div>
            
            <!-- Modal -->
            <div v-if="showModal" 
                 class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
                 @click="showModal = false">
                <div class="bg-white rounded-lg p-6 max-w-md mx-4 transform transition-all duration-300"
                     @click.stop>
                    <div class="text-center">
                        <h3 class="text-xl font-bold text-gray-800 mb-4">
                            🤖 Development Story
                        </h3>
                        <p class="text-gray-600 mb-4">
                            This entire robot fleet dashboard was built as a personal experiment 
                            to test Claude's capabilities while creating something practical.
                        </p>
                        <p class="text-gray-600 mb-6">
                            Every line of code, architecture decision, and feature was developed 
                            through human-AI collaboration.
                        </p>
                        <div class="bg-blue-50 rounded-lg p-4 mb-4">
                            <p class="text-blue-800 text-sm font-medium">
                                From ping checker → Full production dashboard
                            </p>
                            <p class="text-blue-600 text-xs mt-1">
                                Showcasing what's possible with human creativity + AI capabilities
                            </p>
                        </div>
                        <button @click="showModal = false" 
                                class="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded font-medium transition-colors">
                            Amazing! 🚀
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `,
    
    data() {
        return {
            showModal: false,
            isHovered: false
        }
    }
};

// CSS for the badge
const badgeCSS = `
.claude-badge {
    position: fixed;
    bottom: 20px;
    right: 20px;
    z-index: 40;
}

@media (max-width: 768px) {
    .claude-badge {
        bottom: 80px;
        right: 16px;
    }
}

.claude-badge:hover {
    transform: translateY(-2px);
}
`;
