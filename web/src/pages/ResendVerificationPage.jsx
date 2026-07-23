import { useState } from "react";
import { Link } from "react-router-dom";
import { resendVerificationApi } from "../lib/api";

export default function ResendVerificationPage() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [sent, setSent] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage("");
    setError("");
    setSent(false);

    try {
      const result = await resendVerificationApi(email);
      setMessage(result?.message || "Verification email sent successfully.");
      setSent(true);
    } catch (err) {
      setError(err?.message || "Something went wrong.");
      setSent(false);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center px-4">
      <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h1 className="text-2xl font-semibold text-slate-900 mb-4">
          Resend verification
        </h1>

        {!sent ? (
          <form onSubmit={handleSubmit}>
            <label className="block text-sm font-medium text-slate-700 mb-2">
              Email address
            </label>

            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Enter your email"
              required
              className="w-full rounded-lg border border-slate-300 px-3 py-2 outline-none focus:border-slate-500"
            />

            <button
              type="submit"
              disabled={loading}
              className="mt-4 inline-flex w-full items-center justify-center rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-60"
            >
              {loading ? "Sending..." : "Send verification email"}
            </button>

            {error ? (
              <p className="mt-4 text-sm text-red-600">{error}</p>
            ) : null}

            <div className="mt-4">
              <Link
                to="/login"
                className="text-sm font-medium text-slate-700 underline"
              >
                Back to login
              </Link>
            </div>
          </form>
        ) : (
          <div>
            <p className="text-sm text-green-700">{message}</p>

            <div className="mt-4 rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
              We sent a new verification email to <strong>{email}</strong>.
              Please open your inbox and click the verification link.
              If you do not see it, check your spam folder.
            </div>

            <div className="mt-5 flex flex-col gap-3">
              <Link
                to="/login"
                className="inline-flex items-center justify-center rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium !text-white"
              >
                Back to login
              </Link>

              <button
                type="button"
                onClick={() => {
                  setSent(false);
                  setMessage("");
                  setError("");
                }}
                className="inline-flex items-center justify-center rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700"
              >
                Use another email
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}