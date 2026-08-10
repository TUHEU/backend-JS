"""
Shared building blocks (Repository pattern + Template Method) used by
every microservice in the GlobeTrotter Phase 2 architecture. Each
service keeps its own copy of this file on purpose -- microservices
should not share a runtime library, only a design convention.
"""
import json
import os
import threading


class JsonRepository:
    """Template Method / Repository pattern.

    Encapsulates *how* records are persisted (a JSON file on disk) so
    that service classes never touch the filesystem directly. Concrete
    repositories (UserRepository, ItineraryRepository, ...) only need
    to say *what* a record's id field is called -- everything else
    (read, write, add, update, delete) is implemented once here.
    """

    def __init__(self, file_path, id_field="id"):
        self._file_path = file_path
        self._id_field = id_field
        self._lock = threading.Lock()
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        if not os.path.exists(file_path):
            self._write_all([])

    # -- low level ---------------------------------------------------
    def _read_all(self):
        with open(self._file_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            return json.loads(content) if content else []

    def _write_all(self, records):
        tmp_path = self._file_path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, self._file_path)

    # -- CRUD used by every subclass ----------------------------------
    def all(self):
        with self._lock:
            return self._read_all()

    def find(self, predicate):
        return next((r for r in self.all() if predicate(r)), None)

    def find_by_id(self, record_id):
        return self.find(lambda r: r.get(self._id_field) == record_id)

    def filter(self, predicate):
        return [r for r in self.all() if predicate(r)]

    def add(self, record):
        with self._lock:
            records = self._read_all()
            records.append(record)
            self._write_all(records)
        return record

    def update(self, record_id, mutate_fn):
        """mutate_fn receives the record dict and mutates it in place."""
        with self._lock:
            records = self._read_all()
            record = next((r for r in records if r.get(self._id_field) == record_id), None)
            if record is None:
                return None
            mutate_fn(record)
            self._write_all(records)
            return record

    def delete(self, record_id):
        with self._lock:
            records = self._read_all()
            remaining = [r for r in records if r.get(self._id_field) != record_id]
            deleted = len(remaining) != len(records)
            if deleted:
                self._write_all(remaining)
            return deleted


class ServiceError(Exception):
    """Base class for business-rule failures -- carries an HTTP status
    so the Flask layer can translate it without knowing the reason."""

    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
