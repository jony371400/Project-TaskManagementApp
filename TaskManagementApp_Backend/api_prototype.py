from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta

app = Flask(__name__)
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

# Routes

## 1. Task Creation and Editing
@app.route('/tasks', methods=['POST'])
def create_task():
    data = request.json
    new_task = Task(
        name=data['name'],
        description=data.get('description'),
        due_date=datetime.strptime(data['due_date'], '%Y-%m-%d') if 'due_date' in data else None
    )
    db.session.add(new_task)
    db.session.commit()
    log_activity(new_task.id, "Task Created")
    return jsonify({"message": "Task created successfully", "task": new_task.id}), 201

@app.route('/tasks/<int:task_id>', methods=['PUT'])
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
def get_tasks():
    tasks = Task.query.all()
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

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # 確保資料庫在應用啟動時初始化
    app.run(debug=True)

