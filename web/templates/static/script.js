class Nav2Controller {
    constructor() {
        this.apiBase = '/';
        this.statusEl = document.getElementById('status');
        this.locationsEl = document.getElementById('locations-data');
        this.gridButtonsEl = document.getElementById('grid-buttons');
        this.refreshBtn = document.getElementById('refresh-status');

        this.locButtons = [];  // Will store dynamically created buttons
        this.locations = {};   // Cache for locations data

        this.init();
    }

    init() {
        this.refreshBtn.addEventListener('click', () => this.refreshStatus());
        
        document.getElementById('reload-locations')?.addEventListener('click', () => {
            this.loadLocations().then(() => this.createLocationButtons());
        });

        
        // Load initial data
        this.loadLocations().then(() => {
            this.createLocationButtons();
            this.refreshStatus();
        });
        
        // Auto-refresh status every 3 seconds
        setInterval(() => this.refreshStatus(), 3000);
    }

    async apiCall(endpoint, options = {}) {
        try {
            const response = await fetch(this.apiBase + endpoint, options);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            return await response.json();
        } catch (error) {
            console.error('API error:', error);
            throw error;
        }
    }

    async loadLocations() {
        try {
            this.locations = await this.apiCall('locations');
            this.locationsEl.textContent = JSON.stringify(this.locations, null, 2);
            return this.locations;
        } catch (error) {
            this.locationsEl.textContent = 'Failed to load locations';
            throw error;
        }
    }

    createLocationButtons() {
        // Clear existing buttons
        this.gridButtonsEl.innerHTML = '';
        this.locButtons = [];

        // Create button for each location
        Object.entries(this.locations).forEach(([target, coords]) => {
            const btn = document.createElement('button');
            btn.className = 'loc-btn';
            btn.dataset.target = target;
            btn.textContent = this.getButtonLabel(target);
            
            // Add click handler
            btn.addEventListener('click', (e) => this.gotoLocation(target, e.target));
            this.locButtons.push(btn);
            
            this.gridButtonsEl.appendChild(btn);
        });
    }

    getButtonLabel(target) {
        const icons = {
            'home': '🏠',
            'loc1': '📍',
            'loc2': '📍',
            'loc3': '📍',
            'dock': '⚓',
            'charging': '🔋'
        };
        return `${icons[target] || '📍'} ${target.toUpperCase()}`;
    }

    async gotoLocation(target, btn) {
        btn.textContent = '⏳ Sending...';
        btn.classList.add('sending');
        btn.disabled = true;

        try {
            const result = await this.apiCall('goto', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ target })
            });
            
            this.updateStatus(`✅ Sent to ${target}: ${result.x.toFixed(2)}, ${result.y.toFixed(2)}`);
            console.log('Goal sent:', result);
        } catch (error) {
            this.updateStatus(`❌ Error: ${error.message}`);
        } finally {
            btn.textContent = this.getButtonLabel(target);
            btn.classList.remove('sending');
            btn.disabled = false;
        }
    }

    async refreshStatus() {
        try {
            const data = await this.apiCall('status');
            this.updateStatus(data.status);
        } catch (error) {
            this.updateStatus('❌ Connection failed');
        }
    }

    updateStatus(message) {
        this.statusEl.textContent = message;
        
        // Color coding
        this.statusEl.className = '';
        if (message.includes('idle') || message.includes('reached')) {
            this.statusEl.classList.add('idle');
        } else if (message.includes('navigating')) {
            this.statusEl.classList.add('navigating');
        } else if (message.includes('error')) {
            this.statusEl.classList.add('error');
        }
    }
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', () => {
    new Nav2Controller();
});
