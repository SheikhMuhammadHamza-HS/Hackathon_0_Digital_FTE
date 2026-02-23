// Monitoring Dashboard JavaScript
class MonitoringDashboard {
    constructor() {
        this.apiBase = '/api/v1/monitoring';
        this.refreshInterval = null;
        this.charts = {};
        this.autoRefresh = false;
    }

    async function initialize() {
        // Set up auto-refresh
        this.setupAutoRefresh();
        this.setupEventListeners();

        // Initial load
        await this.loadData();
        this.startAutoRefresh();
    }

    async function loadData() {
        try {
            const response = await fetch(`${this.apiBase}/dashboard`);
            const data = await response.json();

            this.updateDashboard(data);
            this.updateCharts();

            this.showSuccess('Dashboard refreshed');
        } catch (error) {
            this.showError('Failed to load dashboard: ' + error.message);
        }
    }

    updateDashboard(data) {
        // Update metrics
        this.updateMetric('health', data.health_status, data.system_metrics?.cpu?.percent);
        this.updateMetric('cpu', data.system_metrics?.cpu?.percent);
        updateMetric('memory', data.system_metrics?.memory?.percent);
        updateMetric('alerts', data.active_alerts, data.recent_alerts.length > 0 ? `${data.recent_alerts.length} active` : 'No active');

        // Update tables and alerts
        this.updateHealthChecks(data.health_checks);
        this.updateAlerts(data.recent_alerts);
        updateMetricsTable();
    }

