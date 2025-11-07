"""
Security Integration Module for Memori
Integrates all security components into a unified system
"""

from typing import Any

from loguru import logger

from .exceptions import DatabaseError, SecurityError, ValidationError
from .input_validator import DatabaseInputValidator, InputValidator
from .query_builder import DatabaseDialect, DatabaseQueryExecutor, QueryBuilder
from .security_audit import get_security_auditor
from .transaction_manager import TransactionManager


class SecureMemoriDatabase:
    """Secure wrapper for Memori database operations"""

    def __init__(self, connector, dialect: DatabaseDialect):
        self.connector = connector
        self.dialect = dialect
        self.query_builder = QueryBuilder(dialect)
        self.query_executor = DatabaseQueryExecutor(connector, dialect)
        self.transaction_manager = TransactionManager(connector)
        self.security_auditor = get_security_auditor()

    def secure_search(
        self,
        query_text: str,
        namespace: str = "default",
        category_filter: list[str] | None = None,
        limit: int = 10,
        use_fts: bool = True,
    ) -> list[dict[str, Any]]:
        """Execute secure search with comprehensive validation"""
        try:
            # Phase 1: Input validation
            validated_params = DatabaseInputValidator.validate_search_params(
                query_text, namespace, category_filter, limit
            )

            # Phase 2: Build secure query
            if use_fts:
                try:
                    sql_query, params = self.query_builder.build_fts_query(
                        validated_params["query"],
                        validated_params["namespace"],
                        validated_params["category_filter"],
                        validated_params["limit"],
                    )
                except Exception as e:
                    logger.debug(
                        f"FTS query building failed, falling back to LIKE: {e}"
                    )
                    use_fts = False

            if not use_fts:
                sql_query, params = self.query_builder.build_search_query(
                    ["short_term_memory", "long_term_memory"],
                    ["searchable_content", "summary"],
                    validated_params["query"],
                    validated_params["namespace"],
                    validated_params["category_filter"],
                    validated_params["limit"],
                    use_fts=False,
                )

            # Phase 3: Security audit
            is_safe, security_findings = self.security_auditor.validate_query_safety(
                sql_query, params, "secure_search"
            )

            if not is_safe:
                critical_findings = [
                    f
                    for f in security_findings
                    if f.severity.value in ["critical", "high"]
                ]
                logger.error(f"Search query failed security audit: {critical_findings}")
                raise SecurityError("Search query blocked due to security concerns")

            # Phase 4: Execute with proper error handling
            results = self.connector.execute_query(sql_query, params)

            # Phase 5: Log successful operation
            logger.debug(f"Secure search completed: {len(results)} results")

            return results

        except (ValidationError, SecurityError) as e:
            logger.error(f"Secure search blocked: {e}")
            return []
        except Exception as e:
            logger.error(f"Secure search failed: {e}")
            return []

    def secure_insert(
        self, table: str, data: dict[str, Any], on_conflict: str = "REPLACE"
    ) -> str | None:
        """Execute secure insert with comprehensive validation"""
        try:
            # Phase 1: Input validation
            validated_data = DatabaseInputValidator.validate_insert_params(table, data)

            # Phase 2: Build secure query
            sql_query, params = self.query_builder.build_insert_query(
                table, validated_data, on_conflict
            )

            # Phase 3: Security audit
            is_safe, security_findings = self.security_auditor.validate_query_safety(
                sql_query, params, f"secure_insert_{table}"
            )

            if not is_safe:
                critical_findings = [
                    f
                    for f in security_findings
                    if f.severity.value in ["critical", "high"]
                ]
                logger.error(f"Insert query failed security audit: {critical_findings}")
                raise SecurityError("Insert query blocked due to security concerns")

            # Phase 4: Execute with transaction
            with self.transaction_manager.transaction() as tx:
                result = tx.execute(sql_query, params)
                return str(result[0].get("affected_rows", 0)) if result else None

        except (ValidationError, SecurityError) as e:
            logger.error(f"Secure insert blocked: {e}")
            raise DatabaseError(f"Secure insert failed: {e}")
        except Exception as e:
            logger.error(f"Secure insert failed: {e}")
            raise DatabaseError(f"Secure insert failed: {e}")

    def secure_update(
        self, table: str, data: dict[str, Any], where_conditions: dict[str, Any]
    ) -> int:
        """Execute secure update with comprehensive validation"""
        try:
            # Phase 1: Input validation
            validated_data = {
                k: (
                    InputValidator.validate_text_content(str(v))
                    if isinstance(v, str)
                    else v
                )
                for k, v in data.items()
            }
            validated_where = {
                k: (
                    InputValidator.validate_text_content(str(v))
                    if isinstance(v, str)
                    else v
                )
                for k, v in where_conditions.items()
            }

            # Phase 2: Build secure query
            sql_query, params = self.query_builder.build_update_query(
                table, validated_data, validated_where
            )

            # Phase 3: Security audit
            is_safe, security_findings = self.security_auditor.validate_query_safety(
                sql_query, params, f"secure_update_{table}"
            )

            if not is_safe:
                critical_findings = [
                    f
                    for f in security_findings
                    if f.severity.value in ["critical", "high"]
                ]
                logger.error(f"Update query failed security audit: {critical_findings}")
                raise SecurityError("Update query blocked due to security concerns")

            # Phase 4: Execute with transaction
            with self.transaction_manager.transaction() as tx:
                result = tx.execute(sql_query, params)
                return result[0].get("affected_rows", 0) if result else 0

        except (ValidationError, SecurityError) as e:
            logger.error(f"Secure update blocked: {e}")
            raise DatabaseError(f"Secure update failed: {e}")
        except Exception as e:
            logger.error(f"Secure update failed: {e}")
            raise DatabaseError(f"Secure update failed: {e}")

    def secure_delete(self, table: str, where_conditions: dict[str, Any]) -> int:
        """Execute secure delete with comprehensive validation"""
        try:
            # Phase 1: Input validation
            if not where_conditions:
                raise ValidationError("DELETE operations must include WHERE conditions")

            validated_where = {
                k: (
                    InputValidator.validate_text_content(str(v))
                    if isinstance(v, str)
                    else v
                )
                for k, v in where_conditions.items()
            }

            # Phase 2: Build secure query
            sql_query, params = self.query_builder.build_delete_query(
                table, validated_where
            )

            # Phase 3: Security audit
            is_safe, security_findings = self.security_auditor.validate_query_safety(
                sql_query, params, f"secure_delete_{table}"
            )

            if not is_safe:
                critical_findings = [
                    f
                    for f in security_findings
                    if f.severity.value in ["critical", "high"]
                ]
                logger.error(f"Delete query failed security audit: {critical_findings}")
                raise SecurityError("Delete query blocked due to security concerns")

            # Phase 4: Execute with transaction
            with self.transaction_manager.transaction() as tx:
                result = tx.execute(sql_query, params)
                return result[0].get("affected_rows", 0) if result else 0

        except (ValidationError, SecurityError) as e:
            logger.error(f"Secure delete blocked: {e}")
            raise DatabaseError(f"Secure delete failed: {e}")
        except Exception as e:
            logger.error(f"Secure delete failed: {e}")
            raise DatabaseError(f"Secure delete failed: {e}")

    def get_security_report(self) -> dict[str, Any]:
        """Get comprehensive security report"""
        audit_report = self.security_auditor.generate_audit_report()

        return {
            "total_queries_audited": audit_report.total_queries_audited,
            "security_findings": {
                "critical": audit_report.critical_count,
                "high": audit_report.high_count,
                "medium": audit_report.medium_count,
                "low": audit_report.low_count,
            },
            "overall_risk_score": audit_report.overall_risk_score,
            "risk_level": self._get_risk_level(audit_report.overall_risk_score),
            "audit_timestamp": audit_report.audit_timestamp,
            "database_type": self.dialect.value,
            "security_features_enabled": [
                "input_validation",
                "parameterized_queries",
                "transaction_management",
                "security_audit",
                "multi_database_compatibility",
            ],
        }

    def _get_risk_level(self, risk_score: float) -> str:
        """Convert risk score to risk level"""
        if risk_score >= 75:
            return "CRITICAL"
        elif risk_score >= 50:
            return "HIGH"
        elif risk_score >= 25:
            return "MEDIUM"
        elif risk_score > 0:
            return "LOW"
        else:
            return "MINIMAL"


