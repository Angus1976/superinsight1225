"""
Real-time Sync System Demo.

Demonstrates how to set up and use the real-time synchronization system
with CDC, logical replication, and async task processing.
"""

import asyncio
import logging
from datetime import datetime

from src.sync.realtime import RealTimeSyncManager, SyncConfiguration, SyncMode
from src.sync.cdc.debezium_connector import DebeziumConfig, DebeziumConnectorType, DebeziumMode
from src.sync.cdc.pglogical_replication import PgLogicalConfig, ReplicationMode
from src.sync.async_queue.task_manager import TaskBackend

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def demo_realtime_sync():
    """Demonstrate real-time sync system."""
    
    # Create Debezium configuration for MySQL
    debezium_config = DebeziumConfig(
        name="mysql_cdc",
        connector_type=DebeziumConnectorType.MYSQL,
        mode=DebeziumMode.KAFKA_CONNECT,
        host="localhost",
        port=3306,
        database="test_db",
        username="debezium",
        password="password",
        tables=["users", "orders", "products"],
        kafka_connect_url="http://localhost:8083",
        kafka_bootstrap_servers="localhost:9092",
        topic_prefix="mysql_server"
    )
    
    # Create pglogical configuration for PostgreSQL
    pglogical_config = PgLogicalConfig(
        name="postgres_replication",
        replication_mode=ReplicationMode.SUBSCRIBER,
        host="localhost",
        port=5432,
        database="target_db",
        username="postgres",
        password="password",
        tables=["users", "orders", "products"],
        provider_dsn="postgresql://postgres:password@source-host:5432/source_db"
    )
    
    # Create sync system configuration
    sync_config = SyncConfiguration(
        name="demo_sync_system",
        mode=SyncMode.HYBRID,
        enable_debezium=True,
        debezium_configs=[debezium_config],
        enable_pglogical=True,
        pglogical_configs=[pglogical_config],
        enable_async_tasks=True,
        task_backend=TaskBackend.REDIS_QUEUE,
        redis_url="redis://localhost:6379/0",
        batch_size=500,
        max_concurrent_tasks=5
    )
    
    # Create and initialize sync manager
    sync_manager = RealTimeSyncManager(sync_config)
    
    try:
        logger.info("Initializing real-time sync system...")
        await sync_manager.initialize()
        
        logger.info("Starting real-time sync system...")
        await sync_manager.start()
        
        # Let it run for a while
        logger.info("Real-time sync system is running. Press Ctrl+C to stop.")
        
        # Monitor system status
        for i in range(10):  # Run for 10 iterations
            await asyncio.sleep(30)  # Wait 30 seconds between checks
            
            # Get system status
            status = await sync_manager.get_system_status()
            logger.info(f"System Status - Events: {status['stats']['events_processed']}, "
                       f"Tasks: {status['stats']['tasks_submitted']}")
            
            # Get performance metrics
            metrics = await sync_manager.get_performance_metrics()
            logger.info(f"Performance - Events/sec: {metrics['throughput']['events_per_second']:.2f}, "
                       f"Tasks/sec: {metrics['throughput']['tasks_per_second']:.2f}")
    
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    
    except Exception as e:
        logger.error(f"Error in sync system: {e}")
    
    finally:
        logger.info("Stopping real-time sync system...")
        await sync_manager.stop()
        logger.info("Real-time sync system stopped")


