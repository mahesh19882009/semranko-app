import { Navigate } from "react-router-dom";
import { isAuthenticated } from "../utils/auth";

function PublicOnlyRoute({ children }) {
  if (isAuthenticated()) {
    return <Navigate to="/app" replace />;
  }

  return children;
}

export default PublicOnlyRoute;