function Layout({ children }) {
  return (
    <div
      style={{
        minHeight: "100vh",
        backgroundColor: "#0f0f0f",
        color: "#eaeaea",
        display: "flex",
      }}
    >
      {/* Sidebar */}
      <aside
        style={{
          width: "240px",
          backgroundColor: "#121212",
          borderRight: "1px solid #1f1f1f",
          padding: "24px",
        }}
      >
        <h2 style={{ fontSize: "18px", marginBottom: "24px" }}>
          RAG Optimizer
        </h2>

        <nav style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
          <span style={{ color: "#fff", fontWeight: 500 }}>
            Documents
          </span>
          <span style={{ color: "#777" }}>
            Ask
          </span>
          <span style={{ color: "#777" }}>
            Runs
          </span>
        </nav>
      </aside>

      {/* Main content */}
      <main
        style={{
          flex: 1,
          padding: "40px",
        }}
      >
        <header style={{ marginBottom: "32px" }}>
          <h1 style={{ fontSize: "32px", marginBottom: "8px" }}>
            RAG Pipeline Optimizer
          </h1>
          <p style={{ color: "#a1a1a1" }}>
            Optimize and compare retrieval-augmented generation pipelines
          </p>
        </header>

        {children}
      </main>
    </div>
  );
}

export default Layout;
