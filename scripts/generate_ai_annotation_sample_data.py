"""
Generate sample data for AI annotation workflow testing.

This script creates sample learning jobs, batch annotation jobs, and iteration records
for testing the AI annotation workflow.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
from uuid import uuid4

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from src.models.ai_annotation import AILearningJobModel, BatchAnnotationJobModel, IterationRecordModel
from src.database.base import Base


async def generate_sample_data():
    """Generate sample data for AI annotation workflow."""
    
    # Create async engine
    engine = create_async_engine(
        "sqlite+aiosqlite:///./superinsight.db",
        echo=True
    )
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        print("Generating AI annotation sample data...")
        
        # Generate 3 learning jobs
        learning_jobs = []
        for i in range(1, 4):
            job = AILearningJobModel(
                id=f"learn_job_{i}",
                project_id="default",
                status="completed" if i < 3 else "running",
                sample_count=10 + i * 5,
                patterns_identified=5 + i * 2,
                average_confidence=0.75 + i * 0.05,
                recommended_method="rule_based" if i % 2 == 0 else "ml_based",
                progress_percentage=100.0 if i < 3 else 65.0,
                created_at=datetime.utcnow() - timedelta(days=10 - i),
                updated_at=datetime.utcnow() - timedelta(days=10 - i),
                completed_at=datetime.utcnow() - timedelta(days=10 - i) if i < 3 else None,
            )
            learning_jobs.append(job)
            session.add(job)
        
        print(f"Created {len(learning_jobs)} learning jobs")
        
        # Generate 5 batch annotation jobs
        batch_jobs = []
        for i in range(1, 6):
            learning_job_id = f"learn_job_{min(i, 3)}"
            status = "completed" if i < 4 else ("running" if i == 4 else "pending")
            
            job = BatchAnnotationJobModel(
                id=f"batch_job_{i}",
                project_id="default",
                learning_job_id=learning_job_id,
                target_dataset_id=f"dataset_{i}",
                annotation_type="entity" if i % 2 == 0 else "relation",
                confidence_threshold=0.7 + i * 0.02,
                status=status,
                total_count=1000 + i * 200,
                annotated_count=(1000 + i * 200) if status == "completed" else (500 if status == "running" else 0),
                needs_review_count=50 + i * 10 if status != "pending" else 0,
                average_confidence=0.80 + i * 0.02 if status != "pending" else 0.0,
                created_at=datetime.utcnow() - timedelta(days=8 - i),
                updated_at=datetime.utcnow() - timedelta(hours=i),
                completed_at=datetime.utcnow() - timedelta(days=8 - i) if status == "completed" else None,
            )
            batch_jobs.append(job)
            session.add(job)
        
        print(f"Created {len(batch_jobs)} batch annotation jobs")
        
        # Generate 3 iteration records
        iterations = []
        for i in range(1, 4):
            record = IterationRecordModel(
                id=f"iter_{i}",
                project_id="default",
                iteration_number=i,
                sample_count=10 + i * 5,
                annotation_count=100 + i * 50,
                accuracy=0.75 + i * 0.05,
                recall=0.70 + i * 0.05,
                f1_score=0.72 + i * 0.05,
                consistency=0.80 + i * 0.03,
                duration_seconds=300.0 + i * 50,
                learning_job_id=f"learn_job_{i}",
                batch_job_id=f"batch_job_{i}",
                created_at=datetime.utcnow() - timedelta(days=7 - i),
            )
            iterations.append(record)
            session.add(record)
        
        print(f"Created {len(iterations)} iteration records")
        
        # Commit all changes
        await session.commit()
        
        print("\n✅ Sample data generation completed!")
        print(f"   - {len(learning_jobs)} AI learning jobs")
        print(f"   - {len(batch_jobs)} batch annotation jobs")
        print(f"   - {len(iterations)} iteration records")
        print("\nYou can now test the AI annotation workflow with this data.")


if __name__ == "__main__":
    asyncio.run(generate_sample_data())
