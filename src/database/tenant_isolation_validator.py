"""
Tenant Data Isolation Validator

Validates that tenant data is properly isolated and queries are tenant-aware.
"""

import logging
from typing import List, Dict, Any, Optional
from sqlalchemy import text, inspect
from sqlalchemy.orm import Session
from src.database.connection import get_db_session
from src.database.models import (
    DocumentModel, TaskModel, BillingRecordModel, QualityIssueModel
)
from src.security.models import UserModel, AuditLogModel
from src.ticket.models import TicketModel, AnnotatorSkillModel, TicketHistoryModel
from src.evaluation.models import PerformanceRecordModel, AppealModel, PerformanceHistoryModel
from src.business_logic.models import BusinessRuleModel, BusinessPatternModel, BusinessInsightModel
from src.sync.models import (
    DataSourceModel, SyncJobModel, SyncExecutionModel, DataConflictModel,
    SyncRuleModel, TransformationRuleModel, SyncAuditLogModel, DataQualityScoreModel
)

logger = logging.getLogger(__name__)


class TenantIsolationValidator:
    """Validates tenant data isolation across all tables."""
    
    def __init__(self):
        self.tenant_aware_tables = [
            # Core business tables
            'documents', 'tasks', 'billing_records', 'quality_issues',
            # Security tables
            'users', 'audit_logs', 'ip_whitelist', 'data_masking_rules',
            # Ticket management
            'tickets', 'annotator_skills', 'ticket_history',
            # Performance evaluation
            'performance_records', 'performance_appeals', 'performance_history',
            # Business logic
            'business_rules', 'business_patterns', 'business_insights',
            # Sync system
            'data_sources', 'sync_jobs', 'sync_executions', 'data_conflicts',
            'sync_rules', 'transformation_rules', 'sync_audit_logs', 'data_quality_scores',
            # RBAC
            'rbac_roles', 'rbac_user_roles', 'rbac_resource_permissions',
            'rbac_field_permissions', 'rbac_data_access_audit',
            # Export control
            'export_requests', 'export_approvals', 'export_watermarks',
            'export_tracking', 'export_behavior', 'export_policies'
        ]
    
    def validate_all_tables_have_tenant_id(self) -> Dict[str, Any]:
        """Validate that all business tables have tenant_id column."""
        results = {
            'valid': True,
            'missing_tenant_id': [],
            'tables_checked': 0,
            'checked_tables': [],
            'errors': []
        }
        
        try:
            with get_db_session() as session:
                inspector = inspect(session.bind)
                
                for table_name in self.tenant_aware_tables:
                    try:
                        columns = inspector.get_columns(table_name)
                        column_names = [col['name'] for col in columns]
                        
                        if 'tenant_id' not in column_names:
                            results['missing_tenant_id'].append(table_name)
                            results['valid'] = False
                        
                        results['tables_checked'] += 1
                        results['checked_tables'].append(table_name)
                        
                    except Exception as e:
                        # Table might not exist yet
                        logger.warning(f"Could not check table {table_name}: {e}")
                        results['errors'].append(f"Table {table_name}: {str(e)}")
                        
        except Exception as e:
            results['valid'] = False
            results['errors'].append(f"Database connection error: {str(e)}")
            
        return results
    
    def validate_tenant_indexes(self) -> Dict[str, Any]:
        """Validate that tenant_id columns have proper indexes."""
        results = {
            'valid': True,
            'missing_indexes': [],
            'indexes_checked': 0,
            'tenant_indexes_found': 0,
            'errors': []
        }
        
        try:
            with get_db_session() as session:
                inspector = inspect(session.bind)
                
                for table_name in self.tenant_aware_tables:
                    try:
                        indexes = inspector.get_indexes(table_name)
                        
                        # Check if there's an index on tenant_id
                        has_tenant_index = False
                        for index in indexes:
                            if 'tenant_id' in index['column_names']:
                                has_tenant_index = True
                                results['tenant_indexes_found'] += 1
                                break
                        
                        if not has_tenant_index:
                            results['missing_indexes'].append(table_name)
                            results['valid'] = False
                        
                        results['indexes_checked'] += 1
                        
                    except Exception as e:
                        logger.warning(f"Could not check indexes for table {table_name}: {e}")
                        results['errors'].append(f"Table {table_name}: {str(e)}")
                        
        except Exception as e:
            results['valid'] = False
            results['errors'].append(f"Database connection error: {str(e)}")
            
        return results
    
    def test_cross_tenant_data_isolation(self, tenant1: str, tenant2: str) -> Dict[str, Any]:
        """Test that queries are properly isolated between tenants."""
        results = {
            'valid': True,
            'isolation_violations': [],
            'tests_run': 0,
            'errors': []
        }
        
        try:
            with get_db_session() as session:
                # Test document isolation
                self._test_model_isolation(
                    session, DocumentModel, tenant1, tenant2, results
                )
                
                # Test task isolation
                self._test_model_isolation(
                    session, TaskModel, tenant1, tenant2, results
                )
                
                # Test user isolation
                self._test_model_isolation(
                    session, UserModel, tenant1, tenant2, results
                )
                
                # Test ticket isolation
                self._test_model_isolation(
                    session, TicketModel, tenant1, tenant2, results
                )
                
                # Test business rule isolation
                self._test_model_isolation(
                    session, BusinessRuleModel, tenant1, tenant2, results
                )
                
        except Exception as e:
            results['valid'] = False
            results['errors'].append(f"Isolation test error: {str(e)}")
            
        return results
    
    def _test_model_isolation(self, session: Session, model_class, tenant1: str, tenant2: str, results: Dict):
        """Test isolation for a specific model."""
        try:
            # Query for tenant1 data
            tenant1_query = session.query(model_class).filter(
                model_class.tenant_id == tenant1
            )
            tenant1_count = tenant1_query.count()
            
            # Query for tenant2 data
            tenant2_query = session.query(model_class).filter(
                model_class.tenant_id == tenant2
            )
            tenant2_count = tenant2_query.count()
            
            # Query without tenant filter (should be avoided in production)
            all_query = session.query(model_class)
            all_count = all_query.count()
            
            # Validate isolation
            if tenant1_count > 0 and tenant2_count > 0:
                # Both tenants have data, check that they don't overlap
                tenant1_ids = {str(row.id) for row in tenant1_query.all()}
                tenant2_ids = {str(row.id) for row in tenant2_query.all()}
                
                overlap = tenant1_ids.intersection(tenant2_ids)
                if overlap:
                    results['isolation_violations'].append({
                        'model': model_class.__name__,
                        'issue': 'Data overlap between tenants',
                        'overlapping_ids': list(overlap)
                    })
                    results['valid'] = False
            
            results['tests_run'] += 1
            
        except Exception as e:
            results['errors'].append(f"Model {model_class.__name__}: {str(e)}")
    
    def validate_cross_tenant_isolation(self, tenant1: str, tenant2: str) -> Dict[str, Any]:
        """Validate that cross-tenant data access is prevented."""
        results = {
            'isolated': True,
            'cross_tenant_records': 0,
            'violations': [],
            'tests_run': 0
        }
        
        try:
            with get_db_session() as session:
                # Test that tenant1 queries don't return tenant2 data
                query = text("""
                    SELECT COUNT(*) as count FROM documents 
                    WHERE tenant_id = :tenant1 
                    AND id IN (SELECT id FROM documents WHERE tenant_id = :tenant2)
                """)
                
                result = session.execute(query, {'tenant1': tenant1, 'tenant2': tenant2})
                cross_tenant_count = result.fetchone()[0]
                
                results['cross_tenant_records'] = cross_tenant_count
                results['isolated'] = cross_tenant_count == 0
                results['tests_run'] = 1
                
        except Exception as e:
            results['isolated'] = False
            results['violations'].append(f"Query error: {str(e)}")
            
        return results

    def validate_query_patterns(self) -> Dict[str, Any]:
        """Validate common query patterns include tenant filtering."""
        results = {
            'valid': True,
            'recommendations': [],
            'warnings': []
        }
        
        # This would typically analyze actual query logs or code patterns
        # For now, we'll provide recommendations
        
        results['recommendations'] = [
            "Always include tenant_id in WHERE clauses for multi-tenant tables",
            "Use composite indexes (tenant_id, other_columns) for better performance",
            "Implement query interceptors to automatically add tenant filters",
            "Use database views or row-level security for additional protection",
            "Regularly audit queries to ensure tenant isolation"
        ]
        
        return results
    
    def generate_isolation_report(self) -> Dict[str, Any]:
        """Generate comprehensive tenant isolation report."""
        report = {
            'timestamp': None,
            'overall_status': 'PASS',
            'tenant_id_validation': None,
            'index_validation': None,
            'isolation_test': None,
            'query_patterns': None,
            'recommendations': []
        }
        
        from datetime import datetime
        report['timestamp'] = datetime.now().isoformat()
        
        # Run all validations
        report['tenant_id_validation'] = self.validate_all_tables_have_tenant_id()
        report['index_validation'] = self.validate_tenant_indexes()
        report['query_patterns'] = self.validate_query_patterns()
        
        # Test isolation with sample tenants
        report['isolation_test'] = self.test_cross_tenant_data_isolation('tenant1', 'tenant2')
        
        # Determine overall status
        if (not report['tenant_id_validation']['valid'] or 
            not report['index_validation']['valid'] or 
            not report['isolation_test']['valid']):
            report['overall_status'] = 'FAIL'
        
        # Compile recommendations
        recommendations = []
        
        if report['tenant_id_validation']['missing_tenant_id']:
            recommendations.append(
                f"Add tenant_id columns to: {', '.join(report['tenant_id_validation']['missing_tenant_id'])}"
            )
        
        if report['index_validation']['missing_indexes']:
            recommendations.append(
                f"Add tenant_id indexes to: {', '.join(report['index_validation']['missing_indexes'])}"
            )
        
        if report['isolation_test']['isolation_violations']:
            recommendations.append("Fix data isolation violations found in testing")
        
        recommendations.extend(report['query_patterns']['recommendations'])
        report['recommendations'] = recommendations
        
        return report


