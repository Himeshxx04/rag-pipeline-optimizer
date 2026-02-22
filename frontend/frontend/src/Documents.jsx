import { useEffect, useState } from "react";
import { fetchDocuments, uploadDocument } from "./api";
function getStatusStyle(status) {
  switch (status) {
    case "uploaded":
      return {
        backgroundColor: "#1f2937",
        color: "#93c5fd",
      };
    case "processing":
      return {
        backgroundColor: "#3f2f1f",
        color: "#facc15",
      };
    case "embedded":
      return {
        backgroundColor: "#064e3b",
        color: "#6ee7b7",
      };
    default:
      return {
        backgroundColor: "#1f2937",
        color: "#9ca3af",
      };
  }
}


function Documents() {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadMsg, setUploadMsg] = useState("");

  const loadDocuments = () => {
    setLoading(true);
    fetchDocuments()
      .then((data) => setDocuments(data))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadDocuments();
  }, []);

  const handleUpload = async () => {
    if (!selectedFile) {
      setUploadMsg("Please select a file");
      return;
    }

    try {
      setUploadMsg("Uploading...");
      await uploadDocument(selectedFile);
      setUploadMsg("Upload successful");
      setSelectedFile(null);
      loadDocuments(); // refresh list
    } catch {
      setUploadMsg("Upload failed");
    }
  };

  return (
    <section>
      {/* Upload Card */}
      <div
        style={{
          backgroundColor: "#161616",
          borderRadius: "8px",
          padding: "16px",
          marginBottom: "24px",
        }}
      >
        <h2 style={{ marginBottom: "12px" }}>Upload Document</h2>

        <input
          type="file"
          onChange={(e) => setSelectedFile(e.target.files[0])}
        />

        <button
          onClick={handleUpload}
          style={{
            marginLeft: "12px",
            padding: "6px 12px",
            backgroundColor: "#2563eb",
            color: "#fff",
            border: "none",
            borderRadius: "4px",
            cursor: "pointer",
          }}
        >
          Upload
        </button>

        {uploadMsg && (
          <p style={{ marginTop: "8px", color: "#aaa" }}>
            {uploadMsg}
          </p>
        )}
      </div>

      {/* Documents List */}
      <h2 style={{ fontSize: "24px", marginBottom: "16px" }}>
        Documents
      </h2>

      {loading ? (
        <p style={{ color: "#999" }}>Loading documents...</p>
      ) : documents.length === 0 ? (
        <p style={{ color: "#999" }}>
          No documents uploaded yet.
        </p>
      ) : (
        <div
          style={{
            backgroundColor: "#161616",
            borderRadius: "8px",
            padding: "16px",
          }}
        >
          {documents.map((doc) => (
            <div
              key={doc.doc_id}
              style={{
                display: "flex",
                justifyContent: "space-between",
                padding: "16px 0",
                borderBottom: "1px solid #222",
                alignItems: "center",

              }}
            >
              <div>
                <div style={{ fontWeight: 500 }}>
                  {doc.filename}
                </div>
                <div style={{ fontSize: "12px", color: "#777" }}>
                  {doc.doc_id}
                </div>
              </div>

                      <span
              style={{
                padding: "4px 12px",
                borderRadius: "999px",
                fontSize: "12px",
                fontWeight: 500,
                alignSelf: "center",
                ...getStatusStyle(doc.status),
              }}
          >
            {doc.status}
          </span>

            </div>
          ))}
        </div>
      )}
    </section>
  );
}

export default Documents;
