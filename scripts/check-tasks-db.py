#!/usr/bin/env python3
"""
Check tasks in database and create sample task if needed
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.connection import db_manager
from src.database.models import TaskModel, TaskStatus, TaskPriority, AnnotationType
from uuid import uuid4
from datetime import datetime

def main():
    # Initialize database
    db_manager.initialize()
    
    # Get session
    db = db_manager.get_session()
    
    try:
        # Count tasks
        count = db.query(TaskModel).count()
        print(f'Total tasks in database: {count}')
        
        if count > 0:
            # Show first 5 tasks
            tasks = db.query(TaskModel).limit(5).all()
            print('\nFirst 5 tasks:')
            for task in tasks:
                print(f'  - ID: {task.id}')
                print(f'    Name: {task.name}')
                print(f'    Status: {task.status}')
                print(f'    Label Studio Project: {task.label_studio_project_id}')
                print()
        else:
            print('\nNo tasks found in database.')
            print('Creating sample task...')
            
            # Create sample task
            sample_task = TaskModel(
                id=uuid4(),
                name='Sample Annotation Task',
                description='This is a sample task for testing Label Studio integration',
                status=TaskStatus.PENDING,
                priority=TaskPriority.MEDIUM,
                annotation_type=AnnotationType.TEXT_CLASSIFICATION,
                total_items=100,
                completed_items=0,
                progress=0,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                label_studio_project_id=None
            )
            
            db.add(sample_task)
            db.commit()
            
            print(f'\n✓ Created sample task:')
            print(f'  ID: {sample_task.id}')
            print(f'  Name: {sample_task.name}')
            print(f'  Status: {sample_task.status}')
            print(f'\nYou can now access this task at:')
            print(f'  http://localhost:5173/tasks/{sample_task.id}')
            
    finally:
        db.close()

if __name__ == '__main__':
    main()
