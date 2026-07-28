import { useState } from "react";
import { Link } from "react-router-dom";
import { forgotPasswordApi } from "../lib/api";
import Button from "../components/ui/Button";
import Alert from "../components/ui/Alert";

export default function ForgotPasswordPage() {
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
      const result = await forgotPasswordApi(email);
      setMessage(result?.message || "If your email is registered, you will receive a password reset link.");
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
        <h1 className="text-2xl font-semibold text-slate-900 mb-2">
          Forgot password?
        </h1>
        <p className="text-sm text-slate-600 mb-6">
          Enter your email address and we'll send you a link to reset your password.
        </p>

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

            <Button
              type="submit"
              disabled={loading}
              loading={loading}
              fullWidth
              className="mt-4"
            >
              Send reset link
            </Button>

            {error && <Alert variant="error" message={error} />}

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
            <div className="mb-4 flex items-center justify-center">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-emerald-100">
                <svg className="h-6 w-6 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
            </div>
            <p className="text-sm text-green-700 text-center font-medium mb-4">{message}</p>

            <div className="mt-4 rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
              We sent a password reset link to <strong>{email}</strong>.
              Please open your inbox and click the link to reset your password.
              If you do not see it, check your spam folder.
            </div>

            <div className="mt-5 flex flex-col gap-3">
              <Button
                as={Link}
                to="/login"
                fullWidth
                className="bg-slate-900 hover:bg-slate-800"
              >
                Back to login
              </Button>

              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  setSent(false);
                  setMessage("");
                  setError("");
                }}
                fullWidth
              >
                Use another email
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
