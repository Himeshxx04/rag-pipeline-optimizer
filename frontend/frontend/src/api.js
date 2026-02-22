export async function checkBackendHealth() {
  const response = await fetch("http://127.0.0.1:8000/health");
  if (!response.ok) {
    throw new Error("Backend error");
  }
  return response.json();
}
export async function uploadDocument(file) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(
    "http://127.0.0.1:8000/documents/upload",
    {
      method: "POST",
      body: formData,
    }
  );

  if (!response.ok) {
    throw new Error("Upload failed");
  }

  return response.json();
}
export async function fetchDocuments() {
  const response = await fetch("http://127.0.0.1:8000/documents");

  if (!response.ok) {
    throw new Error("Failed to fetch documents");
  }

  return response.json();
}


