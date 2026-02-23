import { useEffect, useState } from "react";
import { getShelves, createShelf, deleteShelf } from "../api/client";
import type { Shelf } from "../types/paper";

interface Props {
  activeShelfId: string | null;
  onSelectShelf: (shelfId: string | null) => void;
}

export default function ShelfSidebar({ activeShelfId, onSelectShelf }: Props) {
  const [shelves, setShelves] = useState<Shelf[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");
  const [newNameJa, setNewNameJa] = useState("");

  const loadShelves = () => {
    getShelves().then(setShelves).catch(console.error);
  };

  useEffect(() => {
    loadShelves();
  }, []);

  const handleCreate = async () => {
    if (!newName.trim()) return;
    try {
      await createShelf(newName.trim(), newNameJa.trim());
      setNewName("");
      setNewNameJa("");
      setShowCreate(false);
      loadShelves();
    } catch (e) {
      console.error(e);
    }
  };

  const handleDelete = async (shelfId: string) => {
    if (!confirm("Delete this shelf? Papers will become unsorted.")) return;
    try {
      await deleteShelf(shelfId);
      if (activeShelfId === shelfId) {
        onSelectShelf(null);
      }
      loadShelves();
    } catch (e) {
      console.error(e);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") handleCreate();
  };

  return (
    <div className="shelf-sidebar">
      <div className="shelf-sidebar-header">
        <span className="shelf-sidebar-title">Shelves</span>
        <button
          className="btn shelf-add-btn"
          onClick={() => setShowCreate(!showCreate)}
          title="Create shelf"
        >
          +
        </button>
      </div>

      <div
        className={`shelf-item ${activeShelfId === null ? "active" : ""}`}
        onClick={() => onSelectShelf(null)}
      >
        <span>All</span>
      </div>

      {shelves.map((s) => (
        <div
          key={s.shelf_id}
          className={`shelf-item ${activeShelfId === s.shelf_id ? "active" : ""}`}
          onClick={() => onSelectShelf(s.shelf_id)}
        >
          <span>{s.name}</span>
          <div className="shelf-item-right">
            <span className="shelf-count">{s.paper_count}</span>
            {!s.is_virtual && (
              <button
                className="shelf-delete-btn"
                onClick={(e) => {
                  e.stopPropagation();
                  handleDelete(s.shelf_id);
                }}
                title="Delete shelf"
              >
                &times;
              </button>
            )}
          </div>
        </div>
      ))}

      {showCreate && (
        <div className="shelf-create-form">
          <input
            placeholder="Name"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            onKeyDown={handleKeyDown}
            autoFocus
          />
          <input
            placeholder="名前 (Ja)"
            value={newNameJa}
            onChange={(e) => setNewNameJa(e.target.value)}
            onKeyDown={handleKeyDown}
          />
          <button className="btn btn-primary btn-sm" onClick={handleCreate}>
            Create
          </button>
        </div>
      )}
    </div>
  );
}
