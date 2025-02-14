from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from flask_cors import CORS
from flasgger import Swagger, swag_from
from flask_socketio import SocketIO
import json
from threading import Thread
import time


app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Swagger configuration
swagger_config = {
    "headers": [],
    "specs": [
        {
            "endpoint": 'apispec',
            "route": '/apispec.json',
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/docs"
}

swagger = Swagger(app, config=swagger_config)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tasks.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Models
class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='Pending')  # e.g., Pending, In Progress, Completed
    due_date = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False)
    assignee = db.Column(db.String(100), nullable=False)
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow)
    
class ActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False)
    action = db.Column(db.String(200), nullable=False)  # e.g., "Task Created", "Status Updated"
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# Utility functions
def log_activity(task_id, action):
    log = ActivityLog(task_id=task_id, action=action)
    db.session.add(log)
    db.session.commit()
    print(f"\nActivity logged - Task ID: {task_id}, Action: {action}")

# Routes

## 1. Task Creation and Editing
@app.route('/tasks', methods=['POST'])
@swag_from({
    'tags': ['Tasks'],
    'summary': 'Create a new task',
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'name': {'type': 'string'},
                    'description': {'type': 'string'},
                    'due_date': {'type': 'string', 'format': 'date'}
                },
                'required': ['name']
            }
        }
    ],
    'responses': {
        201: {
            'description': 'Task created successfully'
        }
    }
})
def create_task():
    data = request.json
    print(f"\nCreating new task: {data['name']}")
    
    new_task = Task(
        name=data['name'],
        description=data.get('description'),
        due_date=datetime.strptime(data['due_date'], '%Y-%m-%d') if 'due_date' in data else None
    )
    db.session.add(new_task)
    db.session.commit()
    log_activity(new_task.id, "Task Created")
    
    print(f"Task created successfully with ID: {new_task.id}")
    return jsonify({"message": "Task created successfully", "task": new_task.id}), 201

@app.route('/tasks/<int:task_id>', methods=['PUT'])
@swag_from({
    'tags': ['Tasks'],
    'summary': 'Update an existing task',
    'parameters': [
        {
            'name': 'task_id',
            'in': 'path',
            'type': 'integer',
            'required': True
        },
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'name': {'type': 'string'},
                    'description': {'type': 'string'},
                    'status': {'type': 'string', 'enum': ['Pending', 'In Progress', 'Completed']},
                    'due_date': {'type': 'string', 'format': 'date'}
                }
            }
        }
    ],
    'responses': {
        200: {
            'description': 'Task updated successfully'
        },
        404: {
            'description': 'Task not found'
        }
    }
})
def edit_task(task_id):
    data = request.json
    task = Task.query.get_or_404(task_id)
    task.name = data.get('name', task.name)
    task.description = data.get('description', task.description)
    task.status = data.get('status', task.status)
    task.due_date = datetime.strptime(data['due_date'], '%Y-%m-%d') if 'due_date' in data else task.due_date
    db.session.commit()
    log_activity(task_id, "Task Updated")
    return jsonify({"message": "Task updated successfully"})

## 2. Task Assignment
@app.route('/tasks/<int:task_id>/assign', methods=['POST'])
def assign_task(task_id):
    data = request.json
    task = Task.query.get_or_404(task_id)
    assignee = data['assignee']
    assignment = Assignment(task_id=task_id, assignee=assignee)
    db.session.add(assignment)
    db.session.commit()
    log_activity(task_id, f"Task assigned to {assignee}")
    return jsonify({"message": f"Task assigned to {assignee}"})

