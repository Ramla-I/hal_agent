"""
Vector Store Configuration Management.

Provides utilities for loading and managing vector store configurations
stored in devices/{manufacturer}/{device}/vector_stores.json files.
"""

import json
import os
from dataclasses import dataclass
from typing import Optional, Dict, Any
from pathlib import Path


@dataclass
class VectorStoreInfo:
    """Information about a single vector store."""
    name: str
    vs_id: Optional[str]
    description: str
    file_id: Optional[str] = None
    created_at: Optional[str] = None
    file_count: Optional[int] = None
    chunk_index_path: Optional[str] = None
    local_path: Optional[str] = None
    local_db_name: Optional[str] = None  # ChromaDB database name for local vector DB

    @property
    def is_uploaded(self) -> bool:
        """Check if this vector store has been uploaded (has a vs_id)."""
        return self.vs_id is not None

    @property
    def is_local(self) -> bool:
        """Check if this is a local vector DB entry."""
        return self.local_db_name is not None


@dataclass
class DeviceVectorStores:
    """All vector store configurations for a device."""
    device_name: str
    manufacturer: str
    vector_stores: Dict[str, VectorStoreInfo]
    default: str
    _device_dir: str = ""

    def get(self, name: str) -> Optional[VectorStoreInfo]:
        """Get a vector store by name."""
        return self.vector_stores.get(name)

    def get_default(self) -> Optional[VectorStoreInfo]:
        """Get the default vector store."""
        return self.vector_stores.get(self.default)

    def get_vs_id(self, name: str) -> Optional[str]:
        """Get the vs_id for a named vector store."""
        vs = self.vector_stores.get(name)
        return vs.vs_id if vs else None

    def get_chunk_index_path(self, name: str) -> Optional[str]:
        """Get the full chunk index path for a named vector store."""
        vs = self.vector_stores.get(name)
        if vs and vs.chunk_index_path:
            return os.path.join(self._device_dir, vs.chunk_index_path)
        return None

    def get_local_db_name(self, name: str) -> Optional[str]:
        """Get the local ChromaDB database name for a named vector store."""
        vs = self.vector_stores.get(name)
        return vs.local_db_name if vs else None

    def list_available(self) -> list:
        """List all vector stores that have been uploaded (have vs_id)."""
        return [name for name, vs in self.vector_stores.items() if vs.is_uploaded]

    def list_all(self) -> list:
        """List all vector store names."""
        return list(self.vector_stores.keys())


def load_vector_stores(device_dir: str) -> DeviceVectorStores:
    """
    Load vector store configuration for a device.

    Args:
        device_dir: Path to device directory (e.g., 'devices/stm/rm0041')

    Returns:
        DeviceVectorStores object with all configurations

    Raises:
        FileNotFoundError: If vector_stores.json doesn't exist
    """
    config_path = os.path.join(device_dir, "vector_stores.json")

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Vector store config not found: {config_path}")

    with open(config_path, 'r') as f:
        data = json.load(f)

    # Parse vector stores
    vector_stores = {}
    for name, info in data.get("vector_stores", {}).items():
        vector_stores[name] = VectorStoreInfo(
            name=name,
            vs_id=info.get("vs_id"),
            description=info.get("description", ""),
            file_id=info.get("file_id"),
            created_at=info.get("created_at"),
            file_count=info.get("file_count"),
            chunk_index_path=info.get("chunk_index_path"),
            local_path=info.get("local_path"),
            local_db_name=info.get("local_db_name"),
        )

    return DeviceVectorStores(
        device_name=data.get("device_name", ""),
        manufacturer=data.get("manufacturer", ""),
        vector_stores=vector_stores,
        default=data.get("default", ""),
        _device_dir=device_dir,
    )


def save_vector_stores(device_dir: str, config: DeviceVectorStores) -> str:
    """
    Save vector store configuration for a device.

    Args:
        device_dir: Path to device directory
        config: DeviceVectorStores object to save

    Returns:
        Path to saved config file
    """
    config_path = os.path.join(device_dir, "vector_stores.json")

    data = {
        "device_name": config.device_name,
        "manufacturer": config.manufacturer,
        "vector_stores": {},
        "default": config.default,
    }

    for name, vs in config.vector_stores.items():
        vs_data = {
            "vs_id": vs.vs_id,
            "description": vs.description,
        }
        if vs.file_id:
            vs_data["file_id"] = vs.file_id
        if vs.created_at:
            vs_data["created_at"] = vs.created_at
        if vs.file_count:
            vs_data["file_count"] = vs.file_count
        if vs.chunk_index_path:
            vs_data["chunk_index_path"] = vs.chunk_index_path
        if vs.local_path:
            vs_data["local_path"] = vs.local_path
        if vs.local_db_name:
            vs_data["local_db_name"] = vs.local_db_name

        data["vector_stores"][name] = vs_data

    with open(config_path, 'w') as f:
        json.dump(data, f, indent=2)

    return config_path


def update_vector_store(
    device_dir: str,
    name: str,
    vs_id: Optional[str] = None,
    description: Optional[str] = None,
    file_count: Optional[int] = None,
    chunk_index_path: Optional[str] = None,
    created_at: Optional[str] = None,
) -> DeviceVectorStores:
    """
    Update a vector store entry and save the config.

    Args:
        device_dir: Path to device directory
        name: Name of the vector store to update
        vs_id: New vs_id (if uploading)
        description: Updated description
        file_count: Number of files uploaded
        chunk_index_path: Path to chunks_index.csv
        created_at: Creation date

    Returns:
        Updated DeviceVectorStores object
    """
    config = load_vector_stores(device_dir)

    if name not in config.vector_stores:
        # Create new entry
        config.vector_stores[name] = VectorStoreInfo(
            name=name,
            vs_id=vs_id,
            description=description or "",
        )
    else:
        vs = config.vector_stores[name]
        if vs_id is not None:
            vs.vs_id = vs_id
        if description is not None:
            vs.description = description
        if file_count is not None:
            vs.file_count = file_count
        if chunk_index_path is not None:
            vs.chunk_index_path = chunk_index_path
        if created_at is not None:
            vs.created_at = created_at

    save_vector_stores(device_dir, config)
    return config


# Cache for loaded configs
_config_cache: Dict[str, DeviceVectorStores] = {}


def get_vector_stores(device_dir: str, use_cache: bool = True) -> DeviceVectorStores:
    """
    Get vector store configuration with optional caching.

    Args:
        device_dir: Path to device directory
        use_cache: Whether to use cached config

    Returns:
        DeviceVectorStores object
    """
    device_dir = os.path.abspath(device_dir)

    if use_cache and device_dir in _config_cache:
        return _config_cache[device_dir]

    config = load_vector_stores(device_dir)

    if use_cache:
        _config_cache[device_dir] = config

    return config


def clear_cache():
    """Clear the config cache."""
    _config_cache.clear()


if __name__ == "__main__":
    # Test loading
    import sys

    if len(sys.argv) < 2:
        print("Usage: python vector_store_config.py <device_dir>")
        sys.exit(1)

    device_dir = sys.argv[1]
    config = load_vector_stores(device_dir)

    print(f"Device: {config.device_name} ({config.manufacturer})")
    print(f"Default: {config.default}")
    print(f"\nVector Stores:")
    for name in config.list_all():
        vs = config.get(name)
        status = "uploaded" if vs.is_uploaded else "local only"
        print(f"  {name}: {vs.vs_id or 'N/A'} ({status})")
        print(f"    Description: {vs.description}")
        if vs.file_count:
            print(f"    Files: {vs.file_count}")

    print(f"\nAvailable (uploaded): {config.list_available()}")