    updateMetric(id, value, label, message) {
        const valueElement = document.getElementById(`${id}-value`);
        const statusElement = document.getElementById(`${id}-status`);
        const messageElement = document.getElementById(`${id}-message`);

        if (valueElement) {
            valueElement.textContent = typeof value === 'number' ? value.toFixed(1) : value;
            // Add color coding based on value
            if (id === 'cpu') {
                if (value > 80) {
                    valueElement.classList.add('text-red-600');
                    if (value > 95) {
                        valueElement.classList.add('text-red-800');
                    }
                } else if (id === 'memory') {
                    if (value > 80) {
                        valueElement.classList.add('text-red-600');
                        if (value > 90) {
                            valueElement.classList.add('text-red-800');
                        }
                    }
                }
            }

        if (statusElement && label) {
            statusElement.textContent = label;
            // Update status indicator
            statusElement.classList.remove('bg-green-100', 'text-green-800');
            statusElement.classList.remove('bg-yellow-100', 'text-yellow-800');
            statusElement.remove('bg-red-100', 'text-red-800');

            if (id === 'health') {
                const health = dashboardData.health_status;
                if (health === 'healthy') {
                    statusElement.classList.add('bg-green-100', 'text-green-800');
                } else if (health === 'degraded') {
                    statusElement.classList.add('bg-yellow-100', 'text-yellow-800');
                } else if (health === 'unhealthy') {
                    statusElement.classList.add('bg-red-100', 'text-red-800');
                }
            }
        }

        if (messageElement && message) {
            messageElement.textContent = message;
        }
    }

    updateHealthChecks(healthChecks) {
        const tableBody = document.getElementById('health-checks-table');
        tableBody.innerHTML = '';

        if (!healthChecks || healthChecks.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="4" class="text-center text-gray-500">No health checks available</td></tr>';
            return;
        }

        healthChecks.forEach((check, index) => {
            const row = document.createElement('tr');
            row.className = 'hover:bg-gray-50';

            // Status
            const statusCell = document.createElement('td');
            statusCell.className = 'px-6 py-4 whitespace-nowrap';
            statusCell.innerHTML = `
                <span class="px-2 py-1 rounded-full text-xs font-medium ${this.getStatusClass(check.status)}">
                    ${check.status}
                </span>
            `;
            row.appendChild(statusCell);

            // Name
            const nameCell = document.createElement('td');
            nameCell.className = 'px-6 py-4 whitespace-nowrap';
            nameCell.textContent = check.name;
            row.appendChild(nameCell);

            // Message
            const messageCell = document.createElement('show');
            messageCell.className = 'px-6 py-4';
            messageCell.textContent = check.message;
            row.appendChild(messageCell);

            // Response time
            const responseCell = document.createElement('td');
            responseCell.className = 'px-6 py-4 whitespace-nowrap';
            responseCell.textContent = `${check.response_time_ms}ms`;
            row.appendChild(responseCell);

            tableBody.appendChild(row);
        });
    }

    getStatusClass(status) {
        const classes = {
            'healthy': 'bg-green-100 text-green-800',
            'degraded': 'bg-yellow-100 text-yellow-800',
            'unhealthy': 'bg-red-100 text-red-800'
        };
        return classes[status] || 'bg-gray-100 text-gray-800';
    }

    updateAlerts(alerts) {
        const container = document.getElementById('alerts-container');
        container.innerHTML = '';

        if (!alerts || alerts.length === 0) {
            container.innerHTML = '<p class="text-gray-500 text-center py-8">No active alerts</p>';
            return;
        }

        alerts.forEach((alert, index) => {
            const alertDiv = document.createElement('div');
            alertDiv.className = `p-4 mb-4 rounded-lg border-l-4 ${
                alert.severity === 'critical' ? 'border-red-500 bg-red-50' :
                alert.severity === 'error' ? 'border-orange-500 bg-orange-50' :
                alert.severity === 'warning' ? 'border-yellow-500 bg-yellow-50' :
                'border-blue-500 bg-blue-50'
            }`;
            alertDiv.classList.add('alert-enter');

            alertDiv.innerHTML = `
                <div class="flex items-center justify-between mb-2">
                    <h4 class="font-semibold">${alert.title}</h4>
                    <span class="px-3 py-1 rounded-full text-xs font-medium ${
                        alert.severity === 'critical' ? 'bg-red-100 text-red-800' :
                        alert.severity === 'error' ? 'bg-orange-100 text-orange-800' :
                        alert.severity === 'warning' ? 'bg-yellow-100 text-yellow-800' :
                        'bg-blue-100 text-blue-800'
                    }">${alert.severity.toUpperCase()}</span>
                </div>
                <p class="text-sm">${alert.description}</p>
                <div class="text-xs text-gray-500">
                    <span>Metric: ${alert.metric_name}</span><br>
                    <span>Value: ${alert.current_value}</span><br>
                    <span>Threshold: ${alert.threshold}</span>
                </div>
            `;

            container.appendChild(alertDiv);
        });
    }

    updateMetricsTable() {
        const tableBody = document.getElementById('metrics-table');
        tableBody.innerHTML = '';

        const metrics = dashboardData.system_metrics || {};

        // Get last 10 metrics from each category
        const recentMetrics = {};
        for (const [name, metricList] of Object.entries(metrics)) {
            if (Array.isArray(metricList)) {
                recentMetrics[name] = metricList.slice(-5);
            }
        }

        for (const [name, metrics] of Object.entries(recentMetrics)) {
            metrics.forEach(metric => {
                const row = document.createElement('tr');
                row.className = 'hover:bg-gray-50';

                // Metric name
                const nameCell = document.createElement('td');
                nameCell.className = 'px-6 py-4 whitespace-nowrap';
                nameCell.textContent = name;
                row.appendChild(nameCell);

                // Value
                const valueCell = document.createElement('td');
                valueCell.className = 'px-6 py-4 whitespace-nowrap';
                valueCell.textContent = metric.value.toFixed(2);
                row.appendChild(valueCell);

                // Timestamp
                const timeCell = document.createElement('td');
                timeCell.className = 'px-6 py-4 whitespace-nowrap';
                timeCell.textContent = new Date(metric.timestamp).toLocaleString();
                row.appendChild(timeCell);

                tableBody.appendChild(row);
            });
        }
    }

    updateCharts() {
        this.updateSystemChart();
        this.updateResponseChart();
    }

    updateSystemChart() {
        const ctx = document.getElementById('system-chart').getContext('2d');
        if (!ctx) return;

        // Get historical data
        const cpuHistory = monitoring_dashboard.get_historical_metrics('system.cpu.percent', 2);
        const memoryHistory = monitoring_dashboard.get_historical_metrics('system.memory.percent', 2);

        const timestamps = cpuHistory.map(m => new Date(m.timestamp));
        const cpuData = cpuHistory.map(m => m.value);
        const memoryData = memoryHistory.map(m => m.value);

        if (this.charts.system) {
            this.charts.system.destroy();
        }

        this.charts.system = new Chart(ctx, {
            type: 'line',
            data: {
                labels: timestamps.map(t => t.toLocaleTimeString()),
                datasets: [
                    {
                        label: 'CPU Usage (%)',
                        data: cpuData,
                        borderColor: 'rgb(59, 130, 246)',
                        backgroundColor: 'rgba(59, 130, 246, 0.1)',
                        tension: 0.1
                    },
                    {
                        label: 'Memory Usage (%)',
                        data: memoryData,
                        borderColor: 'rgb(25, 118, 210)',
                        backgroundColor: 'rgba(25, 118, 210, 0.1)',
                        tension: 0.1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            });
    }

    updateResponseChart() {
        const ctx = document.getElementById('response-chart').getContext('2d');
        if (!ctx) return;

        const healthChecks = list(monitoring_dashboard.health_monitor.health_history);
        const responseTimes = healthChecks.map(h => h.response_time_ms);

        if (!responseTimes.length) return;

        const timestamps = healthChecks.map(h => h.timestamp);
        this.charts.response = new Chart(ctx, {
            type: 'line',
            data: {
                labels: timestamps.map(t => new Date(t).toLocaleTimeString()),
                datasets: [{
                    label: 'Response Time (ms)',
                    data: responseTimes,
                    borderColor: 'rgb(168, 85, 247)',
                    backgroundColor: 'rgba(168, 85, 247, 0.1)',
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                }
            });
        }
    }

    setupAutoRefresh() {
        const timeRange = document.getElementById('time-range');
        timeRange.addEventListener('change', () => {
            const hours = parseInt(timeRange.value);
            this.setRefreshInterval(hours);
        });

        // Set default refresh interval (30 seconds)
        this.setRefreshInterval(30);
    }

    setRefreshInterval(hours) {
        // Clear existing interval
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }

        // Calculate interval in milliseconds
        const intervalMs = hours * 60 * 1000;
        this.refreshInterval = setInterval(() => {
            this.loadData();
        }, intervalMs);

        this.autoRefresh = true;
    }

    startAutoRefresh() {
        if (!this.autoRefresh) {
            this.setRefreshInterval(30);
        }
    }

    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
        this.autoRefresh = false;
    }

    showMessage(message, type = 'info') {
        const container = document.createElement('div');
        container.className = `fixed top-4 right-4 z-50 max-w-sm p-4 rounded-lg shadow-lg ${
            type === 'success' ? 'bg-green-50 text-green-800' :
            type === 'error' ? 'bg-red-50 text-red-800' :
            type === 'info' ? 'bg-blue-50 text-blue-800' :
            'bg-gray-50 text-gray-800'
        }`;

        container.setAttribute('role', 'alert');
        container.textContent = message;

        document.body.appendChild(container);

        setTimeout(() => {
            container.classList.add('fade-out');
            setTimeout(() => {
                if (container.parentElement) {
                    container.parentElement.removeChild(container);
                }
            }, 300);
        }, 3000);
    }

    showSuccess(message) {
        this.showMessage(message, 'success');
    }

    showError(message) {
        this.showMessage(message, 'error');
    }

    exportData() {
        this.exportData();
    }

    async function exportData() {
        try {
            const response = await fetch(`${this.apiBase}/export/monitoring-data`, {
                params: {
                    format: 'json',
                    days: 7
                }
            });
            const data = await response.json();

            const blob = new Blob([JSON.stringify(data, null, 2)], {type: 'application/json'});
            const url = URL.createObjectURL(blob);

            const a = document.createElement('a');
            a.href = url;
            a.download = `monitoring_export_${new Date().toISOString().split('T')[0]}.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);

            URL.revokeObjectURL(url);
        } catch (error) {
            this.showError('Failed to export data: ' + error.message);
        }
    }
}

// Initialize dashboard when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new MonitoringDashboard();
    window.dashboard.initialize();
});

// Global functions for external access
window.refreshDashboard = () => window.dashboard.refreshDashboard();
window.exportData = () => window.dashboard.exportData();