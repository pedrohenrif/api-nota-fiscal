import { Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { ProtectedRoute } from "./components/ProtectedRoute";
import Acesso from "./pages/Acesso";
import Ajuda from "./pages/Ajuda";
import Configuracoes from "./pages/Configuracoes";
import Dashboard from "./pages/Dashboard";
import Destinatarios from "./pages/Destinatarios";
import EmitirNota from "./pages/EmitirNota";
import Login from "./pages/Login";
import Logs from "./pages/Logs";
import Usuarios from "./pages/Usuarios";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Layout>
              <EmitirNota />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <Layout>
              <Dashboard />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/usuarios"
        element={
          <ProtectedRoute adminOnly>
            <Layout>
              <Usuarios />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/logs"
        element={
          <ProtectedRoute adminOnly>
            <Layout>
              <Logs />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/acesso"
        element={
          <ProtectedRoute adminOnly>
            <Layout>
              <Acesso />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/configuracoes"
        element={
          <ProtectedRoute adminOnly>
            <Layout>
              <Configuracoes />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/destinatarios"
        element={
          <ProtectedRoute>
            <Layout>
              <Destinatarios />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/ajuda"
        element={
          <ProtectedRoute>
            <Layout>
              <Ajuda />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
