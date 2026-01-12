#!/usr/bin/env python3
"""
Demonstration of Comprehensive Audit System for SuperInsight Platform.

This script demonstrates the complete audit recording of all user operations
including middleware-based logging, decorator-based logging, and manual logging.

Usage:
    python demo_comprehensive_audit_system.py
"""

import asyncio
import json
from datetime import datetime, timedelta
from uuid import uuid4
from fastapi import FastAPI, Request, Depends
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

# Import audit system components
from src.security.comprehensive_audit_integration import ComprehensiveAuditIntegration
from src.security.audit_middleware import ComprehensiveAuditMiddleware
from src.security.audit_decorators import audit_all, audit_sensitive, audit_data
from src.security.audit_service import EnhancedAuditService
from src.security.models import AuditAction, UserModel, UserRole
from src.database.connection import get_db_session


class AuditSystemDemo:
    """Demonstration of comprehensive audit system functionality."""
    
    def __init__(self):
        self.audit_integration = ComprehensiveAuditIntegration()
        self.audit_service = EnhancedAuditService()
        
    def create_demo_app(self) -> FastAPI:
        """Create a demo FastAPI application with comprehensive audit logging."""
        
        app = FastAPI(title="Audit System Demo", version="1.0.0")
        
        # Integrate comprehensive audit system
        self.audit_integration.integrate_with_fastapi(app)
        
        # Demo endpoints with different audit decorators
        
        @app.get("/")
        async def root():
            """Root endpoint - automatically audited by middleware."""
            return {"message": "Audit System Demo", "timestamp": datetime.utcnow().isoformat()}
        
        @app.post("/api/users")
        @audit_all(resource_type="user", action=AuditAction.CREATE)
        async def create_user(
            user_data: dict,
            request: Request,
            current_user: dict = None,
            db: Session = Depends(get_db_session)
        ):
            """Create user endpoint with comprehensive audit logging."""
            return {
                "message": "User created successfully",
                "user_id": str(uuid4()),
                "audit": "Logged via @audit_all decorator"
            }
        
        @app.put("/api/users/{user_id}/role")
        @audit_sensitive(
            resource_type="user_role",
            action=AuditAction.UPDATE,
            risk_level="high"
        )
        async def update_user_role(
            user_id: str,
            role_data: dict,
            request: Request,
            current_user: dict = None,
            db: Session = Depends(get_db_session)
        ):
            """Update user role - sensitive operation with enhanced audit."""
            return {
                "message": "User role updated",
                "user_id": user_id,
                "audit": "Logged via @audit_sensitive decorator"
            }
        
        @app.get("/api/data/export")
        @audit_data(
            data_type="user_data",
            access_level="read",
            track_volume=True
        )
        async def export_user_data(
            request: Request,
            current_user: dict = None,
            db: Session = Depends(get_db_session)
        ):
            """Export user data with data access audit logging."""
            return {
                "message": "Data exported",
                "record_count": 1000,
                "audit": "Logged via @audit_data decorator"
            }
        
        @app.get("/api/audit/coverage")
        async def get_audit_coverage():
            """Get audit coverage report."""
            return await self.audit_integration.get_audit_coverage_report()
        
        @app.get("/api/audit/stats")
        async def get_audit_stats():
            """Get real-time audit statistics."""
            return await self.audit_integration.get_real_time_audit_stats()
        
        return app
    
    async def demonstrate_system_logging(self):
        """Demonstrate system-level audit logging."""
        
        print("\n=== System-Level Audit Logging Demo ===")
        
        # Log various system operations
        operations = [
            {
                "operation": "database_backup_started",
                "resource_type": "database",
                "details": {"backup_type": "full", "size_gb": 50}
            },
            {
                "operation": "user_session_cleanup",
                "resource_type": "session",
                "details": {"expired_sessions": 25, "cleanup_duration": "2.5s"}
            },
            {
                "operation": "security_scan_completed",
                "resource_type": "security",
                "details": {"vulnerabilities_found": 0, "scan_duration": "45s"}
            }
        ]
        
        for op in operations:
            await self.audit_integration.log_system_operation(
                operation=op["operation"],
                resource_type=op["resource_type"],
                details=op["details"],
                tenant_id="demo_tenant"
            )
            print(f"✓ Logged system operation: {op['operation']}")
    
    async def demonstrate_batch_logging(self):
        """Demonstrate batch audit logging."""
        
        print("\n=== Batch Audit Logging Demo ===")
        
        # Create batch operations
        batch_operations = []
        for i in range(10):
            batch_operations.append({
                "user_id": f"user_{i}",
                "action": "create" if i % 2 == 0 else "update",
                "resource_type": "document",
                "resource_id": f"doc_{i}",
                "details": {
                    "document_name": f"Document {i}",
                    "size_kb": 100 + i * 10,
                    "timestamp": datetime.utcnow().isoformat()
                }
            })
        
        # Log batch operations
        await self.audit_integration.log_batch_operations(
            operations=batch_operations,
            tenant_id="demo_tenant"
        )
        
        print(f"✓ Logged {len(batch_operations)} operations in batch")
    
    async def demonstrate_coverage_analysis(self):
        """Demonstrate audit coverage analysis."""
        
        print("\n=== Audit Coverage Analysis Demo ===")
        
        # Register some demo endpoints for coverage tracking
        coverage_tracker = self.audit_integration.coverage_tracker
        
        demo_endpoints = [
            ("/api/users", True),
            ("/api/documents", True),
            ("/api/billing", False),  # Not audited
            ("/api/reports", True),
            ("/api/settings", False),  # Not audited
            ("/api/export", True)
        ]
        
        for endpoint, has_audit in demo_endpoints:
            await coverage_tracker.register_endpoint(endpoint, has_audit)
        
        # Generate coverage report
        coverage_report = await self.audit_integration.get_audit_coverage_report()
        
        print("Coverage Report:")
        print(f"  Total Endpoints: {coverage_report['total_endpoints']}")
        print(f"  Audited Endpoints: {coverage_report['audited_endpoints']}")
        print(f"  Coverage Percentage: {coverage_report['coverage_percentage']:.1f}%")
        
        if coverage_report['unaudited_endpoints']:
            print("  Unaudited Endpoints:")
            for endpoint in coverage_report['unaudited_endpoints']:
                print(f"    - {endpoint}")
        
        print("  Recommendations:")
        for rec in coverage_report['recommendations']:
            print(f"    - {rec}")
    
    async def demonstrate_completeness_verification(self):
        """Demonstrate audit completeness verification."""
        
        print("\n=== Audit Completeness Verification Demo ===")
        
        # Verify audit completeness for demo tenant
        completeness_report = await self.audit_integration.verify_audit_completeness(
            tenant_id="demo_tenant",
            time_range=timedelta(hours=1)
        )
        
        if "error" not in completeness_report:
            print("Completeness Report:")
            print(f"  Tenant ID: {completeness_report['tenant_id']}")
            print(f"  Time Range: {completeness_report['time_range']['duration_hours']:.1f} hours")
            print(f"  Completeness Score: {completeness_report['completeness_score']:.1f}/100")
            
            print("  Recommendations:")
            for rec in completeness_report['recommendations']:
                print(f"    - {rec}")
        else:
            print(f"  Verification failed: {completeness_report['error']}")
    
    def demonstrate_api_endpoints(self):
        """Demonstrate API endpoints with audit logging."""
        
        print("\n=== API Endpoints Audit Demo ===")
        
        # Create demo app
        app = self.create_demo_app()
        client = TestClient(app)
        
        # Test various endpoints
        test_requests = [
            ("GET", "/", None),
            ("POST", "/api/users", {"username": "testuser", "email": "test@example.com"}),
            ("PUT", "/api/users/123/role", {"role": "admin"}),
            ("GET", "/api/data/export", None),
            ("GET", "/api/audit/coverage", None),
            ("GET", "/api/audit/stats", None)
        ]
        
        print("Testing API endpoints (audit logging via middleware and decorators):")
        
        for method, url, data in test_requests:
            try:
                if method == "GET":
                    response = client.get(url)
                elif method == "POST":
                    response = client.post(url, json=data)
                elif method == "PUT":
                    response = client.put(url, json=data)
                
                print(f"  ✓ {method} {url} -> {response.status_code}")
                
                if response.status_code == 200 and url in ["/api/audit/coverage", "/api/audit/stats"]:
                    result = response.json()
                    if url == "/api/audit/coverage":
                        print(f"    Coverage: {result.get('coverage_percentage', 0):.1f}%")
                    elif url == "/api/audit/stats":
                        print(f"    Events: {result.get('total_events', 0)}")
                
            except Exception as e:
                print(f"  ✗ {method} {url} -> Error: {e}")
    
    def demonstrate_audit_decorators(self):
        """Demonstrate different audit decorators."""
        
        print("\n=== Audit Decorators Demo ===")
        
        # Show decorator usage examples
        decorator_examples = [
            {
                "name": "@audit_all",
                "description": "Comprehensive audit logging for all operations",
                "usage": "@audit_all(resource_type='user', action=AuditAction.CREATE)"
            },
            {
                "name": "@audit_sensitive", 
                "description": "Enhanced audit logging for sensitive operations",
                "usage": "@audit_sensitive(resource_type='security', action=AuditAction.UPDATE, risk_level='high')"
            },
            {
                "name": "@audit_data",
                "description": "Specialized audit logging for data access operations", 
                "usage": "@audit_data(data_type='user_data', access_level='read', track_volume=True)"
            }
        ]
        
        print("Available Audit Decorators:")
        for example in decorator_examples:
            print(f"  {example['name']}")
            print(f"    Description: {example['description']}")
            print(f"    Usage: {example['usage']}")
            print()
    
    def demonstrate_middleware_features(self):
        """Demonstrate middleware features."""
        
        print("\n=== Audit Middleware Features Demo ===")
        
        middleware = ComprehensiveAuditMiddleware(None)
        
        print("Middleware Features:")
        print(f"  Excluded Paths: {list(middleware.excluded_paths)}")
        print(f"  Sensitive Endpoints: {list(middleware.sensitive_endpoints)}")
        print(f"  HTTP Method Mapping: {dict(middleware.method_to_action)}")
        
        # Demonstrate resource type detection
        print("\n  Resource Type Detection Examples:")
        test_paths = [
            "/api/users/123",
            "/api/security/settings", 
            "/api/audit/logs",
            "/api/billing/invoices",
            "/api/quality/reports"
        ]
        
        for path in test_paths:
            resource_type = middleware._extract_resource_type(path)
            print(f"    {path} -> {resource_type}")
        
        # Demonstrate sensitive data detection
        print("\n  Sensitive Data Detection Examples:")
        test_data = [
            b'{"username": "user", "password": "secret"}',
            b'{"email": "user@example.com", "phone": "555-1234"}',
            b'{"name": "John", "age": 30}',
            b'{"status": "active", "count": 100}'
        ]
        
        for data in test_data:
            is_sensitive = middleware._detect_sensitive_data(data)
            data_str = data.decode()[:50] + "..." if len(data) > 50 else data.decode()
            print(f"    {data_str} -> {'Sensitive' if is_sensitive else 'Not Sensitive'}")
    
    async def run_complete_demo(self):
        """Run the complete audit system demonstration."""
        
        print("=" * 60)
        print("COMPREHENSIVE AUDIT SYSTEM DEMONSTRATION")
        print("SuperInsight Platform - Complete User Operation Auditing")
        print("=" * 60)
        
        try:
            # Initialize audit system
            print("\n🚀 Initializing Comprehensive Audit System...")
            await self.audit_integration.initialize_audit_system()
            print("✓ Audit system initialized successfully")
            
            # Demonstrate different audit logging methods
            await self.demonstrate_system_logging()
            await self.demonstrate_batch_logging()
            
            # Demonstrate coverage and completeness analysis
            await self.demonstrate_coverage_analysis()
            await self.demonstrate_completeness_verification()
            
            # Demonstrate API endpoint auditing
            self.demonstrate_api_endpoints()
            
            # Demonstrate decorator and middleware features
            self.demonstrate_audit_decorators()
            self.demonstrate_middleware_features()
            
            print("\n" + "=" * 60)
            print("✅ COMPREHENSIVE AUDIT SYSTEM DEMO COMPLETED")
            print("=" * 60)
            
            print("\nKey Features Demonstrated:")
            print("  ✓ Automatic middleware-based audit logging")
            print("  ✓ Decorator-based endpoint audit logging")
            print("  ✓ Manual system operation logging")
            print("  ✓ Batch operation logging")
            print("  ✓ Audit coverage analysis")
            print("  ✓ Audit completeness verification")
            print("  ✓ Real-time audit monitoring")
            print("  ✓ Sensitive data detection")
            print("  ✓ Risk assessment and threat detection")
            print("  ✓ Multi-tenant audit isolation")
            
            print("\nAudit System Benefits:")
            print("  • Complete audit trail of ALL user operations")
            print("  • Enterprise-level security and compliance")
            print("  • Real-time threat detection and monitoring")
            print("  • Comprehensive coverage analysis")
            print("  • Performance-optimized batch processing")
            print("  • Multi-level audit integration")
            
        except Exception as e:
            print(f"\n❌ Demo failed with error: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            # Shutdown audit system
            print("\n🔄 Shutting down audit system...")
            await self.audit_integration.shutdown_audit_system()
            print("✓ Audit system shutdown completed")


async def main():
    """Main demo function."""
    
    demo = AuditSystemDemo()
    await demo.run_complete_demo()


if __name__ == "__main__":
    # Run the demonstration
    asyncio.run(main())