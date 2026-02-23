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
          <svg
            width="22"
            height="22"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            style={{ marginRight: 6, verticalAlign: -3 }}
          >
            <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20" />
            <path d="M8 7h6" />
            <path d="M8 11h4" />
          </svg>
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
