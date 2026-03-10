import { useEffect, useState } from "react";

function Admin() {
  const [users, setUsers] = useState([]);
  const [token, setToken] = useState(localStorage.getItem("nexo_token") || "");
  const [loginForm, setLoginForm] = useState({ username: "", password: "" });
  const [loginError, setLoginError] = useState("");
  const [loginLoading, setLoginLoading] = useState(false);

  const login = async () => {
    setLoginLoading(true);
    setLoginError("");
    try {
      const res = await fetch("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(loginForm),
      });
      const data = await res.json();
      if (res.ok) {
        localStorage.setItem("nexo_token", data.access_token);
        setToken(data.access_token);
      } else {
        setLoginError(data.detail || "Credenciales inválidas");
      }
    } catch {
      setLoginError("Error conectando al backend");
    } finally {
      setLoginLoading(false);
    }
  };

  const handleLoginKey = e => {
    if (e.key === "Enter") login();
  };

  useEffect(() => {
    if (!token) return;
    fetch("/admin/users", { headers: { Authorization: `Bearer ${token}` } })
      .then(r => {
        if (!r.ok) throw new Error("unauthorized");
        return r.json();
      })
      .then(d => setUsers(d.users || []))
      .catch(() => {
        setUsers([]);
        localStorage.removeItem("nexo_token");
        setToken("");
      });
  }, [token]);

  /* ---- Login Screen ---- */
  if (!token) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="w-full max-w-xs">
          <div className="nexo-card p-6 space-y-4">
            <div className="text-center mb-2">
              <div className="w-10 h-10 rounded-lg bg-nexo-green/20 flex items-center justify-center mx-auto mb-3">
                <span className="text-nexo-green-l text-lg font-bold">Nₛ</span>
              </div>
              <h2 className="text-base font-bold text-nexo-text">Acceso Admin</h2>
              <p className="text-[10px] text-nexo-dim mt-1">Ingresa tus credenciales para continuar</p>
            </div>

            <div className="space-y-3">
              <input
                className="nexo-input text-sm"
                placeholder="Usuario"
                value={loginForm.username}
                onChange={e => setLoginForm(f => ({ ...f, username: e.target.value }))}
                onKeyDown={handleLoginKey}
              />
              <input
                className="nexo-input text-sm"
                type="password"
                placeholder="Contraseña"
                value={loginForm.password}
                onChange={e => setLoginForm(f => ({ ...f, password: e.target.value }))}
                onKeyDown={handleLoginKey}
              />
            </div>

            {loginError && (
              <div className="bg-red-500/10 border border-red-500/20 rounded px-3 py-2">
                <p className="text-xs text-red-300">{loginError}</p>
              </div>
            )}

            <button onClick={login} disabled={loginLoading} className="nexo-btn w-full text-sm">
              {loginLoading ? "Verificando…" : "Ingresar"}
            </button>
          </div>
        </div>
      </div>
    );
  }

  /* ---- Admin Dashboard ---- */
  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-bold text-nexo-text">Panel de Administración</h2>
          <p className="text-xs text-nexo-dim">{users.length} usuario(s) registrados</p>
        </div>
        <button
          onClick={() => { localStorage.removeItem("nexo_token"); setToken(""); }}
          className="nexo-btn-secondary text-xs px-3 py-1.5"
        >
          Cerrar sesión
        </button>
      </div>

      {/* Users table */}
      <div className="nexo-card overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-nexo-border bg-nexo-dark/50">
              <th className="text-left px-4 py-3 text-[10px] text-nexo-dim font-semibold uppercase tracking-wider">Usuario</th>
              <th className="text-left px-4 py-3 text-[10px] text-nexo-dim font-semibold uppercase tracking-wider">Email</th>
              <th className="text-left px-4 py-3 text-[10px] text-nexo-dim font-semibold uppercase tracking-wider">Rol</th>
              <th className="text-left px-4 py-3 text-[10px] text-nexo-dim font-semibold uppercase tracking-wider">Estado</th>
              <th className="text-left px-4 py-3 text-[10px] text-nexo-dim font-semibold uppercase tracking-wider">Creado</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u, i) => (
              <tr key={i} className="border-b border-nexo-border/30 hover:bg-nexo-surface/50 transition-colors">
                <td className="px-4 py-3 font-medium text-nexo-text">{u.username}</td>
                <td className="px-4 py-3 text-nexo-muted">{u.email}</td>
                <td className="px-4 py-3">
                  <span className={`nexo-badge ${
                    u.role === "admin" ? "bg-purple-500/15 text-purple-400" : "bg-nexo-surface text-nexo-muted"
                  }`}>
                    {u.role}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-1.5">
                    <span className={`w-1.5 h-1.5 rounded-full ${u.is_active ? "bg-emerald-400" : "bg-red-400"}`} />
                    <span className="text-xs text-nexo-muted">{u.is_active ? "Activo" : "Inactivo"}</span>
                  </div>
                </td>
                <td className="px-4 py-3 text-xs text-nexo-dim">
                  {u.created_at ? new Date(u.created_at).toLocaleDateString() : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default Admin;
