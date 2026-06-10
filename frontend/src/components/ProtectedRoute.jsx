import { Navigate } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { Spinner } from "./ui";

export default function ProtectedRoute({ children, role }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="flex justify-center p-12"><Spinner /></div>;
  if (!user) return <Navigate to="/login" replace />;
  if (role && user.role !== role) return <Navigate to="/" replace />;
  return children;
}
