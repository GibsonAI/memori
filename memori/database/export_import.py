"""
Export/Import functionality for Memori memory system.

Provides comprehensive export and import capabilities for chat history,
short-term memory, and long-term memory with support for multiple formats:
JSON, SQLite, CSV, and SQL.
"""

import base64
import contextlib
import gzip
import hashlib
import io
import json
import os
import shutil
import tempfile
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, Generator, Iterable, List, Optional, Tuple

from loguru import logger
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from ..utils.exceptions import DatabaseError, MemoriError
from .models import Base, ChatHistory, LongTermMemory, ShortTermMemory


def _extract_column_values(record: Any) -> Dict[str, Any]:
    """Extract column values from a SQLAlchemy model preserving native types."""
    return {
        column.name: getattr(record, column.name)
        for column in record.__table__.columns
    }


class ExportFormat(str, Enum):
    """Supported export formats"""

    JSON = "json"
    SQLITE = "sqlite"
    CSV = "csv"
    SQL = "sql"


class MergeStrategy(str, Enum):
    """Import merge strategies"""

    REPLACE = "replace"  # Delete existing, insert new
    MERGE = "merge"  # Insert only new records
    SKIP_DUPLICATES = "skip_duplicates"  # Skip if exists


class ExportManifest:
    """Export manifest structure"""

    EXPORT_VERSION = "1.0"

    def __init__(
        self,
        source_database_type: str,
        export_scope: Dict[str, Any],
        record_counts: Dict[str, int],
        checksums: Dict[str, str],
        export_format: str = "json",
        chunk_size: int = 1000,
        batch_size: int = 500,
        compression: str | None = None,
        checksum_algorithm: str = "sha256",
        encrypted: bool = False,
    ):
        self.export_version = self.EXPORT_VERSION
        self.export_timestamp = datetime.utcnow().isoformat() + "Z"
        self.source_database_type = source_database_type
        self.export_scope = export_scope
        self.record_counts = record_counts
        self.checksums = checksums
        self.export_format = export_format
        self.chunk_size = chunk_size
        self.batch_size = batch_size
        self.compression = compression
        self.checksum_algorithm = checksum_algorithm
        self.encrypted = encrypted

    def to_dict(self) -> Dict[str, Any]:
        """Convert manifest to dictionary"""
        return {
            "export_version": self.export_version,
            "export_timestamp": self.export_timestamp,
            "source_database_type": self.source_database_type,
            "export_scope": self.export_scope,
            "record_counts": self.record_counts,
            "checksums": self.checksums,
            "export_format": self.export_format,
            "chunk_size": self.chunk_size,
            "batch_size": self.batch_size,
            "compression": self.compression,
            "checksum_algorithm": self.checksum_algorithm,
            "encrypted": self.encrypted,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExportManifest":
        """Create manifest from dictionary"""
        return cls(
            source_database_type=data.get("source_database_type", "unknown"),
            export_scope=data.get("export_scope", {}),
            record_counts=data.get("record_counts", {}),
            checksums=data.get("checksums", {}),
            export_format=data.get("export_format", "json"),
            chunk_size=data.get("chunk_size", 1000),
            batch_size=data.get("batch_size", 500),
            compression=data.get("compression"),
            checksum_algorithm=data.get("checksum_algorithm", "sha256"),
            encrypted=data.get("encrypted", False),
        )


class ChecksumCalculator:
    """Streaming checksum helper"""

    def __init__(self, algorithm: str = "sha256"):
        try:
            self._hasher = hashlib.new(algorithm)
        except ValueError as exc:
            raise MemoriError(f"Unsupported checksum algorithm: {algorithm}") from exc
        self.algorithm = algorithm

    def update(self, record: Dict[str, Any]) -> None:
        payload = json.dumps(record, sort_keys=True, default=str).encode("utf-8")
        self._hasher.update(payload)

    def hexdigest(self) -> str:
        return self._hasher.hexdigest()


class ExportManager:
    """Manages export operations for Memori memory system"""

    def __init__(self, db_manager: Any):
        """
        Initialize ExportManager.

        Args:
            db_manager: SQLAlchemyDatabaseManager instance
        """
        self.db_manager = db_manager
        self.database_type = db_manager.database_type

    def export(
        self,
        export_path: str,
        format: str = "json",
        user_id: Optional[str] = None,
        assistant_id: Optional[str] = None,
        session_id: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        include_metadata: bool = True,
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
        compression: Optional[str] = None,
        chunk_size: int = 1000,
        checksum_algorithm: str = "sha256",
        compresslevel: int = 5,
        encryption_key: Optional[str] = None,
        audit_logging: bool = True,
    ) -> Dict[str, Any]:
        """
        Export memories to file.

        Args:
            export_path: Path to export file
            format: Export format (json, sqlite, csv, sql)
            user_id: Filter by user_id
            assistant_id: Filter by assistant_id
            session_id: Filter by session_id
            date_from: Filter by start date
            date_to: Filter by end date
            include_metadata: Include export manifest
            progress_callback: Optional callback for progress updates
            compression: Optional compression codec ('gzip')
            chunk_size: Number of rows streamed per chunk
            checksum_algorithm: Hash algorithm for table checksums
            compresslevel: Compression level for gzip (1-9)
            encryption_key: Optional key for encrypting the export
            audit_logging: Emit audit log entries for this export

        Returns:
            Export summary dictionary
        """
        # Validate format
        try:
            export_format = ExportFormat(format.lower())
        except ValueError:
            raise MemoriError(f"Unsupported export format: {format}")

        compression = compression.lower() if compression else None

        # Pre-export validation
        self._validate_pre_export(
            export_path,
            user_id,
            date_from,
            date_to,
            chunk_size,
            checksum_algorithm,
            compression,
        )

        # Build export scope
        export_scope = {
            "user_id": user_id,
            "assistant_id": assistant_id,
            "session_id": session_id,
            "date_from": date_from.isoformat() if date_from else None,
            "date_to": date_to.isoformat() if date_to else None,
            "compression": compression,
            "chunk_size": chunk_size,
        }

        if audit_logging:
            self._audit_event(
                "export_started",
                {
                    "format": export_format.value,
                    "path": str(export_path),
                    "user_id": user_id,
                    "assistant_id": assistant_id,
                    "session_id": session_id,
                    "compression": compression,
                    "encrypted": bool(encryption_key),
                },
            )

        # Route to format-specific handler
        if export_format == ExportFormat.JSON:
            result = self._export_json(
                export_path,
                export_scope,
                include_metadata,
                progress_callback,
                compression,
                chunk_size,
                checksum_algorithm,
                compresslevel,
                encryption_key,
            )
        elif export_format == ExportFormat.SQLITE:
            result = self._export_sqlite(
                export_path,
                export_scope,
                include_metadata,
                progress_callback,
                compression,
                checksum_algorithm,
                compresslevel,
                encryption_key,
            )
        elif export_format == ExportFormat.CSV:
            result = self._export_csv(
                export_path,
                export_scope,
                include_metadata,
                progress_callback,
                compression,
                checksum_algorithm,
                compresslevel,
                encryption_key,
            )
        elif export_format == ExportFormat.SQL:
            result = self._export_sql(
                export_path,
                export_scope,
                include_metadata,
                progress_callback,
                compression,
                checksum_algorithm,
                compresslevel,
                encryption_key,
            )

        if audit_logging:
            self._audit_event(
                "export_completed",
                {
                    "format": export_format.value,
                    "path": result.get("export_path"),
                    "record_counts": result.get("record_counts", {}),
                    "file_size": result.get("file_size"),
                },
            )

        return result

    def _validate_pre_export(
        self,
        export_path: str,
        user_id: Optional[str],
        date_from: Optional[datetime],
        date_to: Optional[datetime],
        chunk_size: int,
        checksum_algorithm: str,
        compression: Optional[str],
    ):
        """Validate pre-export conditions"""
        # Check export path
        export_file = Path(export_path)
        export_dir = export_file.parent
        if not export_dir.exists():
            export_dir.mkdir(parents=True, exist_ok=True)

        # Check disk space (basic check - at least 100MB free)
        try:
            stat = shutil.disk_usage(export_dir)
            free_space_mb = stat.free / (1024 * 1024)
            if free_space_mb < 100:
                raise MemoriError(
                    f"Insufficient disk space: {free_space_mb:.1f}MB free (need at least 100MB)"
                )
        except Exception as e:
            logger.warning(f"Could not check disk space: {e}")

        # Validate date range
        if date_from and date_to and date_from > date_to:
            raise MemoriError("date_from must be before date_to")

        if chunk_size <= 0:
            raise MemoriError("chunk_size must be greater than zero")

        try:
            hashlib.new(checksum_algorithm)
        except ValueError as exc:
            raise MemoriError(
                f"Unsupported checksum algorithm: {checksum_algorithm}"
            ) from exc

        if compression and compression.lower() not in {"gzip"}:
            raise MemoriError(f"Unsupported compression codec: {compression}")

    def _create_temp_path(self, export_path: str) -> Path:
        """Create a temp file in the target directory"""
        export_file = Path(export_path)
        export_dir = export_file.parent
        export_dir.mkdir(parents=True, exist_ok=True)
        fd, temp_path = tempfile.mkstemp(
            prefix=f"{export_file.stem}_", suffix=".tmp", dir=export_dir
        )
        os.close(fd)
        return Path(temp_path)

    def _finalize_artifact(
        self,
        temp_path: Path,
        export_path: str,
        compression: Optional[str],
        encryption_key: Optional[str],
        compresslevel: int,
    ) -> Path:
        """Apply compression/encryption if requested and move to destination"""
        target_path = Path(export_path)
        current_path = temp_path

        if compression:
            compression = compression.lower()
            compressed_path = (
                target_path
                if encryption_key is None
                else target_path.with_suffix(target_path.suffix + ".cmp")
            )
            self._compress_file(
                current_path,
                compressed_path,
                compression,
                compresslevel,
            )
            current_path.unlink(missing_ok=True)
            current_path = compressed_path
        else:
            target_path.parent.mkdir(parents=True, exist_ok=True)

        if not compression and encryption_key is None:
            shutil.move(str(current_path), str(target_path))
            current_path = target_path

        if encryption_key:
            source_path = current_path
            if source_path == target_path and not compression:
                # Re-open temp file before it was moved
                source_path = current_path
            self._encrypt_file(source_path, target_path, encryption_key)
            if source_path != target_path:
                source_path.unlink(missing_ok=True)
            current_path = target_path

        return current_path

    def _compress_file(
        self,
        input_path: Path,
        output_path: Path,
        compression: str,
        compresslevel: int,
    ) -> None:
        """Compress file to the output path"""
        if compression != "gzip":
            raise MemoriError(f"Unsupported compression codec: {compression}")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(input_path, "rb") as src, gzip.open(
            output_path, "wb", compresslevel=compresslevel
        ) as dst:
            shutil.copyfileobj(src, dst)

    def _derive_fernet_key(self, encryption_key: str) -> bytes:
        """Convert arbitrary string into Fernet-compatible key"""
        digest = hashlib.sha256(encryption_key.encode("utf-8")).digest()
        return base64.urlsafe_b64encode(digest)

    def _encrypt_file(
        self, input_path: Path, output_path: Path, encryption_key: str
    ) -> None:
        """Encrypt file using Fernet"""
        try:
            from cryptography.fernet import Fernet
        except ImportError as exc:
            raise MemoriError(
                "File encryption requires the 'cryptography' package"
            ) from exc

        key = self._derive_fernet_key(encryption_key)
        cipher = Fernet(key)
        with open(input_path, "rb") as src:
            data = src.read()
        encrypted = cipher.encrypt(data)
        with open(output_path, "wb") as dst:
            dst.write(encrypted)

    def _audit_event(self, action: str, details: Dict[str, Any]):
        """Emit audit log entry"""
        logger.info(f"[AUDIT] {action}: {details}")

    def _build_query_filters(
        self,
        session: Session,
        model: Any,
        export_scope: Dict[str, Any],
    ):
        """Build SQLAlchemy query with filters"""
        query = session.query(model)

        # Apply filters
        filters = []

        if export_scope.get("user_id"):
            filters.append(model.user_id == export_scope["user_id"])

        if export_scope.get("assistant_id"):
            filters.append(model.assistant_id == export_scope["assistant_id"])

        if export_scope.get("session_id"):
            filters.append(model.session_id == export_scope["session_id"])

        if export_scope.get("date_from"):
            date_from = datetime.fromisoformat(export_scope["date_from"])
            filters.append(model.created_at >= date_from)

        if export_scope.get("date_to"):
            date_to = datetime.fromisoformat(export_scope["date_to"])
            filters.append(model.created_at <= date_to)

        if filters:
            query = query.filter(and_(*filters))

        # Order by timestamp for consistency
        if hasattr(model, "created_at"):
            query = query.order_by(model.created_at)

        return query

    def _export_json(
        self,
        export_path: str,
        export_scope: Dict[str, Any],
        include_metadata: bool,
        progress_callback: Optional[Callable[[str, int, int], None]],
        compression: Optional[str],
        chunk_size: int,
        checksum_algorithm: str,
        compresslevel: int,
        encryption_key: Optional[str],
    ) -> Dict[str, Any]:
        """Export to JSON format with streaming writer"""
        session = self.db_manager.get_session()
        temp_path: Optional[Path] = None
        try:
            # Query data
            chat_history_query = self._build_query_filters(
                session, ChatHistory, export_scope
            )
            short_term_query = self._build_query_filters(
                session, ShortTermMemory, export_scope
            )
            long_term_query = self._build_query_filters(
                session, LongTermMemory, export_scope
            )

            # Get record counts
            chat_count = chat_history_query.count()
            short_term_count = short_term_query.count()
            long_term_count = long_term_query.count()

            if progress_callback:
                progress_callback("querying", 0, 100)

            chat_checksum = ChecksumCalculator(checksum_algorithm)
            short_checksum = ChecksumCalculator(checksum_algorithm)
            long_checksum = ChecksumCalculator(checksum_algorithm)

            chat_iter = self._stream_serialized_records(
                chat_history_query,
                chunk_size,
                chat_checksum,
                chat_count,
                progress_callback,
                "exporting_chat_history",
                0,
                30,
            )
            short_iter = self._stream_serialized_records(
                short_term_query,
                chunk_size,
                short_checksum,
                short_term_count,
                progress_callback,
                "exporting_short_term_memory",
                30,
                60,
            )
            long_iter = self._stream_serialized_records(
                long_term_query,
                chunk_size,
                long_checksum,
                long_term_count,
                progress_callback,
                "exporting_long_term_memory",
                60,
                90,
            )

            record_counts = {
                "chat_history": chat_count,
                "short_term_memory": short_term_count,
                "long_term_memory": long_term_count,
            }

            if progress_callback:
                progress_callback("writing", 90, 100)

            temp_path = self._create_temp_path(export_path)
            with open(temp_path, "w", encoding="utf-8") as writer:
                self._write_json_stream(
                    writer,
                    [
                        ("chat_history", chat_iter),
                        ("short_term_memory", short_iter),
                        ("long_term_memory", long_iter),
                    ],
                    manifest_provider=(
                        lambda: ExportManifest(
                            source_database_type=self.database_type,
                            export_scope=export_scope,
                            record_counts=record_counts,
                            checksums={
                                "chat_history": chat_checksum.hexdigest(),
                                "short_term_memory": short_checksum.hexdigest(),
                                "long_term_memory": long_checksum.hexdigest(),
                            },
                            export_format="json",
                            chunk_size=chunk_size,
                            batch_size=chunk_size,
                            compression=compression,
                            checksum_algorithm=checksum_algorithm,
                            encrypted=bool(encryption_key),
                        ).to_dict()
                    )
                    if include_metadata
                    else None,
                )

            final_path = self._finalize_artifact(
                temp_path,
                export_path,
                compression,
                encryption_key,
                compresslevel,
            )

            checksums = {
                "chat_history": chat_checksum.hexdigest(),
                "short_term_memory": short_checksum.hexdigest(),
                "long_term_memory": long_checksum.hexdigest(),
            }

            if progress_callback:
                progress_callback("complete", 100, 100)

            return {
                "export_path": str(final_path),
                "format": "json",
                "record_counts": record_counts,
                "file_size": final_path.stat().st_size,
                "checksums": checksums,
            }

        finally:
            if temp_path and temp_path.exists():
                temp_path.unlink(missing_ok=True)
            session.close()

    def _serialize_record(self, record: Any) -> Dict[str, Any]:
        """Serialize SQLAlchemy record to dictionary"""
        result = {}
        for column in record.__table__.columns:
            value = getattr(record, column.name)
            # Handle datetime objects
            if isinstance(value, datetime):
                value = value.isoformat()
            # Handle JSON columns (already dict/list)
            elif isinstance(value, (dict, list)):
                value = value
            result[column.name] = value
        return result

    def _calculate_checksum(
        self, data: List[Dict[str, Any]], algorithm: str = "sha256"
    ) -> str:
        """Calculate checksum for in-memory datasets"""
        calculator = ChecksumCalculator(algorithm)
        for record in data:
            calculator.update(record)
        return calculator.hexdigest()

    def _stream_serialized_records(
        self,
        query,
        chunk_size: int,
        checksum: ChecksumCalculator,
        total: int,
        progress_callback: Optional[Callable[[str, int, int], None]],
        label: str,
        progress_start: int,
        progress_end: int,
    ) -> Iterable[Dict[str, Any]]:
        """Yield serialized records while updating checksum and progress"""
        progress_span = max(progress_end - progress_start, 1)
        progress_every = max(1, chunk_size // 2)

        def generator():
            emitted = 0
            for record in query.yield_per(chunk_size):
                serialized = self._serialize_record(record)
                checksum.update(serialized)
                emitted += 1
                if (
                    progress_callback
                    and emitted % progress_every == 0
                    and total > 0
                ):
                    progress = progress_start + int(
                        (emitted / max(total, 1)) * progress_span
                    )
                    progress = min(progress, progress_end)
                    progress_callback(label, progress, 100)
                yield serialized

            if progress_callback:
                progress_callback(label, progress_end, 100)

        if total == 0:
            return []
        return generator()

    def _write_json_stream(
        self,
        writer: io.TextIOWrapper,
        tables: List[Tuple[str, Iterable[Dict[str, Any]]]],
        manifest_provider: Optional[Callable[[], Dict[str, Any]]] = None,
    ) -> None:
        """Write JSON data incrementally with optional manifest footer"""
        writer.write("{\n")
        section_written = False

        for table_name, generator in tables:
            if section_written:
                writer.write(",\n")
            writer.write(f'  "{table_name}": [\n')
            first_record = True
            for record in generator:
                if not first_record:
                    writer.write(",\n")
                writer.write("    ")
                json.dump(record, writer, default=str, ensure_ascii=False)
                first_record = False
            writer.write("\n  ]")
            section_written = True

        if manifest_provider:
            manifest = manifest_provider()
            if section_written:
                writer.write(",\n")
            writer.write('  "_manifest": ')
            json.dump(manifest, writer, default=str, ensure_ascii=False, indent=2)
            section_written = True

        if not section_written:
            writer.write("  ")

        writer.write("\n}\n")

    def _export_sqlite(
        self,
        export_path: str,
        export_scope: Dict[str, Any],
        include_metadata: bool,
        progress_callback: Optional[Callable[[str, int, int], None]],
        compression: Optional[str],
        checksum_algorithm: str,
        compresslevel: int,
        encryption_key: Optional[str],
    ) -> Dict[str, Any]:
        """Export to SQLite format"""
        from sqlalchemy import Column, String, Table, Text, create_engine
        from sqlalchemy.orm import sessionmaker

        export_db_path = export_path
        if not export_db_path.endswith(".db") and not export_db_path.endswith(".sqlite"):
            export_db_path = export_db_path + ".db"

        temp_db_path = self._create_temp_path(export_db_path)
        export_engine = create_engine(f"sqlite:///{temp_db_path}", echo=False)
        export_session = sessionmaker(bind=export_engine)()
        session_closed = False
        engine_disposed = False

        try:
            Base.metadata.create_all(bind=export_engine)

            if progress_callback:
                progress_callback("creating_schema", 10, 100)

            source_session = self.db_manager.get_session()

            try:
                chat_history_query = self._build_query_filters(
                    source_session, ChatHistory, export_scope
                )
                short_term_query = self._build_query_filters(
                    source_session, ShortTermMemory, export_scope
                )
                long_term_query = self._build_query_filters(
                    source_session, LongTermMemory, export_scope
                )

                chat_count = chat_history_query.count()
                short_term_count = short_term_query.count()
                long_term_count = long_term_query.count()

                record_counts = {
                    "chat_history": chat_count,
                    "short_term_memory": short_term_count,
                    "long_term_memory": long_term_count,
                }

                # Export chat_history
                if progress_callback:
                    progress_callback("exporting_chat_history", 20, 100)

                chat_records = []
                for i, record in enumerate(chat_history_query.all()):
                    record_dict = self._serialize_record(record)
                    export_session.add(ChatHistory(**_extract_column_values(record)))
                    chat_records.append(record_dict)
                    if progress_callback and i % 100 == 0:
                        progress = 20 + int((i / max(chat_count, 1)) * 25)
                        progress_callback("exporting_chat_history", progress, 100)

                export_session.commit()

                # Export short_term_memory
                if progress_callback:
                    progress_callback("exporting_short_term_memory", 45, 100)

                short_term_records = []
                for i, record in enumerate(short_term_query.all()):
                    record_dict = self._serialize_record(record)
                    export_session.add(ShortTermMemory(**_extract_column_values(record)))
                    short_term_records.append(record_dict)
                    if progress_callback and i % 100 == 0:
                        progress = 45 + int((i / max(short_term_count, 1)) * 25)
                        progress_callback("exporting_short_term_memory", progress, 100)

                export_session.commit()

                # Export long_term_memory
                if progress_callback:
                    progress_callback("exporting_long_term_memory", 70, 100)

                long_term_records = []
                for i, record in enumerate(long_term_query.all()):
                    record_dict = self._serialize_record(record)
                    export_session.add(LongTermMemory(**_extract_column_values(record)))
                    long_term_records.append(record_dict)
                    if progress_callback and i % 100 == 0:
                        progress = 70 + int((i / max(long_term_count, 1)) * 25)
                        progress_callback("exporting_long_term_memory", progress, 100)

                export_session.commit()

                checksums = {
                    "chat_history": self._calculate_checksum(
                        chat_records, checksum_algorithm
                    ),
                    "short_term_memory": self._calculate_checksum(
                        short_term_records, checksum_algorithm
                    ),
                    "long_term_memory": self._calculate_checksum(
                        long_term_records, checksum_algorithm
                    ),
                }

                if include_metadata:
                    manifest = ExportManifest(
                        source_database_type=self.database_type,
                        export_scope=export_scope,
                        record_counts=record_counts,
                        checksums=checksums,
                        export_format="sqlite",
                        chunk_size=len(chat_records),
                        batch_size=len(chat_records),
                        compression=compression,
                        checksum_algorithm=checksum_algorithm,
                        encrypted=bool(encryption_key),
                    )
                    metadata_table = Table(
                        "export_manifest",
                        Base.metadata,
                        Column("key", String(255), primary_key=True),
                        Column("value", Text),
                    )
                    metadata_table.create(export_engine, checkfirst=True)
                    export_session.execute(
                        metadata_table.insert().values(
                            key="manifest", value=json.dumps(manifest.to_dict())
                        )
                    )
                    export_session.commit()

                if progress_callback:
                    progress_callback("complete", 100, 100)

                export_session.close()
                session_closed = True
                export_engine.dispose()
                engine_disposed = True

                final_path = Path(export_db_path)
                if compression or encryption_key:
                    final_path = self._finalize_artifact(
                        Path(temp_db_path),
                        export_db_path,
                        compression,
                        encryption_key,
                        compresslevel,
                    )
                else:
                    shutil.move(str(temp_db_path), export_db_path)
                    final_path = Path(export_db_path)

                return {
                    "export_path": str(final_path),
                    "format": "sqlite",
                    "record_counts": record_counts,
                    "file_size": final_path.stat().st_size,
                    "checksums": checksums,
                }

            finally:
                source_session.close()

        finally:
            if not session_closed:
                with contextlib.suppress(Exception):
                    export_session.close()
            if not engine_disposed:
                with contextlib.suppress(Exception):
                    export_engine.dispose()

    def _export_csv(
        self,
        export_path: str,
        export_scope: Dict[str, Any],
        include_metadata: bool,
        progress_callback: Optional[Callable[[str, int, int], None]],
        compression: Optional[str],
        checksum_algorithm: str,
        compresslevel: int,
        encryption_key: Optional[str],
    ) -> Dict[str, Any]:
        """Export to CSV format"""
        import csv

        if compression or encryption_key:
            raise MemoriError(
                "CSV export currently outputs multiple files and cannot be "
                "automatically compressed or encrypted. Use JSON/SQLite export "
                "or compress the folder manually."
            )

        export_dir = Path(export_path).parent
        export_base = Path(export_path).stem

        # Create directory if needed
        export_dir.mkdir(parents=True, exist_ok=True)

        session = self.db_manager.get_session()
        try:
            # Query data
            chat_history_query = self._build_query_filters(
                session, ChatHistory, export_scope
            )
            short_term_query = self._build_query_filters(
                session, ShortTermMemory, export_scope
            )
            long_term_query = self._build_query_filters(
                session, LongTermMemory, export_scope
            )

            # Get record counts
            chat_count = chat_history_query.count()
            short_term_count = short_term_query.count()
            long_term_count = long_term_query.count()

            record_counts = {
                "chat_history": chat_count,
                "short_term_memory": short_term_count,
                "long_term_memory": long_term_count,
            }

            csv_files = []
            checksums = {}

            # Export chat_history
            if progress_callback:
                progress_callback("exporting_chat_history", 10, 100)

            chat_file = export_dir / f"{export_base}_chat_history.csv"
            chat_records = []
            with open(chat_file, "w", newline="", encoding="utf-8") as f:
                writer = None
                for i, record in enumerate(chat_history_query.all()):
                    record_dict = self._serialize_record(record)
                    chat_records.append(record_dict)

                    # Initialize writer with headers from first record
                    if writer is None:
                        fieldnames = list(record_dict.keys())
                        writer = csv.DictWriter(f, fieldnames=fieldnames)
                        writer.writeheader()

                    # Stringify JSON fields
                    row = {}
                    for key, value in record_dict.items():
                        if isinstance(value, (dict, list)):
                            row[key] = json.dumps(value, default=str)
                        elif isinstance(value, datetime):
                            row[key] = value.isoformat()
                        else:
                            row[key] = value

                    writer.writerow(row)

                    if progress_callback and i % 100 == 0:
                        progress = 10 + int((i / max(chat_count, 1)) * 30)
                        progress_callback("exporting_chat_history", progress, 100)

            csv_files.append(str(chat_file))
            checksums["chat_history"] = self._calculate_checksum(
                chat_records, checksum_algorithm
            )

            # Export short_term_memory
            if progress_callback:
                progress_callback("exporting_short_term_memory", 40, 100)

            short_term_file = export_dir / f"{export_base}_short_term_memory.csv"
            short_term_records = []
            with open(short_term_file, "w", newline="", encoding="utf-8") as f:
                writer = None
                for i, record in enumerate(short_term_query.all()):
                    record_dict = self._serialize_record(record)
                    short_term_records.append(record_dict)

                    if writer is None:
                        fieldnames = list(record_dict.keys())
                        writer = csv.DictWriter(f, fieldnames=fieldnames)
                        writer.writeheader()

                    row = {}
                    for key, value in record_dict.items():
                        if isinstance(value, (dict, list)):
                            row[key] = json.dumps(value, default=str)
                        elif isinstance(value, datetime):
                            row[key] = value.isoformat()
                        else:
                            row[key] = value

                    writer.writerow(row)

                    if progress_callback and i % 100 == 0:
                        progress = 40 + int((i / max(short_term_count, 1)) * 30)
                        progress_callback("exporting_short_term_memory", progress, 100)

            csv_files.append(str(short_term_file))
            checksums["short_term_memory"] = self._calculate_checksum(
                short_term_records, checksum_algorithm
            )

            # Export long_term_memory
            if progress_callback:
                progress_callback("exporting_long_term_memory", 70, 100)

            long_term_file = export_dir / f"{export_base}_long_term_memory.csv"
            long_term_records = []
            with open(long_term_file, "w", newline="", encoding="utf-8") as f:
                writer = None
                for i, record in enumerate(long_term_query.all()):
                    record_dict = self._serialize_record(record)
                    long_term_records.append(record_dict)

                    if writer is None:
                        fieldnames = list(record_dict.keys())
                        writer = csv.DictWriter(f, fieldnames=fieldnames)
                        writer.writeheader()

                    row = {}
                    for key, value in record_dict.items():
                        if isinstance(value, (dict, list)):
                            row[key] = json.dumps(value, default=str)
                        elif isinstance(value, datetime):
                            row[key] = value.isoformat()
                        else:
                            row[key] = value

                    writer.writerow(row)

                    if progress_callback and i % 100 == 0:
                        progress = 70 + int((i / max(long_term_count, 1)) * 25)
                        progress_callback("exporting_long_term_memory", progress, 100)

            csv_files.append(str(long_term_file))
            checksums["long_term_memory"] = self._calculate_checksum(
                long_term_records, checksum_algorithm
            )

            # Create manifest file
            manifest_file = export_dir / f"{export_base}_manifest.json"
            manifest_data = {
                "export_version": ExportManifest.EXPORT_VERSION,
                "export_timestamp": datetime.utcnow().isoformat() + "Z",
                "source_database_type": self.database_type,
                "export_scope": export_scope,
                "record_counts": record_counts,
                "checksums": checksums,
                "csv_files": csv_files,
                "compression": compression,
                "checksum_algorithm": checksum_algorithm,
                "encrypted": bool(encryption_key),
            }

            with open(manifest_file, "w", encoding="utf-8") as f:
                json.dump(manifest_data, f, indent=2, default=str)

            if progress_callback:
                progress_callback("complete", 100, 100)

            # Calculate total file size
            total_size = sum(Path(f).stat().st_size for f in csv_files)
            total_size += manifest_file.stat().st_size

            return {
                "export_path": str(manifest_file),
                "format": "csv",
                "record_counts": record_counts,
                "file_size": total_size,
                "checksums": checksums,
                "csv_files": csv_files,
            }

        finally:
            session.close()

    def _export_sql(
        self,
        export_path: str,
        export_scope: Dict[str, Any],
        include_metadata: bool,
        progress_callback: Optional[Callable[[str, int, int], None]],
        compression: Optional[str],
        checksum_algorithm: str,
        compresslevel: int,
        encryption_key: Optional[str],
    ) -> Dict[str, Any]:
        """Export to SQL format"""
        from sqlalchemy.schema import CreateTable

        session = self.db_manager.get_session()
        try:
            # Query data
            chat_history_query = self._build_query_filters(
                session, ChatHistory, export_scope
            )
            short_term_query = self._build_query_filters(
                session, ShortTermMemory, export_scope
            )
            long_term_query = self._build_query_filters(
                session, LongTermMemory, export_scope
            )

            # Get record counts
            chat_count = chat_history_query.count()
            short_term_count = short_term_query.count()
            long_term_count = long_term_query.count()

            record_counts = {
                "chat_history": chat_count,
                "short_term_memory": short_term_count,
                "long_term_memory": long_term_count,
            }

            # Generate SQL statements
            sql_statements = []

            # Database-specific SQL generation
            if self.database_type == "postgresql":
                sql_statements.append("BEGIN;")
            elif self.database_type == "mysql":
                sql_statements.append("START TRANSACTION;")
            else:
                sql_statements.append("BEGIN TRANSACTION;")

            # Generate CREATE TABLE statements (if needed)
            if include_metadata:
                sql_statements.append("-- Export generated by Memori")
                sql_statements.append(f"-- Export timestamp: {datetime.utcnow().isoformat()}Z")
                sql_statements.append(f"-- Source database: {self.database_type}")
                sql_statements.append("")

            # Export chat_history
            if progress_callback:
                progress_callback("exporting_chat_history", 10, 100)

            chat_records = []
            for i, record in enumerate(chat_history_query.all()):
                record_dict = self._serialize_record(record)
                chat_records.append(record_dict)
                sql_statements.append(
                    self._generate_insert_statement("chat_history", record_dict)
                )
                if progress_callback and i % 100 == 0:
                    progress = 10 + int((i / max(chat_count, 1)) * 30)
                    progress_callback("exporting_chat_history", progress, 100)

            # Export short_term_memory
            if progress_callback:
                progress_callback("exporting_short_term_memory", 40, 100)

            short_term_records = []
            for i, record in enumerate(short_term_query.all()):
                record_dict = self._serialize_record(record)
                short_term_records.append(record_dict)
                sql_statements.append(
                    self._generate_insert_statement("short_term_memory", record_dict)
                )
                if progress_callback and i % 100 == 0:
                    progress = 40 + int((i / max(short_term_count, 1)) * 30)
                    progress_callback("exporting_short_term_memory", progress, 100)

            # Export long_term_memory
            if progress_callback:
                progress_callback("exporting_long_term_memory", 70, 100)

            long_term_records = []
            for i, record in enumerate(long_term_query.all()):
                record_dict = self._serialize_record(record)
                long_term_records.append(record_dict)
                sql_statements.append(
                    self._generate_insert_statement("long_term_memory", record_dict)
                )
                if progress_callback and i % 100 == 0:
                    progress = 70 + int((i / max(long_term_count, 1)) * 25)
                    progress_callback("exporting_long_term_memory", progress, 100)

            # Commit transaction
            sql_statements.append("COMMIT;")

            # Generate checksums
            checksums = {}
            checksums["chat_history"] = self._calculate_checksum(
                chat_records, checksum_algorithm
            )
            checksums["short_term_memory"] = self._calculate_checksum(
                short_term_records, checksum_algorithm
            )
            checksums["long_term_memory"] = self._calculate_checksum(
                long_term_records, checksum_algorithm
            )

            # Write SQL file
            if progress_callback:
                progress_callback("writing", 95, 100)

            temp_path = self._create_temp_path(export_path)
            with open(temp_path, "w", encoding="utf-8") as f:
                f.write("\n".join(sql_statements))

            final_path = self._finalize_artifact(
                temp_path,
                export_path,
                compression,
                encryption_key,
                compresslevel,
            )

            if progress_callback:
                progress_callback("complete", 100, 100)

            return {
                "export_path": str(final_path),
                "format": "sql",
                "record_counts": record_counts,
                "file_size": final_path.stat().st_size,
                "checksums": checksums,
            }

        finally:
            session.close()

    def _generate_insert_statement(
        self, table_name: str, record: Dict[str, Any]
    ) -> str:
        """Generate SQL INSERT statement for a record"""
        columns = []
        values = []

        for key, value in record.items():
            columns.append(key)
            if value is None:
                values.append("NULL")
            elif isinstance(value, (dict, list)):
                # JSON fields
                json_str = json.dumps(value, default=str).replace("'", "''")
                if self.database_type == "postgresql":
                    values.append(f"'{json_str}'::jsonb")
                elif self.database_type == "mysql":
                    values.append(f"'{json_str}'")
                else:
                    values.append(f"'{json_str}'")
            elif isinstance(value, datetime):
                values.append(f"'{value.isoformat()}'")
            elif isinstance(value, bool):
                values.append("1" if value else "0")
            elif isinstance(value, (int, float)):
                values.append(str(value))
            else:
                # Escape single quotes
                escaped_value = str(value).replace("'", "''")
                values.append(f"'{escaped_value}'")

        columns_str = ", ".join(columns)
        values_str = ", ".join(values)

        return f"INSERT INTO {table_name} ({columns_str}) VALUES ({values_str});"


class ImportManager:
    """Manages import operations for Memori memory system"""

    def __init__(self, db_manager: Any):
        """
        Initialize ImportManager.

        Args:
            db_manager: SQLAlchemyDatabaseManager instance
        """
        self.db_manager = db_manager
        self.database_type = db_manager.database_type

    def import_data(
        self,
        import_path: str,
        format: Optional[str] = None,
        target_user_id: Optional[str] = None,
        target_assistant_id: Optional[str] = None,
        merge_strategy: str = "merge",
        validate_only: bool = False,
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
        compression: Optional[str] = None,
        batch_size: int = 500,
        checksum_algorithm: str = "sha256",
        encryption_key: Optional[str] = None,
        resume_token: Optional[str] = None,
        verify_checksums: bool = True,
        audit_logging: bool = True,
    ) -> Dict[str, Any]:
        """
        Import memories from file.

        Args:
            import_path: Path to import file
            format: Import format (auto-detect if None)
            target_user_id: Remap user_id during import
            target_assistant_id: Remap assistant_id during import
            merge_strategy: Merge strategy (replace, merge, skip_duplicates)
            validate_only: Only validate, don't import
            progress_callback: Optional callback for progress updates
            compression: Compression codec if file is compressed
            batch_size: Number of records to insert before flushing session
            checksum_algorithm: Hash algorithm for checksum verification
            encryption_key: Optional key if file is encrypted
            resume_token: Resume import starting at specific table
            verify_checksums: Verify manifest checksums during import
            audit_logging: Emit audit log entries for import events

        Returns:
            Import summary dictionary
        """
        # Auto-detect format if not specified
        if format is None:
            format = self._detect_format(import_path)

        # Validate format
        try:
            import_format = ExportFormat(format.lower())
        except ValueError:
            raise MemoriError(f"Unsupported import format: {format}")

        # Normalize compression hint
        compression_hint = compression.lower() if compression else None
        if compression_hint is None:
            compression_hint = self._detect_compression(import_path)

        if import_path.endswith(".enc") and not encryption_key:
            raise MemoriError(
                "Encrypted export detected (.enc) but no encryption_key was provided"
            )

        # Prepare source file (decompress/decrypt)
        prepared_path, cleanup_paths = self._prepare_import_file(
            import_path, compression_hint, encryption_key
        )

        try:
            # Validate merge strategy
            try:
                strategy = MergeStrategy(merge_strategy.lower())
            except ValueError:
                raise MemoriError(f"Unsupported merge strategy: {merge_strategy}")

            # Pre-import validation
            manifest = self._validate_pre_import(str(prepared_path), import_format)

            if validate_only:
                return {
                    "valid": True,
                    "format": format,
                    "manifest": manifest.to_dict() if manifest else None,
                    "message": "Validation successful",
                }

            if audit_logging:
                logger.info(
                    "[AUDIT] import_started: %s",
                    {
                        "format": import_format.value,
                        "path": str(import_path),
                        "target_user": target_user_id,
                        "target_assistant": target_assistant_id,
                        "compression": compression_hint,
                        "encrypted": bool(encryption_key),
                    },
                )

            # Route to format-specific handler
            if import_format == ExportFormat.JSON:
                summary = self._import_json(
                    str(prepared_path),
                    target_user_id,
                    target_assistant_id,
                    strategy,
                    progress_callback,
                    batch_size,
                    checksum_algorithm,
                    resume_token,
                    verify_checksums,
                    manifest,
                )
            elif import_format == ExportFormat.SQLITE:
                summary = self._import_sqlite(
                    str(prepared_path),
                    target_user_id,
                    target_assistant_id,
                    strategy,
                    progress_callback,
                    batch_size,
                    checksum_algorithm,
                )
            elif import_format == ExportFormat.CSV:
                summary = self._import_csv(
                    str(prepared_path),
                    target_user_id,
                    target_assistant_id,
                    strategy,
                    progress_callback,
                    batch_size,
                    checksum_algorithm,
                )
            elif import_format == ExportFormat.SQL:
                summary = self._import_sql(
                    str(prepared_path),
                    target_user_id,
                    target_assistant_id,
                    strategy,
                    progress_callback,
                    batch_size,
                    checksum_algorithm,
                )

            if audit_logging:
                logger.info(
                    "[AUDIT] import_completed: %s",
                    {
                        "format": import_format.value,
                        "path": str(import_path),
                        "imported": summary.get("imported"),
                        "skipped": summary.get("skipped"),
                    },
                )

            if manifest:
                summary["manifest_diff"] = self._calculate_manifest_diff(
                    manifest, target_user_id, target_assistant_id
                )

            return summary
        finally:
            for temp_path in cleanup_paths:
                try:
                    Path(temp_path).unlink(missing_ok=True)
                except Exception:
                    pass

    def _detect_format(self, import_path: str) -> str:
        """Auto-detect import file format"""
        path = Path(import_path)
        suffix = path.suffix.lower()

        if suffix == ".json":
            return "json"
        elif suffix == ".db" or suffix == ".sqlite":
            return "sqlite"
        elif suffix == ".sql":
            return "sql"
        elif suffix == ".csv" or path.parent.glob("*.csv"):
            return "csv"
        else:
            # Try to read as JSON first
            try:
                with open(import_path, "r") as f:
                    json.load(f)
                return "json"
            except:
                raise MemoriError(f"Could not auto-detect format for: {import_path}")

    def _detect_compression(self, import_path: str) -> Optional[str]:
        """Detect compression codec from file suffix"""
        suffix = Path(import_path).suffix.lower()
        if suffix == ".gz":
            return "gzip"
        return None

    def _prepare_import_file(
        self,
        import_path: str,
        compression: Optional[str],
        encryption_key: Optional[str],
    ) -> Tuple[Path, List[Path]]:
        """Prepare import file by decrypting/decompressing as needed"""
        current_path = Path(import_path)
        cleanup_paths: List[Path] = []

        if encryption_key:
            temp_dec = self._create_temp_file(current_path, suffix=".dec")
            self._decrypt_file(current_path, temp_dec, encryption_key)
            cleanup_paths.append(temp_dec)
            current_path = temp_dec

        if compression:
            temp_decomp = self._create_temp_file(current_path, suffix=".decomp")
            self._decompress_file(current_path, temp_decomp, compression)
            cleanup_paths.append(temp_decomp)
            current_path = temp_decomp

        return current_path, cleanup_paths

    def _create_temp_file(self, base_path: Path, suffix: str) -> Path:
        """Create temp file near working directory"""
        fd, temp_path = tempfile.mkstemp(
            prefix=f"{base_path.stem}_", suffix=suffix
        )
        os.close(fd)
        return Path(temp_path)

    def _decompress_file(
        self, source_path: Path, target_path: Path, compression: str
    ) -> None:
        """Decompress file to temporary location"""
        if compression.lower() != "gzip":
            raise MemoriError(f"Unsupported compression codec: {compression}")
        with gzip.open(source_path, "rb") as src, open(target_path, "wb") as dst:
            shutil.copyfileobj(src, dst)

    def _decrypt_file(
        self, source_path: Path, target_path: Path, encryption_key: str
    ) -> None:
        """Decrypt encrypted export file"""
        try:
            from cryptography.fernet import Fernet
        except ImportError as exc:
            raise MemoriError(
                "File decryption requires the 'cryptography' package"
            ) from exc

        digest = hashlib.sha256(encryption_key.encode("utf-8")).digest()
        key = base64.urlsafe_b64encode(digest)
        cipher = Fernet(key)
        with open(source_path, "rb") as src:
            encrypted = src.read()
        decrypted = cipher.decrypt(encrypted)
        with open(target_path, "wb") as dst:
            dst.write(decrypted)

    def _calculate_checksum(
        self, records: List[Dict[str, Any]], algorithm: str
    ) -> str:
        calculator = ChecksumCalculator(algorithm)
        for record in records:
            calculator.update(record)
        return calculator.hexdigest()

    def _calculate_manifest_diff(
        self,
        manifest: Optional[ExportManifest],
        target_user_id: Optional[str],
        target_assistant_id: Optional[str],
    ) -> Dict[str, Dict[str, Any]]:
        if not manifest:
            return {}

        diff: Dict[str, Dict[str, Any]] = {}
        scope = manifest.export_scope or {}

        source_user = scope.get("user_id")
        if target_user_id and source_user not in (None, target_user_id):
            diff["user_id"] = {"source": source_user, "target": target_user_id}

        source_assistant = scope.get("assistant_id")
        if target_assistant_id and source_assistant not in (None, target_assistant_id):
            diff["assistant_id"] = {
                "source": source_assistant,
                "target": target_assistant_id,
            }

        return diff

    def _validate_pre_import(
        self, import_path: str, format: ExportFormat
    ) -> Optional[ExportManifest]:
        """Validate pre-import conditions"""
        # Check file exists
        if not Path(import_path).exists():
            raise MemoriError(f"Import file not found: {import_path}")

        # Validate format-specific structure
        if format == ExportFormat.JSON:
            return self._validate_json_structure(import_path)
        elif format == ExportFormat.SQLITE:
            return self._validate_sqlite_structure(import_path)
        else:
            return None

    def _validate_json_structure(self, import_path: str) -> Optional[ExportManifest]:
        """Validate JSON export structure"""
        try:
            with open(import_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Check for required tables
            required_tables = ["chat_history", "short_term_memory", "long_term_memory"]
            for table in required_tables:
                if table not in data:
                    logger.warning(f"Missing table in export: {table}")

            # Extract manifest if present
            manifest_data = data.get("_manifest")
            if manifest_data:
                manifest = ExportManifest.from_dict(manifest_data)
                # Validate export version compatibility
                if manifest.export_version != ExportManifest.EXPORT_VERSION:
                    logger.warning(
                        f"Export version mismatch: {manifest.export_version} != {ExportManifest.EXPORT_VERSION}"
                    )
                return manifest

            return None

        except json.JSONDecodeError as e:
            raise MemoriError(f"Invalid JSON file: {e}")

    def _validate_sqlite_structure(self, import_path: str) -> Optional[ExportManifest]:
        """Validate SQLite export structure"""
        from sqlalchemy import create_engine, inspect
        from sqlalchemy.orm import sessionmaker

        try:
            engine = create_engine(f"sqlite:///{import_path}", echo=False)
            inspector = inspect(engine)

            # Check for required tables
            required_tables = ["chat_history", "short_term_memory", "long_term_memory"]
            existing_tables = inspector.get_table_names()

            for table in required_tables:
                if table not in existing_tables:
                    logger.warning(f"Missing table in SQLite export: {table}")

            # Try to extract manifest from metadata table
            if "export_manifest" in existing_tables:
                session = sessionmaker(bind=engine)()
                try:
                    result = session.execute(
                        "SELECT value FROM export_manifest WHERE key = 'manifest'"
                    ).fetchone()
                    if result:
                        manifest_data = json.loads(result[0])
                        return ExportManifest.from_dict(manifest_data)
                finally:
                    session.close()

            return None

        except Exception as e:
            logger.warning(f"Could not validate SQLite structure: {e}")
            return None

    def _import_json(
        self,
        import_path: str,
        target_user_id: Optional[str],
        target_assistant_id: Optional[str],
        merge_strategy: MergeStrategy,
        progress_callback: Optional[Callable[[str, int, int], None]],
        batch_size: int,
        checksum_algorithm: str,
        resume_token: Optional[str],
        verify_checksums: bool,
        manifest: Optional[ExportManifest],
    ) -> Dict[str, Any]:
        """Import from JSON format"""
        session = self.db_manager.get_session()
        try:
            # Load JSON data
            with open(import_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if progress_callback:
                progress_callback("loading", 0, 100)

            manifest_dict = manifest.to_dict() if manifest else data.get("_manifest")

            # Remove manifest to avoid inserting into tables
            data.pop("_manifest", None)

            if verify_checksums and manifest_dict and manifest_dict.get("checksums"):
                mismatches = []
                manifest_checksums = manifest_dict.get("checksums", {})
                computed_chat = self._calculate_checksum(
                    data.get("chat_history", []), checksum_algorithm
                )
                if (
                    manifest_checksums.get("chat_history")
                    and manifest_checksums["chat_history"] != computed_chat
                ):
                    mismatches.append("chat_history")

                computed_short = self._calculate_checksum(
                    data.get("short_term_memory", []), checksum_algorithm
                )
                if (
                    manifest_checksums.get("short_term_memory")
                    and manifest_checksums["short_term_memory"] != computed_short
                ):
                    mismatches.append("short_term_memory")

                computed_long = self._calculate_checksum(
                    data.get("long_term_memory", []), checksum_algorithm
                )
                if (
                    manifest_checksums.get("long_term_memory")
                    and manifest_checksums["long_term_memory"] != computed_long
                ):
                    mismatches.append("long_term_memory")

                if mismatches:
                    raise MemoriError(
                        f"Checksum verification failed for tables: {', '.join(mismatches)}"
                    )

            # Resume handling
            table_order = ["chat_history", "short_term_memory", "long_term_memory"]
            resume_index = 0
            if resume_token and resume_token in table_order:
                resume_index = table_order.index(resume_token)

            summary = {
                "imported": {},
                "skipped": {},
                "errors": [],
                "resume_token": None,
            }

            table_pipeline = [
                (
                    "chat_history",
                    data.get("chat_history", []),
                    self._import_chat_history,
                    "importing_chat_history",
                    10,
                ),
                (
                    "short_term_memory",
                    data.get("short_term_memory", []),
                    self._import_short_term_memory,
                    "importing_short_term_memory",
                    40,
                ),
                (
                    "long_term_memory",
                    data.get("long_term_memory", []),
                    self._import_long_term_memory,
                    "importing_long_term_memory",
                    70,
                ),
            ]

            for index, (table_name, records, handler, label, progress) in enumerate(
                table_pipeline
            ):
                if index < resume_index:
                    summary["imported"][table_name] = 0
                    summary["skipped"][table_name] = len(records)
                    continue

                if progress_callback:
                    progress_callback(label, progress, 100)

                imported, skipped, errors = handler(
                    session,
                    records,
                    target_user_id,
                    target_assistant_id,
                    merge_strategy,
                    batch_size,
                )
                summary["imported"][table_name] = imported
                summary["skipped"][table_name] = skipped
                summary["errors"].extend(errors)
                if index + 1 < len(table_pipeline):
                    summary["resume_token"] = table_pipeline[index + 1][0]
                else:
                    summary["resume_token"] = None

            # Validate relationships
            if progress_callback:
                progress_callback("validating_relationships", 90, 100)

            relationship_errors = self._validate_relationships(session)
            summary["errors"].extend(relationship_errors)

            # Post-import validation
            if progress_callback:
                progress_callback("post_import_validation", 95, 100)

            validation_errors = self._validate_post_import(session)
            summary["errors"].extend(validation_errors)

            session.commit()

            if progress_callback:
                progress_callback("complete", 100, 100)

            return summary

        except Exception as e:
            session.rollback()
            raise MemoriError(f"Import failed: {e}") from e
        finally:
            session.close()

    def _import_chat_history(
        self,
        session: Session,
        records: List[Dict[str, Any]],
        target_user_id: Optional[str],
        target_assistant_id: Optional[str],
        merge_strategy: MergeStrategy,
        batch_size: int,
    ) -> tuple[int, int, List[str]]:
        """Import chat_history records"""
        imported = 0
        skipped = 0
        errors = []
        ops_since_flush = 0
        ops_since_flush = 0

        # Handle replace strategy
        if merge_strategy == MergeStrategy.REPLACE:
            # Delete existing records for target user
            if target_user_id:
                session.query(ChatHistory).filter(
                    ChatHistory.user_id == target_user_id
                ).delete()

        for record in records:
            try:
                # Remap user_id and assistant_id
                if target_user_id:
                    record["user_id"] = target_user_id
                if target_assistant_id:
                    record["assistant_id"] = target_assistant_id

                # Convert datetime strings back to datetime objects
                if "created_at" in record and isinstance(record["created_at"], str):
                    record["created_at"] = datetime.fromisoformat(record["created_at"])
                if "updated_at" in record and isinstance(record["updated_at"], str):
                    record["updated_at"] = datetime.fromisoformat(record["updated_at"])

                # Check if exists
                existing = (
                    session.query(ChatHistory)
                    .filter(ChatHistory.chat_id == record["chat_id"])
                    .first()
                )

                if existing:
                    if merge_strategy == MergeStrategy.SKIP_DUPLICATES:
                        skipped += 1
                        continue
                    elif merge_strategy == MergeStrategy.MERGE:
                        # Update existing
                        for key, value in record.items():
                            setattr(existing, key, value)
                        imported += 1
                        ops_since_flush += 1
                        if ops_since_flush % max(batch_size, 1) == 0:
                            session.flush()
                        continue

                # Create new record
                chat_record = ChatHistory(**record)
                session.add(chat_record)
                imported += 1
                ops_since_flush += 1
                if ops_since_flush % max(batch_size, 1) == 0:
                    session.flush()

            except Exception as e:
                errors.append(f"Error importing chat_history {record.get('chat_id', 'unknown')}: {e}")

        return imported, skipped, errors

    def _import_short_term_memory(
        self,
        session: Session,
        records: List[Dict[str, Any]],
        target_user_id: Optional[str],
        target_assistant_id: Optional[str],
        merge_strategy: MergeStrategy,
        batch_size: int,
    ) -> tuple[int, int, List[str]]:
        """Import short_term_memory records"""
        imported = 0
        skipped = 0
        errors = []
        ops_since_flush = 0

        for record in records:
            try:
                # Remap user_id and assistant_id
                if target_user_id:
                    record["user_id"] = target_user_id
                if target_assistant_id:
                    record["assistant_id"] = target_assistant_id

                # Convert datetime strings
                if "created_at" in record and isinstance(record["created_at"], str):
                    record["created_at"] = datetime.fromisoformat(record["created_at"])
                if "expires_at" in record and isinstance(record["expires_at"], str):
                    record["expires_at"] = datetime.fromisoformat(record["expires_at"])
                if "last_accessed" in record and isinstance(record["last_accessed"], str):
                    record["last_accessed"] = datetime.fromisoformat(record["last_accessed"])

                # Check if exists
                existing = (
                    session.query(ShortTermMemory)
                    .filter(ShortTermMemory.memory_id == record["memory_id"])
                    .first()
                )

                if existing:
                    if merge_strategy == MergeStrategy.SKIP_DUPLICATES:
                        skipped += 1
                        continue
                    elif merge_strategy == MergeStrategy.MERGE:
                        for key, value in record.items():
                            setattr(existing, key, value)
                        imported += 1
                        ops_since_flush += 1
                        if ops_since_flush % max(batch_size, 1) == 0:
                            session.flush()
                        continue

                # Create new record
                memory_record = ShortTermMemory(**record)
                session.add(memory_record)
                imported += 1
                ops_since_flush += 1
                if ops_since_flush % max(batch_size, 1) == 0:
                    session.flush()

            except Exception as e:
                errors.append(
                    f"Error importing short_term_memory {record.get('memory_id', 'unknown')}: {e}"
                )

        return imported, skipped, errors

    def _import_long_term_memory(
        self,
        session: Session,
        records: List[Dict[str, Any]],
        target_user_id: Optional[str],
        target_assistant_id: Optional[str],
        merge_strategy: MergeStrategy,
        batch_size: int,
    ) -> tuple[int, int, List[str]]:
        """Import long_term_memory records"""
        imported = 0
        skipped = 0
        errors = []
        ops_since_flush = 0

        for record in records:
            try:
                # Remap user_id and assistant_id
                if target_user_id:
                    record["user_id"] = target_user_id
                if target_assistant_id:
                    record["assistant_id"] = target_assistant_id

                # Convert datetime strings
                if "created_at" in record and isinstance(record["created_at"], str):
                    record["created_at"] = datetime.fromisoformat(record["created_at"])
                if "last_accessed" in record and isinstance(record["last_accessed"], str):
                    record["last_accessed"] = datetime.fromisoformat(record["last_accessed"])

                # Check if exists
                existing = (
                    session.query(LongTermMemory)
                    .filter(LongTermMemory.memory_id == record["memory_id"])
                    .first()
                )

                if existing:
                    if merge_strategy == MergeStrategy.SKIP_DUPLICATES:
                        skipped += 1
                        continue
                    elif merge_strategy == MergeStrategy.MERGE:
                        for key, value in record.items():
                            setattr(existing, key, value)
                        imported += 1
                        ops_since_flush += 1
                        if ops_since_flush % max(batch_size, 1) == 0:
                            session.flush()
                        continue

                # Create new record
                memory_record = LongTermMemory(**record)
                session.add(memory_record)
                imported += 1
                ops_since_flush += 1
                if ops_since_flush % max(batch_size, 1) == 0:
                    session.flush()

            except Exception as e:
                errors.append(
                    f"Error importing long_term_memory {record.get('memory_id', 'unknown')}: {e}"
                )

        return imported, skipped, errors

    def _validate_relationships(self, session: Session) -> List[str]:
        """Validate relationships after import"""
        errors = []

        # Validate duplicate_of references
        long_term_memories = session.query(LongTermMemory).all()
        for memory in long_term_memories:
            if memory.duplicate_of:
                referenced = (
                    session.query(LongTermMemory)
                    .filter(LongTermMemory.memory_id == memory.duplicate_of)
                    .first()
                )
                if not referenced:
                    errors.append(
                        f"Orphaned duplicate_of reference: {memory.memory_id} -> {memory.duplicate_of}"
                    )

            # Validate related_memories_json
            if memory.related_memories_json:
                if isinstance(memory.related_memories_json, list):
                    for related_id in memory.related_memories_json:
                        referenced = (
                            session.query(LongTermMemory)
                            .filter(LongTermMemory.memory_id == related_id)
                            .first()
                        )
                        if not referenced:
                            errors.append(
                                f"Orphaned related_memory reference: {memory.memory_id} -> {related_id}"
                            )

        return errors

    def _validate_post_import(self, session: Session) -> List[str]:
        """Post-import validation: check data integrity"""
        errors = []

        # Validate foreign key constraints
        try:
            # Check chat_id references in short_term_memory
            orphaned_short_term = (
                session.query(ShortTermMemory)
                .outerjoin(ChatHistory, ShortTermMemory.chat_id == ChatHistory.chat_id)
                .filter(ChatHistory.chat_id.is_(None))
                .filter(ShortTermMemory.chat_id.isnot(None))
                .all()
            )

            for memory in orphaned_short_term:
                errors.append(
                    f"Orphaned chat_id reference in short_term_memory: {memory.memory_id} -> {memory.chat_id}"
                )

        except Exception as e:
            errors.append(f"Error validating foreign keys: {e}")

        # Validate JSON fields are parseable
        try:
            long_term_memories = session.query(LongTermMemory).limit(100).all()
            for memory in long_term_memories:
                # Check processed_data
                if memory.processed_data:
                    if not isinstance(memory.processed_data, (dict, list)):
                        errors.append(
                            f"Invalid processed_data type in long_term_memory: {memory.memory_id}"
                        )

                # Check JSON fields
                json_fields = [
                    "entities_json",
                    "keywords_json",
                    "supersedes_json",
                    "related_memories_json",
                ]
                for field in json_fields:
                    value = getattr(memory, field, None)
                    if value is not None and not isinstance(value, (dict, list)):
                        errors.append(
                            f"Invalid {field} type in long_term_memory: {memory.memory_id}"
                        )

        except Exception as e:
            errors.append(f"Error validating JSON fields: {e}")

        # Validate importance scores are in valid range
        try:
            invalid_scores = (
                session.query(LongTermMemory)
                .filter(
                    (LongTermMemory.importance_score < 0)
                    | (LongTermMemory.importance_score > 1)
                )
                .all()
            )

            for memory in invalid_scores:
                errors.append(
                    f"Invalid importance_score in long_term_memory: {memory.memory_id} = {memory.importance_score}"
                )

        except Exception as e:
            errors.append(f"Error validating importance scores: {e}")

        return errors

    def _import_sqlite(
        self,
        import_path: str,
        target_user_id: Optional[str],
        target_assistant_id: Optional[str],
        merge_strategy: MergeStrategy,
        progress_callback: Optional[Callable[[str, int, int], None]],
        batch_size: int,
        checksum_algorithm: str,
    ) -> Dict[str, Any]:
        """Import from SQLite format"""
        from sqlalchemy import create_engine, inspect
        from sqlalchemy.orm import sessionmaker

        # Create engine for source SQLite database
        source_engine = create_engine(f"sqlite:///{import_path}", echo=False)
        source_session = sessionmaker(bind=source_engine)()

        # Get target session
        target_session = self.db_manager.get_session()

        try:
            # Compare schemas
            source_inspector = inspect(source_engine)
            target_inspector = inspect(self.db_manager.engine)

            if progress_callback:
                progress_callback("comparing_schemas", 5, 100)

            # Get column info for schema comparison
            source_tables = {
                "chat_history": source_inspector.get_columns("chat_history"),
                "short_term_memory": source_inspector.get_columns("short_term_memory"),
                "long_term_memory": source_inspector.get_columns("long_term_memory"),
            }

            target_tables = {
                "chat_history": target_inspector.get_columns("chat_history"),
                "short_term_memory": target_inspector.get_columns("short_term_memory"),
                "long_term_memory": target_inspector.get_columns("long_term_memory"),
            }

            # Check for missing columns (warn but continue)
            for table_name in source_tables:
                source_cols = {col["name"] for col in source_tables[table_name]}
                target_cols = {col["name"] for col in target_tables[table_name]}
                missing_cols = source_cols - target_cols
                if missing_cols:
                    logger.warning(
                        f"Missing columns in target {table_name}: {missing_cols}"
                    )

            summary = {
                "imported": {},
                "skipped": {},
                "errors": [],
            }

            # Import chat_history
            if progress_callback:
                progress_callback("importing_chat_history", 10, 100)

            chat_records = source_session.query(ChatHistory).all()
            imported, skipped, errors = self._import_chat_history_from_orm(
                target_session,
                chat_records,
                target_user_id,
                target_assistant_id,
                merge_strategy,
                batch_size,
            )
            summary["imported"]["chat_history"] = imported
            summary["skipped"]["chat_history"] = skipped
            summary["errors"].extend(errors)

            # Import short_term_memory
            if progress_callback:
                progress_callback("importing_short_term_memory", 40, 100)

            short_term_records = source_session.query(ShortTermMemory).all()
            imported, skipped, errors = self._import_short_term_memory_from_orm(
                target_session,
                short_term_records,
                target_user_id,
                target_assistant_id,
                merge_strategy,
                batch_size,
            )
            summary["imported"]["short_term_memory"] = imported
            summary["skipped"]["short_term_memory"] = skipped
            summary["errors"].extend(errors)

            # Import long_term_memory
            if progress_callback:
                progress_callback("importing_long_term_memory", 70, 100)

            long_term_records = source_session.query(LongTermMemory).all()
            imported, skipped, errors = self._import_long_term_memory_from_orm(
                target_session,
                long_term_records,
                target_user_id,
                target_assistant_id,
                merge_strategy,
                batch_size,
            )
            summary["imported"]["long_term_memory"] = imported
            summary["skipped"]["long_term_memory"] = skipped
            summary["errors"].extend(errors)

            # Validate relationships
            if progress_callback:
                progress_callback("validating_relationships", 90, 100)

            relationship_errors = self._validate_relationships(target_session)
            summary["errors"].extend(relationship_errors)

            # Post-import validation
            if progress_callback:
                progress_callback("post_import_validation", 95, 100)

            validation_errors = self._validate_post_import(target_session)
            summary["errors"].extend(validation_errors)

            # Commit transaction
            target_session.commit()

            if progress_callback:
                progress_callback("complete", 100, 100)

            return summary

        except Exception as e:
            target_session.rollback()
            raise MemoriError(f"SQLite import failed: {e}") from e
        finally:
            source_session.close()
            source_engine.dispose()
            target_session.close()

    def _import_chat_history_from_orm(
        self,
        session: Session,
        records: List[ChatHistory],
        target_user_id: Optional[str],
        target_assistant_id: Optional[str],
        merge_strategy: MergeStrategy,
        batch_size: int,
    ) -> tuple[int, int, List[str]]:
        """Import chat_history records from ORM objects"""
        imported = 0
        skipped = 0
        errors = []

        # Handle replace strategy
        if merge_strategy == MergeStrategy.REPLACE:
            if target_user_id:
                session.query(ChatHistory).filter(
                    ChatHistory.user_id == target_user_id
                ).delete()

        ops_since_flush = 0

        for record in records:
            try:
                # Convert to dict with native Python types
                record_dict = _extract_column_values(record)

                # Remap user_id and assistant_id
                if target_user_id:
                    record_dict["user_id"] = target_user_id
                if target_assistant_id:
                    record_dict["assistant_id"] = target_assistant_id

                # Check if exists
                existing = (
                    session.query(ChatHistory)
                    .filter(ChatHistory.chat_id == record_dict["chat_id"])
                    .first()
                )

                if existing:
                    if merge_strategy == MergeStrategy.SKIP_DUPLICATES:
                        skipped += 1
                        continue
                    elif merge_strategy == MergeStrategy.MERGE:
                        for key, value in record_dict.items():
                            setattr(existing, key, value)
                        imported += 1
                        ops_since_flush += 1
                        if ops_since_flush % max(batch_size, 1) == 0:
                            session.flush()
                        continue

                # Create new record
                chat_record = ChatHistory(**record_dict)
                session.add(chat_record)
                imported += 1
                ops_since_flush += 1
                if ops_since_flush % max(batch_size, 1) == 0:
                    session.flush()

            except Exception as e:
                errors.append(
                    f"Error importing chat_history {record.chat_id if hasattr(record, 'chat_id') else 'unknown'}: {e}"
                )

        return imported, skipped, errors

    def _import_short_term_memory_from_orm(
        self,
        session: Session,
        records: List[ShortTermMemory],
        target_user_id: Optional[str],
        target_assistant_id: Optional[str],
        merge_strategy: MergeStrategy,
        batch_size: int,
    ) -> tuple[int, int, List[str]]:
        """Import short_term_memory records from ORM objects"""
        imported = 0
        skipped = 0
        errors = []

        ops_since_flush = 0

        for record in records:
            try:
                record_dict = _extract_column_values(record)

                # Remap user_id and assistant_id
                if target_user_id:
                    record_dict["user_id"] = target_user_id
                if target_assistant_id:
                    record_dict["assistant_id"] = target_assistant_id

                # Check if exists
                existing = (
                    session.query(ShortTermMemory)
                    .filter(ShortTermMemory.memory_id == record_dict["memory_id"])
                    .first()
                )

                if existing:
                    if merge_strategy == MergeStrategy.SKIP_DUPLICATES:
                        skipped += 1
                        continue
                    elif merge_strategy == MergeStrategy.MERGE:
                        for key, value in record_dict.items():
                            setattr(existing, key, value)
                        imported += 1
                        ops_since_flush += 1
                        if ops_since_flush % max(batch_size, 1) == 0:
                            session.flush()
                        continue

                # Create new record
                memory_record = ShortTermMemory(**record_dict)
                session.add(memory_record)
                imported += 1
                ops_since_flush += 1
                if ops_since_flush % max(batch_size, 1) == 0:
                    session.flush()

            except Exception as e:
                errors.append(
                    f"Error importing short_term_memory {record.memory_id if hasattr(record, 'memory_id') else 'unknown'}: {e}"
                )

        return imported, skipped, errors

    def _import_long_term_memory_from_orm(
        self,
        session: Session,
        records: List[LongTermMemory],
        target_user_id: Optional[str],
        target_assistant_id: Optional[str],
        merge_strategy: MergeStrategy,
        batch_size: int,
    ) -> tuple[int, int, List[str]]:
        """Import long_term_memory records from ORM objects"""
        imported = 0
        skipped = 0
        errors = []

        ops_since_flush = 0

        for record in records:
            try:
                record_dict = _extract_column_values(record)

                # Remap user_id and assistant_id
                if target_user_id:
                    record_dict["user_id"] = target_user_id
                if target_assistant_id:
                    record_dict["assistant_id"] = target_assistant_id

                # Check if exists
                existing = (
                    session.query(LongTermMemory)
                    .filter(LongTermMemory.memory_id == record_dict["memory_id"])
                    .first()
                )

                if existing:
                    if merge_strategy == MergeStrategy.SKIP_DUPLICATES:
                        skipped += 1
                        continue
                    elif merge_strategy == MergeStrategy.MERGE:
                        for key, value in record_dict.items():
                            setattr(existing, key, value)
                        imported += 1
                        ops_since_flush += 1
                        if ops_since_flush % max(batch_size, 1) == 0:
                            session.flush()
                        continue

                # Create new record
                memory_record = LongTermMemory(**record_dict)
                session.add(memory_record)
                imported += 1
                ops_since_flush += 1
                if ops_since_flush % max(batch_size, 1) == 0:
                    session.flush()

            except Exception as e:
                errors.append(
                    f"Error importing long_term_memory {record.memory_id if hasattr(record, 'memory_id') else 'unknown'}: {e}"
                )

        return imported, skipped, errors

    def _import_csv(
        self,
        import_path: str,
        target_user_id: Optional[str],
        target_assistant_id: Optional[str],
        merge_strategy: MergeStrategy,
        progress_callback: Optional[Callable[[str, int, int], None]],
        batch_size: int,
        checksum_algorithm: str,
    ) -> Dict[str, Any]:
        """Import from CSV format"""
        import csv

        # Read manifest file
        manifest_path = Path(import_path)
        if not manifest_path.exists():
            raise MemoriError(f"CSV manifest file not found: {import_path}")

        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)

        csv_files = manifest_data.get("csv_files", [])
        if not csv_files:
            raise MemoriError("No CSV files listed in manifest")

        session = self.db_manager.get_session()
        try:
            summary = {
                "imported": {},
                "skipped": {},
                "errors": [],
            }

            # Import chat_history
            chat_file = None
            for csv_file in csv_files:
                if "chat_history" in csv_file:
                    chat_file = csv_file
                    break

            if chat_file and Path(chat_file).exists():
                if progress_callback:
                    progress_callback("importing_chat_history", 10, 100)

                imported, skipped, errors = self._import_csv_table(
                    session,
                    chat_file,
                    ChatHistory,
                    target_user_id,
                    target_assistant_id,
                    merge_strategy,
                    batch_size,
                )
                summary["imported"]["chat_history"] = imported
                summary["skipped"]["chat_history"] = skipped
                summary["errors"].extend(errors)

            # Import short_term_memory
            short_term_file = None
            for csv_file in csv_files:
                if "short_term_memory" in csv_file:
                    short_term_file = csv_file
                    break

            if short_term_file and Path(short_term_file).exists():
                if progress_callback:
                    progress_callback("importing_short_term_memory", 40, 100)

                imported, skipped, errors = self._import_csv_table(
                    session,
                    short_term_file,
                    ShortTermMemory,
                    target_user_id,
                    target_assistant_id,
                    merge_strategy,
                    batch_size,
                )
                summary["imported"]["short_term_memory"] = imported
                summary["skipped"]["short_term_memory"] = skipped
                summary["errors"].extend(errors)

            # Import long_term_memory
            long_term_file = None
            for csv_file in csv_files:
                if "long_term_memory" in csv_file:
                    long_term_file = csv_file
                    break

            if long_term_file and Path(long_term_file).exists():
                if progress_callback:
                    progress_callback("importing_long_term_memory", 70, 100)

                imported, skipped, errors = self._import_csv_table(
                    session,
                    long_term_file,
                    LongTermMemory,
                    target_user_id,
                    target_assistant_id,
                    merge_strategy,
                    batch_size,
                )
                summary["imported"]["long_term_memory"] = imported
                summary["skipped"]["long_term_memory"] = skipped
                summary["errors"].extend(errors)

            # Validate relationships
            if progress_callback:
                progress_callback("validating_relationships", 90, 100)

            relationship_errors = self._validate_relationships(session)
            summary["errors"].extend(relationship_errors)

            # Post-import validation
            if progress_callback:
                progress_callback("post_import_validation", 95, 100)

            validation_errors = self._validate_post_import(session)
            summary["errors"].extend(validation_errors)

            # Commit transaction
            session.commit()

            if progress_callback:
                progress_callback("complete", 100, 100)

            return summary

        except Exception as e:
            session.rollback()
            raise MemoriError(f"CSV import failed: {e}") from e
        finally:
            session.close()

    def _import_csv_table(
        self,
        session: Session,
        csv_file: str,
        model: Any,
        target_user_id: Optional[str],
        target_assistant_id: Optional[str],
        merge_strategy: MergeStrategy,
        batch_size: int,
    ) -> tuple[int, int, List[str]]:
        """Import a single CSV table"""
        import csv

        imported = 0
        skipped = 0
        errors = []

        # Get primary key column name
        primary_key = None
        for col in model.__table__.columns:
            if col.primary_key:
                primary_key = col.name
                break

        if not primary_key:
            errors.append(f"No primary key found for {model.__tablename__}")
            return imported, skipped, errors

        # Handle replace strategy
        if merge_strategy == MergeStrategy.REPLACE:
            if target_user_id:
                session.query(model).filter(model.user_id == target_user_id).delete()

        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    # Reconstruct JSON fields
                    record_dict = {}
                    for key, value in row.items():
                        if value == "" or value is None:
                            record_dict[key] = None
                        elif key in ["processed_data", "metadata_json", "entities_json", "keywords_json", "supersedes_json", "related_memories_json"]:
                            # Try to parse as JSON
                            try:
                                record_dict[key] = json.loads(value) if value else None
                            except json.JSONDecodeError:
                                record_dict[key] = value  # Keep as string if not valid JSON
                        elif key in ["created_at", "updated_at", "expires_at", "last_accessed"]:
                            # Parse datetime
                            try:
                                record_dict[key] = (
                                    datetime.fromisoformat(value) if value else None
                                )
                            except (ValueError, TypeError):
                                record_dict[key] = None
                        elif key in ["tokens_used", "access_count", "importance_score", "novelty_score", "relevance_score", "actionability_score", "confidence_score"]:
                            # Parse numeric fields
                            try:
                                record_dict[key] = float(value) if value else None
                            except (ValueError, TypeError):
                                record_dict[key] = None
                        elif key in ["is_permanent_context", "is_user_context", "is_preference", "is_skill_knowledge", "is_current_project", "promotion_eligible", "processed_for_duplicates", "conscious_processed"]:
                            # Parse boolean fields
                            record_dict[key] = value.lower() in ["true", "1", "yes"] if value else False
                        else:
                            record_dict[key] = value

                    # Remap user_id and assistant_id
                    if target_user_id:
                        record_dict["user_id"] = target_user_id
                    if target_assistant_id:
                        record_dict["assistant_id"] = target_assistant_id

                    # Check if exists
                    existing = (
                        session.query(model)
                        .filter(getattr(model, primary_key) == record_dict[primary_key])
                        .first()
                    )

                    if existing:
                        if merge_strategy == MergeStrategy.SKIP_DUPLICATES:
                            skipped += 1
                            continue
                        elif merge_strategy == MergeStrategy.MERGE:
                            for key, value in record_dict.items():
                                setattr(existing, key, value)
                            imported += 1
                            ops_since_flush += 1
                            if ops_since_flush % max(batch_size, 1) == 0:
                                session.flush()
                            continue

                    # Create new record
                    record = model(**record_dict)
                    session.add(record)
                    imported += 1
                    ops_since_flush += 1
                    if ops_since_flush % max(batch_size, 1) == 0:
                        session.flush()

                except Exception as e:
                    errors.append(
                        f"Error importing {model.__tablename__} row: {e}"
                    )

        return imported, skipped, errors

    def _import_sql(
        self,
        import_path: str,
        target_user_id: Optional[str],
        target_assistant_id: Optional[str],
        merge_strategy: MergeStrategy,
        progress_callback: Optional[Callable[[str, int, int], None]],
        batch_size: int,
        checksum_algorithm: str,
    ) -> Dict[str, Any]:
        """Import from SQL format"""
        from sqlalchemy import text

        session = self.db_manager.get_session()
        try:
            # Read SQL file
            with open(import_path, "r", encoding="utf-8") as f:
                sql_content = f.read()

            if progress_callback:
                progress_callback("parsing", 10, 100)

            # Parse SQL statements
            statements = self._parse_sql_statements(sql_content)

            summary = {
                "imported": {},
                "skipped": {},
                "errors": [],
            }

            # Track counts
            chat_count = 0
            short_term_count = 0
            long_term_count = 0

            # Execute statements
            total_statements = len(statements)
            for i, statement in enumerate(statements):
                try:
                    # Skip transaction control statements
                    if statement.strip().upper().startswith(("BEGIN", "COMMIT", "START TRANSACTION")):
                        continue

                    # Execute statement
                    session.execute(text(statement))

                    # Track counts
                    if "INSERT INTO chat_history" in statement.upper():
                        chat_count += 1
                    elif "INSERT INTO short_term_memory" in statement.upper():
                        short_term_count += 1
                    elif "INSERT INTO long_term_memory" in statement.upper():
                        long_term_count += 1

                    if progress_callback and i % 100 == 0:
                        progress = 10 + int((i / total_statements) * 80)
                        progress_callback("importing", progress, 100)

                except Exception as e:
                    error_msg = f"Error executing SQL statement: {e}"
                    summary["errors"].append(error_msg)
                    logger.warning(error_msg)
                    # Continue with next statement

            # Apply user_id/assistant_id remapping if needed
            if target_user_id or target_assistant_id:
                if progress_callback:
                    progress_callback("remapping", 90, 100)

                if target_user_id:
                    if chat_count > 0:
                        session.execute(
                            text(
                                "UPDATE chat_history SET user_id = :target WHERE user_id != :target"
                            ),
                            {"target": target_user_id},
                        )
                    if short_term_count > 0:
                        session.execute(
                            text(
                                "UPDATE short_term_memory SET user_id = :target WHERE user_id != :target"
                            ),
                            {"target": target_user_id},
                        )
                    if long_term_count > 0:
                        session.execute(
                            text(
                                "UPDATE long_term_memory SET user_id = :target WHERE user_id != :target"
                            ),
                            {"target": target_user_id},
                        )

                if target_assistant_id:
                    if chat_count > 0:
                        session.execute(
                            text(
                                "UPDATE chat_history SET assistant_id = :target WHERE assistant_id IS NOT NULL"
                            ),
                            {"target": target_assistant_id},
                        )
                    if short_term_count > 0:
                        session.execute(
                            text(
                                "UPDATE short_term_memory SET assistant_id = :target WHERE assistant_id IS NOT NULL"
                            ),
                            {"target": target_assistant_id},
                        )
                    if long_term_count > 0:
                        session.execute(
                            text(
                                "UPDATE long_term_memory SET assistant_id = :target WHERE assistant_id IS NOT NULL"
                            ),
                            {"target": target_assistant_id},
                        )

            # Validate relationships
            if progress_callback:
                progress_callback("validating_relationships", 95, 100)

            relationship_errors = self._validate_relationships(session)
            summary["errors"].extend(relationship_errors)

            # Post-import validation
            if progress_callback:
                progress_callback("post_import_validation", 95, 100)

            validation_errors = self._validate_post_import(session)
            summary["errors"].extend(validation_errors)

            # Commit transaction
            session.commit()

            summary["imported"] = {
                "chat_history": chat_count,
                "short_term_memory": short_term_count,
                "long_term_memory": long_term_count,
            }
            summary["skipped"] = {
                "chat_history": 0,
                "short_term_memory": 0,
                "long_term_memory": 0,
            }

            if progress_callback:
                progress_callback("complete", 100, 100)

            return summary

        except Exception as e:
            session.rollback()
            raise MemoriError(f"SQL import failed: {e}") from e
        finally:
            session.close()

    def _parse_sql_statements(self, sql_content: str) -> List[str]:
        """Parse SQL content into individual statements"""
        statements = []
        current_statement = []
        in_string = False
        string_char = None
        i = 0

        while i < len(sql_content):
            char = sql_content[i]

            # Handle string literals
            if char in ("'", '"') and (i == 0 or sql_content[i - 1] != "\\"):
                if not in_string:
                    in_string = True
                    string_char = char
                elif char == string_char:
                    in_string = False
                    string_char = None
                current_statement.append(char)
                i += 1
                continue

            if not in_string:
                # Check for statement delimiter
                if char == ";" and (i == len(sql_content) - 1 or sql_content[i + 1] in ("\n", "\r", " ")):
                    current_statement.append(char)
                    statement = "".join(current_statement).strip()
                    if statement and not statement.startswith("--"):
                        statements.append(statement)
                    current_statement = []
                    i += 1
                    continue

            current_statement.append(char)
            i += 1

        # Add final statement if any
        if current_statement:
            statement = "".join(current_statement).strip()
            if statement and not statement.startswith("--"):
                statements.append(statement)

        return statements