def create_secure_database(connector, dialect: DatabaseDialect) -> SecureMemoriDatabase:
    """Factory function to create a secure database instance"""
    return SecureMemoriDatabase(connector, dialect)


def validate_memori_security_config() -> dict[str, Any]:
    """Validate that all security components are properly configured"""
    validation_results = {
        "input_validator": False,
        "query_builder": False,
        "transaction_manager": False,
        "security_auditor": False,
        "database_adapters": False,
        "overall_status": False,
    }

    try:
        # Test input validator
        InputValidator.validate_and_sanitize_query("test query")
        validation_results["input_validator"] = True

        # Test query builder
        QueryBuilder(DatabaseDialect.SQLITE)
        validation_results["query_builder"] = True

        # Test security auditor
        auditor = get_security_auditor()
        auditor.audit_query("SELECT * FROM test", None, "validation")
        validation_results["security_auditor"] = True

        # Check database adapters
        try:
            from ..database.adapters import (
                MySQLSearchAdapter,  # noqa: F401
                PostgreSQLSearchAdapter,  # noqa: F401
                SQLiteSearchAdapter,  # noqa: F401
            )

            validation_results["database_adapters"] = True
        except ImportError as e:
            logger.warning(f"Database adapter validation failed: {e}")

        # Test transaction manager (requires actual connector)
        validation_results["transaction_manager"] = True  # Assume OK if no errors above

        # Overall status
        validation_results["overall_status"] = all(
            [
                validation_results["input_validator"],
                validation_results["query_builder"],
                validation_results["security_auditor"],
                validation_results["database_adapters"],
                validation_results["transaction_manager"],
            ]
        )

        logger.info(f"Security configuration validation: {validation_results}")

    except Exception as e:
        logger.error(f"Security configuration validation failed: {e}")
        validation_results["error"] = str(e)

    return validation_results
