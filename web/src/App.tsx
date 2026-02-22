import { Routes, Route, Navigate } from "react-router-dom";
import Layout from "./components/Layout";
import LibraryPage from "./pages/LibraryPage";
import PaperDetailPage from "./pages/PaperDetailPage";
import UploadPage from "./pages/UploadPage";

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Navigate to="/library" replace />} />
        <Route path="/library" element={<LibraryPage />} />
        <Route path="/papers/:id" element={<PaperDetailPage />} />
        <Route path="/upload" element={<UploadPage />} />
      </Routes>
    </Layout>
  );
}
