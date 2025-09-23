"""Example of using async BigQuery repository with global client"""
import asyncio
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

from ..repositories.async_bigquery_detection_repository import AsyncDetectionRepositoryFactory
from ..application.async_services import get_async_cloning_service


async def example_async_repository_usage():
    """Example of using async BigQuery repository directly"""
    
    # Create async repository using global BigQuery client
    repository = AsyncDetectionRepositoryFactory.create_async_bigquery_repository()
    
    try:
        # Test connection
        is_connected = await repository.test_connection()
        print(f"BigQuery connection: {'✅ Connected' if is_connected else '❌ Failed'}")
        
        if is_connected:
            # Query detections for a specific plate
            plate = "ABC1234"
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)
            
            print(f"Querying detections for plate {plate} from {start_date} to {end_date}")
            
            detections = await repository.find_by_plate_and_period(plate, start_date, end_date)
            print(f"Found {len(detections)} detections")
            
            # Print first few detections
            for i, detection in enumerate(detections[:3]):
                print(f"Detection {i+1}: {detection.plate} at {detection.datetime} - {detection.location}")
    
    finally:
        # Always close the repository
        await repository.close()


async def example_async_service_usage():
    """Example of using async cloning service"""
    
    # Create async service instance
    service = get_async_cloning_service()
    
    try:
        # Generate cloning report
        plate = "ABC1234"
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        print(f"Generating async cloning report for plate {plate}")
        
        report = await service.execute(
            plate=plate,
            date_start=start_date,
            date_end=end_date,
            output_dir="reports"
        )
        
        print(f"Report generated: {report.report_path}")
        print(f"Total detections: {report.total_detections}")
        print(f"Suspicious pairs: {len(report.suspicious_pairs)}")
    
    finally:
        # Cleanup service
        await service.close()


async def example_with_custom_executor():
    """Example using custom thread pool executor"""
    
    # Create custom executor with more workers
    executor = ThreadPoolExecutor(max_workers=8)
    
    try:
        # Create repository with custom executor
        repository = AsyncDetectionRepositoryFactory.create_async_bigquery_repository(executor)
        
        # Use repository...
        is_connected = await repository.test_connection()
        print(f"Custom executor connection: {'✅ Connected' if is_connected else '❌ Failed'}")
        
        await repository.close()
    
    finally:
        # Shutdown custom executor
        executor.shutdown(wait=True)


async def main():
    """Run all examples"""
    print("🚀 Running async BigQuery repository examples...\n")
    
    print("1. Direct repository usage:")
    await example_async_repository_usage()
    print()
    
    print("2. Service usage:")
    await example_async_service_usage()
    print()
    
    print("3. Custom executor usage:")
    await example_with_custom_executor()
    print()
    
    print("✅ All examples completed!")


if __name__ == "__main__":
    # Run the examples
    asyncio.run(main())
