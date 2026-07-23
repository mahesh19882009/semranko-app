import { Navigate, useLocation } from "react-router-dom";
import { isAuthenticated, getStoredUser } from "../utils/auth";

function ProtectedRoute({ children }) {
  const location = useLocation();
  const user = getStoredUser();

  if (!isAuthenticated()) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  if (user && user.isVerified === false) {
    return <Navigate to="/verify-email" replace />;
  }

  return children;
}

export default ProtectedRoute;