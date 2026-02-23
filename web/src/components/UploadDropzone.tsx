import { useCallback, useRef, useState } from "react";

interface Props {
  onFilesSelected: (files: File[]) => void;
  disabled?: boolean;
}

export default function UploadDropzone({ onFilesSelected, disabled }: Props) {
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      if (disabled) return;
      const pdfs = Array.from(e.dataTransfer.files).filter((f) =>
        f.name.toLowerCase().endsWith(".pdf")
      );
      if (pdfs.length > 0) {
        onFilesSelected(pdfs);
      }
    },
    [onFilesSelected, disabled]
  );

  const handleClick = () => {
    if (!disabled) inputRef.current?.click();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      onFilesSelected(Array.from(files));
    }
    // Reset so re-selecting the same files triggers onChange
    e.target.value = "";
  };

  return (
    <div
      className={`dropzone ${dragOver ? "drag-over" : ""}`}
      onDragOver={(e) => {
        e.preventDefault();
        setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={handleDrop}
      onClick={handleClick}
      style={disabled ? { opacity: 0.5, cursor: "not-allowed" } : {}}
    >
      <h3>Drag & drop PDFs here</h3>
      <p>or click to browse (multiple files supported)</p>
      <input
        ref={inputRef}
        type="file"
        accept=".pdf"
        multiple
        onChange={handleFileChange}
        style={{ display: "none" }}
      />
    </div>
  );
}
