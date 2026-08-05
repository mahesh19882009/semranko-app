'use client'
import { Navigate } from "../lib/navigation";
import { isAuthenticated } from "../utils/auth";

function PublicOnlyRoute({ children }) {
  if (isAuthenticated()) {
    return <Navigate to="/dashboard" replace />;
  }

  return children;
}

export default PublicOnlyRoute;