async def demo_simple_redis_queue():
    """Demonstrate simple Redis queue usage."""
    from src.sync.async_queue.redis_queue import create_redis_queue, QueueType
    
    logger.info("Creating Redis queue...")
    queue = create_redis_queue(
        redis_url="redis://localhost:6379/0",
        queue_name="demo_queue",
        queue_type=QueueType.PRIORITY
    )
    
    # Enqueue some messages
    logger.info("Enqueuing messages...")
    for i in range(5):
        msg_id = await queue.enqueue(
            payload={"task": f"demo_task_{i}", "data": f"test_data_{i}"},
            priority=i % 3  # Vary priority
        )
        logger.info(f"Enqueued message {msg_id}")
    
    # Dequeue and process messages
    logger.info("Processing messages...")
    while True:
        message = await queue.dequeue(timeout=5)
        if not message:
            logger.info("No more messages")
            break
        
        logger.info(f"Processing message {message.id}: {message.payload}")
        
        # Simulate processing
        await asyncio.sleep(1)
        
        # Acknowledge message
        await queue.ack(message.id)
        logger.info(f"Acknowledged message {message.id}")
    
    # Get queue stats
    stats = await queue.get_stats()
    logger.info(f"Queue stats: {stats}")


async def demo_task_manager():
    """Demonstrate async task manager."""
    from src.sync.async_queue.task_manager import AsyncTaskManager, TaskType, SyncTaskHandlers
    
    logger.info("Creating task manager...")
    task_manager = AsyncTaskManager(default_backend=TaskBackend.LOCAL)
    
    # Register handlers
    task_manager.register_handler(TaskType.DATA_PULL, SyncTaskHandlers.data_pull_handler)
    task_manager.register_handler(TaskType.BATCH_PROCESS, SyncTaskHandlers.batch_process_handler)
    
    await task_manager.start()
    
    try:
        # Submit some tasks
        logger.info("Submitting tasks...")
        
        task_ids = []
        
        # Submit data pull task
        task_id = await task_manager.submit_task(
            task_type=TaskType.DATA_PULL,
            kwargs={
                "source_config": {"name": "demo_source"},
                "sync_config": {"expected_records": 100, "batch_size": 20}
            }
        )
        task_ids.append(task_id)
        logger.info(f"Submitted data pull task: {task_id}")
        
        # Submit batch process task
        task_id = await task_manager.submit_task(
            task_type=TaskType.BATCH_PROCESS,
            kwargs={
                "items": [{"id": i, "data": f"item_{i}"} for i in range(50)],
                "processor_config": {"batch_size": 10}
            }
        )
        task_ids.append(task_id)
        logger.info(f"Submitted batch process task: {task_id}")
        
        # Monitor task progress
        logger.info("Monitoring task progress...")
        while True:
            all_completed = True
            
            for tid in task_ids:
                status = await task_manager.get_task_status(tid)
                progress = await task_manager.get_task_progress(tid)
                
                if status and status.value in ["PENDING", "STARTED"]:
                    all_completed = False
                    if progress:
                        logger.info(f"Task {tid}: {status.value} - {progress.percentage:.1f}% - {progress.message}")
                elif status:
                    result = await task_manager.get_task_result(tid)
                    if result:
                        logger.info(f"Task {tid}: {status.value} - {result.result}")
            
            if all_completed:
                break
            
            await asyncio.sleep(2)
        
        # Get final stats
        stats = await task_manager.get_task_stats()
        logger.info(f"Task manager stats: {stats}")
    
    finally:
        await task_manager.stop()


async def main():
    """Main demo function."""
    logger.info("=== Real-time Sync System Demo ===")
    
    # Choose which demo to run
    demo_choice = input("Choose demo (1=Full System, 2=Redis Queue, 3=Task Manager): ").strip()
    
    if demo_choice == "1":
        await demo_realtime_sync()
    elif demo_choice == "2":
        await demo_simple_redis_queue()
    elif demo_choice == "3":
        await demo_task_manager()
    else:
        logger.info("Running all demos...")
        
        logger.info("\n--- Redis Queue Demo ---")
        await demo_simple_redis_queue()
        
        logger.info("\n--- Task Manager Demo ---")
        await demo_task_manager()
        
        logger.info("\n--- Full System Demo ---")
        logger.info("Note: Full system demo requires Kafka, Debezium, and PostgreSQL")
        # await demo_realtime_sync()


if __name__ == "__main__":
    asyncio.run(main())