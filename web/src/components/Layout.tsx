import type { ReactNode } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useState } from "react";

export default function Layout({ children }: { children: ReactNode }) {
  const location = useLocation();
  const navigate = useNavigate();
  const [searchValue, setSearchValue] = useState("");

  const handleSearch = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && searchValue.trim()) {
      navigate(`/library?search=${encodeURIComponent(searchValue.trim())}`);
    }
  };

  return (
    <div className="layout">
      <nav className="nav">
        <Link to="/library" className="nav-logo">
          Paper Shelf
        </Link>
        <div className="nav-links">
          <Link
            to="/library"
            className={`nav-link ${location.pathname === "/library" ? "active" : ""}`}
          >
            Shelf
          </Link>
          <Link
            to="/upload"
            className={`nav-link ${location.pathname === "/upload" ? "active" : ""}`}
          >
            Upload
          </Link>
        </div>
        <div className="nav-search">
          <input
            type="text"
            className="search-input"
            placeholder="Search papers..."
            value={searchValue}
            onChange={(e) => setSearchValue(e.target.value)}
            onKeyDown={handleSearch}
          />
        </div>
      </nav>
      <main className="main-content">{children}</main>
    </div>
  );
}
