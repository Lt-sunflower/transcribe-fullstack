import { useCallback, useEffect, useState } from 'react';
import './App.css';

function App() {

  const API_BASE = "http://localhost:8000";

  const [uploading, setUploading] = useState(false);
  const [records, setRecords] = useState([]);
  const [search, setSearch] = useState("");

  const fetchRecords = useCallback(async () => {
    try{
      const result = await fetch(`${API_BASE}/transcriptions`)
      const data = await result.json()
      setRecords(data)
    } catch {
      console.error("Failed to fetch records")
    }
  }, [])

  useEffect(() => {
    fetchRecords()
  }, [fetchRecords])

  const handleUpload = async (e) => {
    const files = Array.from(e.target.files)

    if (!files.length) return;

    setUploading(true);

    const form = new FormData();
    files.forEach(file => form.append("files", file))


    try {
      const res = await fetch(`${API_BASE}/transcribe`, { method: "POST", body: form });
      const data = await res.json();

      if (res.status === 200) {
        alert(`✓ ${data.results.length} file(s) transcribed successfully:\n${data.results.map(f => f.filename).join("\n")}`);
        fetchRecords();
      } else if (res.status === 500) {
        alert(`✗ ${data.errors.length} file(s) failed:\n${data.errors.map(f => `${f.filename}: ${f.error}`).join("\n")}`);
      } else if (res.status === 207) {
        alert(
          `✓ ${data.results.length} file(s) transcribed successfully:\n${data.results.map(f => f.filename).join("\n")}` +
          `\n\n✗ ${data.errors.length} file(s) failed:\n${data.errors.map(f => `${f.filename}: ${f.error}`).join("\n")}`
        );
        fetchRecords();
      }
    } catch (e) {
      alert(`✗ Unexpected error: ${e.message}`);
    } finally {
      setUploading(false);
    }
  }

  const handleSearch = async () => {
    if (!search.trim()) return fetchRecords();
    try {
      const res = await fetch(`${API_BASE}/search?filename=${encodeURIComponent(search)}`);
      const data = await res.json();
      setRecords(data);
    } catch {
      console.error("Search failed");
    }
  }


  return (
    <div className="container">
      <div className="topbar">
        <div className="search-group">
          <input
            className="search-input"
            type="text"
            placeholder="Search by filename..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            onKeyDown={e => e.key === "Enter" && handleSearch()}
          />
          <button className="btn-search" onClick={handleSearch}>Search</button>
        </div>

        <div>
          <input type="file" accept="audio/*" id="file-input" onChange={handleUpload} disabled={uploading} multiple/>
          <label htmlFor="file-input" className="btn-upload">
            {uploading ? "Uploading..." : "Upload Audio"}
          </label>
        </div>
      </div>

      {/* {status && <p className={`status ${status.ok ? "ok" : "err"}`}>{status.msg}</p>} */}
      <table>
        <thead>
          <tr>
            <th>#</th>
            <th>Filename</th>
            <th>Transcription</th>
            <th>Created</th>
          </tr>
        </thead>
        <tbody>
          {records.length === 0 ? (
            <tr><td colSpan={4}>No records found</td></tr>
          ) : (
            records.map((r, i) => (
              <tr key={r.id}>
                <td>{i + 1}</td>
                <td>{r.filename}</td>
                <td className="transcript-cell">{r.transcript}</td>
                <td>{r.created_on ? new Date(r.created_on).toLocaleString() : "—"}</td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>    
  );
}

export default App;
