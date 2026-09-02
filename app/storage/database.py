"""Small SQLite control-plane store with tenant-scoped queries."""

import json
import sqlite3
import threading
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


class ControlPlaneStore:
    """Persist authored resources; every public query requires a tenant id."""

    def __init__(self, database_path: str) -> None:
        if database_path != ":memory:":
            Path(database_path).parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(database_path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        self._migrate()

    def close(self) -> None:
        self._connection.close()

    def _migrate(self) -> None:
        with self._connection:
            self._connection.executescript(
                """
                PRAGMA foreign_keys = ON;
                CREATE TABLE IF NOT EXISTS organizations (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    email TEXT,
                    display_name TEXT,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS roles (
                    organization_id TEXT NOT NULL REFERENCES organizations(id),
                    name TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (organization_id, name)
                );
                CREATE TABLE IF NOT EXISTS memberships (
                    organization_id TEXT NOT NULL REFERENCES organizations(id),
                    user_id TEXT NOT NULL REFERENCES users(id),
                    roles TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (organization_id, user_id)
                );
                CREATE TABLE IF NOT EXISTS blueprints (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    display_name TEXT NOT NULL,
                    version TEXT NOT NULL,
                    stage TEXT NOT NULL DEFAULT 'draft',
                    content TEXT NOT NULL,
                    format TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE (tenant_id, name)
                );
                CREATE TABLE IF NOT EXISTS blueprint_versions (
                    id TEXT PRIMARY KEY,
                    blueprint_id TEXT NOT NULL REFERENCES blueprints(id),
                    tenant_id TEXT NOT NULL,
                    version TEXT NOT NULL,
                    content TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    stage TEXT NOT NULL DEFAULT 'draft',
                    created_at TEXT NOT NULL,
                    UNIQUE (blueprint_id, version)
                );
                CREATE TABLE IF NOT EXISTS knowledge_documents (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    allowed_roles TEXT NOT NULL,
                    citation_base TEXT NOT NULL,
                    version INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS module_installations (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    module_key TEXT NOT NULL,
                    rag_config TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE (tenant_id, module_key)
                );
                CREATE TABLE IF NOT EXISTS evaluation_runs (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    blueprint_id TEXT NOT NULL REFERENCES blueprints(id),
                    blueprint_version TEXT NOT NULL,
                    score REAL NOT NULL,
                    passed INTEGER NOT NULL,
                    report_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS deployments (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    blueprint_id TEXT NOT NULL REFERENCES blueprints(id),
                    blueprint_version TEXT NOT NULL,
                    environment TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )

    def provision_identity(
        self,
        *,
        organization_id: str,
        user_id: str,
        roles: tuple[str, ...],
        organization_name: str | None = None,
        email: str | None = None,
        display_name: str | None = None,
    ) -> None:
        """Provision a local/test identity; production uses an admin or SCIM workflow."""

        now = utc_now()
        with self._lock, self._connection:
            self._connection.execute(
                """INSERT INTO organizations (id, name, created_at) VALUES (?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET name=excluded.name""",
                (organization_id, organization_name or organization_id, now),
            )
            self._connection.execute(
                """INSERT INTO users (id, email, display_name, created_at) VALUES (?, ?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET
                     email=COALESCE(excluded.email, users.email),
                     display_name=COALESCE(excluded.display_name, users.display_name)""",
                (user_id, email, display_name, now),
            )
            for role in roles:
                self._connection.execute(
                    """INSERT INTO roles (organization_id, name, created_at) VALUES (?, ?, ?)
                       ON CONFLICT(organization_id, name) DO NOTHING""",
                    (organization_id, role, now),
                )
            self._connection.execute(
                """INSERT INTO memberships
                     (organization_id, user_id, roles, status, created_at, updated_at)
                   VALUES (?, ?, ?, 'active', ?, ?)
                   ON CONFLICT(organization_id, user_id) DO UPDATE SET
                     roles=excluded.roles, status='active', updated_at=excluded.updated_at""",
                (organization_id, user_id, json.dumps(roles), now, now),
            )

    def get_membership(self, organization_id: str, user_id: str) -> dict[str, object]:
        row = self._connection.execute(
            """SELECT organization_id, user_id, roles, status, created_at, updated_at
               FROM memberships WHERE organization_id = ? AND user_id = ?""",
            (organization_id, user_id),
        ).fetchone()
        if row is None:
            raise KeyError((organization_id, user_id))
        membership = dict(row)
        membership["roles"] = json.loads(str(membership["roles"]))
        return membership

    def save_blueprint(
        self,
        *,
        tenant_id: str,
        name: str,
        display_name: str,
        version: str,
        content: str,
        source_format: str,
        content_hash: str,
    ) -> dict[str, object]:
        now = utc_now()
        with self._lock, self._connection:
            existing = self._connection.execute(
                "SELECT id, created_at FROM blueprints WHERE tenant_id = ? AND name = ?",
                (tenant_id, name),
            ).fetchone()
            blueprint_id = existing["id"] if existing else str(uuid4())
            created_at = existing["created_at"] if existing else now
            self._connection.execute(
                """
                INSERT INTO blueprints
                    (id, tenant_id, name, display_name, version, stage, content, format,
                     created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 'draft', ?, ?, ?, ?)
                ON CONFLICT(tenant_id, name) DO UPDATE SET
                    display_name=excluded.display_name, version=excluded.version,
                    content=excluded.content, format=excluded.format, updated_at=excluded.updated_at
                """,
                (
                    blueprint_id,
                    tenant_id,
                    name,
                    display_name,
                    version,
                    content,
                    source_format,
                    created_at,
                    now,
                ),
            )
            self._connection.execute(
                """
                INSERT INTO blueprint_versions
                    (id, blueprint_id, tenant_id, version, content, content_hash, stage, created_at)
                VALUES (?, ?, ?, ?, ?, ?, 'draft', ?)
                ON CONFLICT(blueprint_id, version) DO UPDATE SET
                    content=excluded.content, content_hash=excluded.content_hash
                """,
                (str(uuid4()), blueprint_id, tenant_id, version, content, content_hash, now),
            )
        return self.get_blueprint(tenant_id, blueprint_id)

    def list_blueprints(self, tenant_id: str) -> list[dict[str, object]]:
        rows = self._connection.execute(
            "SELECT * FROM blueprints WHERE tenant_id = ? ORDER BY updated_at DESC",
            (tenant_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def get_blueprint(self, tenant_id: str, blueprint_id: str) -> dict[str, object]:
        row = self._connection.execute(
            "SELECT * FROM blueprints WHERE tenant_id = ? AND id = ?",
            (tenant_id, blueprint_id),
        ).fetchone()
        if row is None:
            raise KeyError(blueprint_id)
        return dict(row)

    def list_versions(self, tenant_id: str, blueprint_id: str) -> list[dict[str, object]]:
        rows = self._connection.execute(
            """SELECT id, blueprint_id, tenant_id, version, content_hash, stage, created_at
               FROM blueprint_versions WHERE tenant_id = ? AND blueprint_id = ?
               ORDER BY created_at DESC""",
            (tenant_id, blueprint_id),
        ).fetchall()
        return [dict(row) for row in rows]

    def add_knowledge_document(
        self,
        *,
        tenant_id: str,
        source_id: str,
        title: str,
        content: str,
        allowed_roles: tuple[str, ...],
        citation_base: str,
    ) -> dict[str, object]:
        document_id = str(uuid4())
        now = utc_now()
        with self._lock, self._connection:
            self._connection.execute(
                """INSERT INTO knowledge_documents
                   (id, tenant_id, source_id, title, content, allowed_roles,
                    citation_base, version, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)""",
                (
                    document_id,
                    tenant_id,
                    source_id,
                    title,
                    content,
                    json.dumps(allowed_roles, ensure_ascii=False),
                    citation_base,
                    now,
                ),
            )
        return self.get_knowledge_document(tenant_id, document_id)

    def get_knowledge_document(self, tenant_id: str, document_id: str) -> dict[str, object]:
        row = self._connection.execute(
            "SELECT * FROM knowledge_documents WHERE tenant_id = ? AND id = ?",
            (tenant_id, document_id),
        ).fetchone()
        if row is None:
            raise KeyError(document_id)
        item = dict(row)
        item["allowed_roles"] = json.loads(str(item["allowed_roles"]))
        return item

    def list_knowledge_documents(self, tenant_id: str) -> list[dict[str, object]]:
        rows = self._connection.execute(
            "SELECT id FROM knowledge_documents WHERE tenant_id = ? ORDER BY created_at DESC",
            (tenant_id,),
        ).fetchall()
        return [self.get_knowledge_document(tenant_id, row["id"]) for row in rows]

    def upsert_module_installation(
        self, tenant_id: str, module_key: str, rag_config: dict[str, object]
    ) -> dict[str, object]:
        now = utc_now()
        with self._lock, self._connection:
            existing = self._connection.execute(
                """SELECT id, created_at FROM module_installations
                   WHERE tenant_id = ? AND module_key = ?""",
                (tenant_id, module_key),
            ).fetchone()
            installation_id = str(existing["id"]) if existing else str(uuid4())
            created_at = str(existing["created_at"]) if existing else now
            self._connection.execute(
                """INSERT INTO module_installations
                   (id, tenant_id, module_key, rag_config, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(tenant_id, module_key) DO UPDATE SET
                     rag_config=excluded.rag_config, updated_at=excluded.updated_at""",
                (
                    installation_id,
                    tenant_id,
                    module_key,
                    json.dumps(rag_config, ensure_ascii=False),
                    created_at,
                    now,
                ),
            )
        return self.get_module_installation(tenant_id, module_key)

    def get_module_installation(self, tenant_id: str, module_key: str) -> dict[str, object]:
        row = self._connection.execute(
            "SELECT * FROM module_installations WHERE tenant_id = ? AND module_key = ?",
            (tenant_id, module_key),
        ).fetchone()
        if row is None:
            raise KeyError(module_key)
        item = dict(row)
        item["rag"] = json.loads(str(item.pop("rag_config")))
        return item

    def list_module_installations(self, tenant_id: str) -> list[dict[str, object]]:
        rows = self._connection.execute(
            """SELECT module_key FROM module_installations
               WHERE tenant_id = ? ORDER BY updated_at DESC""",
            (tenant_id,),
        ).fetchall()
        return [self.get_module_installation(tenant_id, str(row["module_key"])) for row in rows]

    def remove_module_installation(self, tenant_id: str, module_key: str) -> None:
        with self._lock, self._connection:
            cursor = self._connection.execute(
                "DELETE FROM module_installations WHERE tenant_id = ? AND module_key = ?",
                (tenant_id, module_key),
            )
        if cursor.rowcount == 0:
            raise KeyError(module_key)

    def save_evaluation(
        self,
        tenant_id: str,
        blueprint_id: str,
        blueprint_version: str,
        report: dict[str, object],
    ) -> dict[str, object]:
        evaluation_id = str(uuid4())
        now = utc_now()
        with self._lock, self._connection:
            self._connection.execute(
                """INSERT INTO evaluation_runs
                   (id, tenant_id, blueprint_id, blueprint_version, score,
                    passed, report_json, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    evaluation_id,
                    tenant_id,
                    blueprint_id,
                    blueprint_version,
                    report["score"],
                    int(bool(report["passed"])),
                    json.dumps(report, ensure_ascii=False),
                    now,
                ),
            )
        return {
            "id": evaluation_id,
            "tenant_id": tenant_id,
            "blueprint_id": blueprint_id,
            "blueprint_version": blueprint_version,
            "score": report["score"],
            "passed": bool(report["passed"]),
            "report": report,
            "created_at": now,
        }

    def list_evaluations(self, tenant_id: str, blueprint_id: str) -> list[dict[str, object]]:
        rows = self._connection.execute(
            """SELECT * FROM evaluation_runs
               WHERE tenant_id = ? AND blueprint_id = ? ORDER BY created_at DESC""",
            (tenant_id, blueprint_id),
        ).fetchall()
        return [
            {
                **dict(row),
                "passed": bool(row["passed"]),
                "report": json.loads(row["report_json"]),
            }
            for row in rows
        ]

    def publish(self, tenant_id: str, blueprint_id: str, environment: str) -> dict[str, object]:
        blueprint = self.get_blueprint(tenant_id, blueprint_id)
        evaluation = self._connection.execute(
            """SELECT * FROM evaluation_runs WHERE tenant_id = ? AND blueprint_id = ?
               AND blueprint_version = ? ORDER BY created_at DESC LIMIT 1""",
            (tenant_id, blueprint_id, blueprint["version"]),
        ).fetchone()
        if evaluation is None or not bool(evaluation["passed"]):
            raise PermissionError("latest blueprint version has no passing evaluation")
        deployment_id = str(uuid4())
        now = utc_now()
        with self._lock, self._connection:
            self._connection.execute(
                """INSERT INTO deployments
                   (id, tenant_id, blueprint_id, blueprint_version, environment, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    deployment_id,
                    tenant_id,
                    blueprint_id,
                    blueprint["version"],
                    environment,
                    now,
                ),
            )
            self._connection.execute(
                "UPDATE blueprints SET stage = ?, updated_at = ? WHERE id = ? AND tenant_id = ?",
                (environment, now, blueprint_id, tenant_id),
            )
        return {
            "id": deployment_id,
            "tenant_id": tenant_id,
            "blueprint_id": blueprint_id,
            "blueprint_version": blueprint["version"],
            "environment": environment,
            "created_at": now,
        }
