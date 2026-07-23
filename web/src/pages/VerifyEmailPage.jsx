import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { verifyEmailApi } from "../lib/api";

export default function VerifyEmailPage() {
  const [searchParams] = useSearchParams();
  const [status, setStatus] = useState("loading");
  const [message, setMessage] = useState("Verifying your email...");

  const token = useMemo(() => searchParams.get("token"), [searchParams]);

  useEffect(() => {
    const runVerification = async () => {
      if (!token) {
        setStatus("error");
        setMessage("Verification token missing.");
        return;
      }

      try {
        const result = await verifyEmailApi(token);
        setStatus("success");
        setMessage(result?.message || "Email verified successfully.");
      } catch (error) {
        setStatus("error");
        setMessage(error?.message || "Invalid or expired verification link.");
      }
    };

    runVerification();
  }, [token]);

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center px-4">
      <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h1 className="text-2xl font-semibold text-slate-900 mb-3">
          Email verification
        </h1>

        {status === "loading" && (
          <p className="text-slate-600">{message}</p>
        )}

        {status === "success" && (
          <>
            <p className="text-green-700 mb-4">{message}</p>
            <Link
              to="/login"
              className="inline-flex items-center rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium !text-white"
            >
              Go to login
            </Link>
          </>
        )}

        {status === "error" && (
          <>
            <p className="text-red-600 mb-4">{message}</p>
            <Link
              to="/resend-verification"
              className="inline-flex items-center rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700"
            >
              Resend verification email
            </Link>
          </>
        )}
      </div>
    </div>
  );
}