## 3. Progress Tracking
@app.route('/tasks', methods=['GET'])
@swag_from({
    'tags': ['Tasks'],
    'summary': 'Get all tasks',
    'responses': {
        200: {
            'description': 'List of all tasks',
            'schema': {
                'type': 'array',
                'items': {
                    'type': 'object',
                    'properties': {
                        'id': {'type': 'integer'},
                        'name': {'type': 'string'},
                        'description': {'type': 'string'},
                        'status': {'type': 'string'},
                        'due_date': {'type': 'string', 'format': 'date'},
                        'created_at': {'type': 'string', 'format': 'datetime'},
                        'updated_at': {'type': 'string', 'format': 'datetime'}
                    }
                }
            }
        }
    }
})
def get_tasks():
    print("\nFetching all tasks...")
    tasks = Task.query.all()
    print(f"Found {len(tasks)} tasks")
    return jsonify([{
        "id": task.id,
        "name": task.name,
        "description": task.description,
        "status": task.status,
        "due_date": task.due_date.strftime('%Y-%m-%d') if task.due_date else None,
        "created_at": task.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        "updated_at": task.updated_at.strftime('%Y-%m-%d %H:%M:%S') if task.updated_at else None
    } for task in tasks])

## 4. Activity Tracking
@app.route('/tasks/<int:task_id>/logs', methods=['GET'])
def get_logs(task_id):
    logs = ActivityLog.query.filter_by(task_id=task_id).all()
    return jsonify([{
        "id": log.id,
        "action": log.action,
        "timestamp": log.timestamp.strftime('%Y-%m-%d %H:%M:%S')
    } for log in logs])

## 5. Data Reporting and Analysis
@app.route('/reports', methods=['GET'])
def get_report():
    total_tasks = Task.query.count()
    completed_tasks = Task.query.filter_by(status='Completed').count()
    pending_tasks = Task.query.filter_by(status='Pending').count()
    in_progress_tasks = Task.query.filter_by(status='In Progress').count()
    return jsonify({
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "pending_tasks": pending_tasks,
        "in_progress_tasks": in_progress_tasks
    })

## 6. Notifications and Reminders
@app.route('/tasks/reminders', methods=['GET'])
def get_reminders():
    upcoming_tasks = Task.query.filter(Task.due_date != None, Task.due_date <= datetime.utcnow() + timedelta(days=1)).all()
    return jsonify([{
        "id": task.id,
        "name": task.name,
        "due_date": task.due_date.strftime('%Y-%m-%d')
    } for task in upcoming_tasks])

def get_tasks_status():
    """獲取任務狀態統計"""
    total_tasks = Task.query.count()
    completed_tasks = Task.query.filter_by(status='Completed').count()
    pending_tasks = Task.query.filter_by(status='Pending').count()
    in_progress_tasks = Task.query.filter_by(status='In Progress').count()
    
    return {
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "pending_tasks": pending_tasks,
        "in_progress_tasks": in_progress_tasks,
        "timestamp": datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    }

def background_task():
    """背景任務：每10秒發送一次狀態更新"""
    print("\nStarting background task for WebSocket updates...")
    while True:
        with app.app_context():
            status = get_tasks_status()
            print(f"\nEmitting task status update: {status}")
            socketio.emit('status_update', status)
        time.sleep(10)

@socketio.on('connect')
def handle_connect():
    print('\nClient connected to WebSocket')
    # 立即發送一次當前狀態
    with app.app_context():
        socketio.emit('status_update', get_tasks_status())

@socketio.on('disconnect')
def handle_disconnect():
    print('\nClient disconnected from WebSocket')

# Initialize the database
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    print("\n=== Flask Task Management API ===")
    print("Server is starting...")
    print("\nAvailable endpoints:")
    print("* Swagger UI:     http://localhost:5000/docs")
    print("* Tasks List:     http://localhost:5000/tasks")
    print("* Task Reports:   http://localhost:5000/reports")
    print("* Task Reminders: http://localhost:5000/tasks/reminders")
    print("* WebSocket:      ws://localhost:5000")
    print("\nPress CTRL+C to stop the server")
    print("================================\n")
    
    try:
        # 啟動背景任務
        background_thread = Thread(target=background_task)
        background_thread.daemon = True
        background_thread.start()
        
        # 使用 socketio 替代 app.run()
        socketio.run(app, debug=True)
    except Exception as e:
        print(f"\nError starting server: {str(e)}")
