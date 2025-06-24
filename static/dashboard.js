import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Monitor, Battery, Activity, AlertCircle } from 'lucide-react';

const RobotDashboard = () => {
  const [selectedRobot, setSelectedRobot] = useState('base1');
  const [logs, setLogs] = useState({ 'API Errors': {}, 'Robot Errors': {} });
  const [status, setStatus] = useState('Idle');
  const [lastUpdate, setLastUpdate] = useState('N/A');

  const robots = ['base1', 'base2', 'base3'];

  const fetchData = async () => {
    try {
      const response = await fetch(`/logs?robot_name=${selectedRobot}`);
      const data = await response.json();
      setLogs(data);
      setLastUpdate(new Date().toLocaleString());
    } catch (error) {
      console.error('Error fetching logs:', error);
    }

    try {
      const response = await fetch(`/status?robot_name=${selectedRobot}`);
      const data = await response.json();
      setStatus(data.status);
    } catch (error) {
      console.error('Error fetching status:', error);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 15000);
    return () => clearInterval(interval);
  }, [selectedRobot]);

  const getStatusColor = (status) => {
    switch (status.toLowerCase()) {
      case 'cleaning': return 'bg-green-100 text-green-800';
      case 'charging': return 'bg-blue-100 text-blue-800';
      case 'navigation': return 'bg-purple-100 text-purple-800';
      case 'e-stop engaged': return 'bg-red-100 text-red-800';
      case 'offline': return 'bg-gray-100 text-gray-800';
      default: return 'bg-yellow-100 text-yellow-800';
    }
  };

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Monitor className="h-8 w-8" />
          Robot Monitor Dashboard
        </h1>
        <select
          value={selectedRobot}
          onChange={(e) => setSelectedRobot(e.target.value)}
          className="px-4 py-2 border rounded-lg"
        >
          {robots.map(robot => (
            <option key={robot} value={robot}>{robot}</option>
          ))}
        </select>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5" />
              Current Status
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`inline-block px-4 py-2 rounded-full font-semibold ${getStatusColor(status)}`}>
              {status}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Battery className="h-5 w-5" />
              System Info
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p>Last Updated: {lastUpdate}</p>
          </CardContent>
        </Card>

        <Card className="md:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertCircle className="h-5 w-5" />
              Error Logs
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <h3 className="font-semibold mb-2">API Errors</h3>
                <div className="bg-gray-50 p-4 rounded-lg">
                  {Object.entries(logs['API Errors']).map(([error, times]) => (
                    <div key={error} className="mb-2">
                      <p className="font-medium">Error {error}: {times.length} occurrences</p>
                      <div className="ml-4 text-sm text-gray-600">
                        {times.map((time, i) => (
                          <p key={i}>{new Date(time).toLocaleString()}</p>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <h3 className="font-semibold mb-2">Robot Errors</h3>
                <div className="bg-gray-50 p-4 rounded-lg">
                  {logs['Robot Errors'][selectedRobot]?.map((error, index) => (
                    <div key={index} className="mb-2">
                      <p>{error[0]} at {error[1]}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default RobotDashboard;
