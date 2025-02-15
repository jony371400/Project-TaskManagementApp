import React, { useState, useEffect } from 'react';
import './App.css';
import { FaMoon, FaSun, FaRobot, FaTasks, FaClock, FaClipboardList } from 'react-icons/fa';
import io from 'socket.io-client';

function App() {
  const [tasks, setTasks] = useState([]);
  const [newTask, setNewTask] = useState({ name: '', description: '', due_date: '' });
  const [reminders, setReminders] = useState([]);
  const [reports, setReports] = useState(null);
  const [formError, setFormError] = useState('');
  const [darkMode, setDarkMode] = useState(false);
  const [socket, setSocket] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);

  // Initialize WebSocket connection
  useEffect(() => {
    const newSocket = io('http://127.0.0.1:5000');
    
    newSocket.on('connect', () => {
      console.log('Connected to WebSocket server');
    });

    newSocket.on('disconnect', () => {
      console.log('Disconnected from WebSocket server');
    });

    newSocket.on('status_update', (data) => {
      console.log('Received status update:', data);
      setReports(data);
      setLastUpdate(data.timestamp);
      // Refresh tasks list when receiving updates
      fetchTasks();
    });

    setSocket(newSocket);

    return () => {
      newSocket.close();
    };
  }, []);

  useEffect(() => {
    fetchTasks();
    fetchReminders();
    fetchReports();
    // Check system preference for dark mode
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    setDarkMode(prefersDark);
  }, []);

  useEffect(() => {
    document.body.className = darkMode ? 'dark-mode' : '';
  }, [darkMode]);

  const fetchTasks = async () => {
    try {
      const response = await fetch('http://127.0.0.1:5000/tasks');
      const data = await response.json();
      setTasks(data);
    } catch (error) {
      console.error('Error fetching tasks:', error);
    }
  };

  const fetchReminders = async () => {
    try {
      const response = await fetch('http://127.0.0.1:5000/tasks/reminders');
      const data = await response.json();
      setReminders(data);
    } catch (error) {
      console.error('Error fetching reminders:', error);
    }
  };

  const fetchReports = async () => {
    try {
      const response = await fetch('http://127.0.0.1:5000/reports');
      const data = await response.json();
      setReports(data);
    } catch (error) {
      console.error('Error fetching reports:', error);
    }
  };

  const handleCreateTask = async (e) => {
    e.preventDefault();
    setFormError('');

    if (!newTask.name.trim()) {
      setFormError('Task name is required');
      return;
    }
    if (!newTask.description.trim()) {
      setFormError('Task description is required');
      return;
    }
    if (!newTask.due_date) {
      setFormError('Due date is required');
      return;
    }

    const selectedDate = new Date(newTask.due_date);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    
    if (selectedDate < today) {
      setFormError('Due date cannot be in the past');
      return;
    }

    try {
      const response = await fetch('http://127.0.0.1:5000/tasks', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(newTask),
      });
      if (response.ok) {
        setNewTask({ name: '', description: '', due_date: '' });
        setFormError('');
        fetchTasks();
      }
    } catch (error) {
      console.error('Error creating task:', error);
      setFormError('Error creating task');
    }
  };

  const handleStatusUpdate = async (taskId, newStatus) => {
    try {
      await fetch(`http://127.0.0.1:5000/tasks/${taskId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ status: newStatus }),
      });
      fetchTasks();
    } catch (error) {
      console.error('Error updating task:', error);
    }
  };

  return (
    <div className={`App ${darkMode ? 'dark-mode' : ''}`}>
      <header className="App-header">
        <div className="header-content">
          <div className="logo">
            <FaRobot className="robot-icon" />
            <h1>AI Task Management</h1>
          </div>
          <div className="header-controls">
            {lastUpdate && (
              <div className="last-update">
                Last updated: {new Date(lastUpdate).toLocaleString()}
              </div>
            )}
            <button 
              className="theme-toggle"
              onClick={() => setDarkMode(!darkMode)}
            >
              {darkMode ? <FaSun /> : <FaMoon />}
            </button>
          </div>
        </div>
      </header>

      <div className="container">
        {/* Reports Section */}
        {reports && (
          <div className="reports-section">
            <h2><FaClipboardList /> Analytics Dashboard</h2>
            <div className="reports-grid">
              <div className="report-item">
                <h3>Total Tasks</h3>
                <p className="report-number">{reports.total_tasks}</p>
              </div>
              <div className="report-item">
                <h3>Completed</h3>
                <p className="report-number">{reports.completed_tasks}</p>
              </div>
              <div className="report-item">
                <h3>In Progress</h3>
                <p className="report-number">{reports.in_progress_tasks}</p>
              </div>
              <div className="report-item">
                <h3>Pending</h3>
                <p className="report-number">{reports.pending_tasks}</p>
              </div>
            </div>
          </div>
        )}

        {/* Create Task Section */}
        <div className="create-task-section">
          <h2><FaTasks /> Create New Task</h2>
          <form onSubmit={handleCreateTask}>
            {formError && <div className="error-message">{formError}</div>}
            <input
              type="text"
              placeholder="Task Name *"
              value={newTask.name}
              onChange={(e) => setNewTask({ ...newTask, name: e.target.value })}
              required
              className={!newTask.name.trim() ? 'input-error' : ''}
            />
            <textarea
              placeholder="Task Description *"
              value={newTask.description}
              onChange={(e) => setNewTask({ ...newTask, description: e.target.value })}
              required
              className={!newTask.description.trim() ? 'input-error' : ''}
            />
            <input
              type="date"
              value={newTask.due_date}
              onChange={(e) => setNewTask({ ...newTask, due_date: e.target.value })}
              required
              className={!newTask.due_date ? 'input-error' : ''}
            />
            <button type="submit" className="glow-button">Create Task</button>
          </form>
        </div>

        {/* Reminders Section */}
        {reminders.length > 0 && (
          <div className="reminders-section">
            <h2><FaClock /> Upcoming Deadlines</h2>
            <div className="reminders-list">
              {reminders.map((reminder) => (
                <div key={reminder.id} className="reminder-item">
                  <p className="reminder-name">{reminder.name}</p>
                  <p className="reminder-date">Due: {reminder.due_date}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Tasks Section */}
        <div className="tasks-section">
          <h2><FaTasks /> All Tasks</h2>
          <div className="tasks-grid">
            {tasks.map((task) => (
              <div key={task.id} className="task-card">
                <h3>{task.name}</h3>
                <p>{task.description}</p>
                <p>Due Date: {task.due_date || 'Not set'}</p>
                <p className={`status-badge ${task.status.toLowerCase()}`}>
                  {task.status}
                </p>
                <div className="task-actions">
                  <button onClick={() => handleStatusUpdate(task.id, 'In Progress')}>
                    Start Task
                  </button>
                  <button onClick={() => handleStatusUpdate(task.id, 'Completed')}>
                    Complete
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