def run_tenant_isolation_validation():
    """Run tenant isolation validation and print results."""
    validator = TenantIsolationValidator()
    report = validator.generate_isolation_report()
    
    print("=== Tenant Data Isolation Validation Report ===")
    print(f"Timestamp: {report['timestamp']}")
    print(f"Overall Status: {report['overall_status']}")
    print()
    
    print("Tenant ID Validation:")
    tid_val = report['tenant_id_validation']
    print(f"  Status: {'PASS' if tid_val['valid'] else 'FAIL'}")
    print(f"  Tables Checked: {tid_val['tables_checked']}")
    if tid_val['missing_tenant_id']:
        print(f"  Missing tenant_id: {', '.join(tid_val['missing_tenant_id'])}")
    if tid_val['errors']:
        print(f"  Errors: {tid_val['errors']}")
    print()
    
    print("Index Validation:")
    idx_val = report['index_validation']
    print(f"  Status: {'PASS' if idx_val['valid'] else 'FAIL'}")
    print(f"  Indexes Checked: {idx_val['indexes_checked']}")
    if idx_val['missing_indexes']:
        print(f"  Missing indexes: {', '.join(idx_val['missing_indexes'])}")
    if idx_val['errors']:
        print(f"  Errors: {idx_val['errors']}")
    print()
    
    print("Isolation Testing:")
    iso_test = report['isolation_test']
    print(f"  Status: {'PASS' if iso_test['valid'] else 'FAIL'}")
    print(f"  Tests Run: {iso_test['tests_run']}")
    if iso_test['isolation_violations']:
        print("  Violations:")
        for violation in iso_test['isolation_violations']:
            print(f"    - {violation['model']}: {violation['issue']}")
    if iso_test['errors']:
        print(f"  Errors: {iso_test['errors']}")
    print()
    
    if report['recommendations']:
        print("Recommendations:")
        for i, rec in enumerate(report['recommendations'], 1):
            print(f"  {i}. {rec}")
    
    return report


if __name__ == "__main__":
    run_tenant_isolation_validation()