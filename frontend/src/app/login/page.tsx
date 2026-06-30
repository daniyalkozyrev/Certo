"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowRight, Loader2, Mail, ShieldCheck } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Logo } from "@/components/logo";
import { useAuth } from "@/components/auth-provider";
import {
  ApiError, getAuthConfig, googleAuthorizeUrl, requestLoginCode, verifyLoginCode,
} from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const { login, user, loading } = useAuth();

  const [step, setStep] = useState<"email" | "code">("email");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [devCode, setDevCode] = useState<string | null>(null);
  const [googleEnabled, setGoogleEnabled] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  // If a Google redirect handed us a token in ?token=, finish login.
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const token = params.get("token");
    if (token) {
      login(token).then(() => router.replace("/dashboard")).catch(() => setError("Sign-in failed."));
    }
  }, [login, router]);

  // Already logged in → go to the app.
  useEffect(() => {
    if (!loading && user) router.replace("/dashboard");
  }, [loading, user, router]);

  useEffect(() => {
    getAuthConfig().then((c) => setGoogleEnabled(c.google_enabled)).catch(() => {});
  }, []);

  async function sendCode() {
    if (!email.trim()) { setError("Enter your email."); return; }
    setBusy(true); setError("");
    try {
      const res = await requestLoginCode(email.trim());
      setDevCode(res.dev_code);
      setStep("code");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not send the code.");
    } finally {
      setBusy(false);
    }
  }

  async function verify() {
    if (!code.trim()) { setError("Enter the code."); return; }
    setBusy(true); setError("");
    try {
      const res = await verifyLoginCode(email.trim(), code.trim());
      await login(res.access_token, res.user);
      router.replace("/dashboard");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Verification failed.");
      setBusy(false);
    }
  }

  return (
    <div className="grid min-h-screen place-items-center bg-secondary/30 p-4">
      <div className="w-full max-w-sm">
        <div className="mb-6 flex justify-center"><Logo /></div>
        <Card>
          <CardContent className="space-y-5 pt-6">
            <div className="text-center">
              <h1 className="text-xl font-semibold tracking-tight">Sign in to Certo</h1>
              <p className="mt-1 text-sm text-muted-foreground">
                {step === "email" ? "We'll email you a one-time code." : `Code sent to ${email}`}
              </p>
            </div>

            {googleEnabled && step === "email" && (
              <>
                <a href={googleAuthorizeUrl()}>
                  <Button variant="outline" size="lg" className="w-full">
                    <GoogleIcon /> Continue with Google
                  </Button>
                </a>
                <div className="flex items-center gap-3 text-xs text-muted-foreground">
                  <div className="h-px flex-1 bg-border" /> or <div className="h-px flex-1 bg-border" />
                </div>
              </>
            )}

            <AnimatePresence mode="wait">
              {step === "email" ? (
                <motion.div key="email" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-3">
                  <div className="flex items-center gap-2 rounded-lg border bg-background px-3">
                    <Mail className="size-4 text-muted-foreground" />
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      onKeyDown={(e) => e.key === "Enter" && sendCode()}
                      placeholder="you@email.com"
                      autoFocus
                      className="w-full bg-transparent py-2.5 text-sm outline-none placeholder:text-muted-foreground"
                    />
                  </div>
                  <Button onClick={sendCode} size="lg" className="w-full" disabled={busy}>
                    {busy ? <Loader2 className="size-4 animate-spin" /> : <>Continue <ArrowRight className="size-4" /></>}
                  </Button>
                </motion.div>
              ) : (
                <motion.div key="code" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-3">
                  {devCode && (
                    <div className="rounded-lg border border-accent/30 bg-accent/5 p-3 text-center text-sm">
                      <span className="text-muted-foreground">Dev mode — your code is </span>
                      <span className="font-mono font-semibold text-accent">{devCode}</span>
                    </div>
                  )}
                  <input
                    value={code}
                    onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                    onKeyDown={(e) => e.key === "Enter" && verify()}
                    placeholder="6-digit code"
                    inputMode="numeric"
                    autoFocus
                    className="w-full rounded-lg border bg-background px-3 py-2.5 text-center font-mono text-lg tracking-[0.3em] outline-none focus:ring-2 focus:ring-ring"
                  />
                  <Button onClick={verify} size="lg" className="w-full" disabled={busy}>
                    {busy ? <Loader2 className="size-4 animate-spin" /> : <><ShieldCheck className="size-4" /> Verify & sign in</>}
                  </Button>
                  <button onClick={() => { setStep("email"); setCode(""); setError(""); }} className="w-full text-xs text-muted-foreground hover:text-foreground">
                    ← Use a different email
                  </button>
                </motion.div>
              )}
            </AnimatePresence>

            {error && <p className="text-center text-sm text-[hsl(var(--danger))]">{error}</p>}
          </CardContent>
        </Card>
        <p className="mt-4 text-center text-xs text-muted-foreground">
          By continuing you agree to Certo&apos;s terms. No password required.
        </p>
      </div>
    </div>
  );
}

function GoogleIcon() {
  return (
    <svg viewBox="0 0 24 24" className="size-4" aria-hidden>
      <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.76h3.56c2.08-1.92 3.28-4.74 3.28-8.09Z" />
      <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.56-2.76c-.98.66-2.23 1.06-3.72 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84A11 11 0 0 0 12 23Z" />
      <path fill="#FBBC05" d="M5.84 14.1a6.6 6.6 0 0 1 0-4.2V7.06H2.18a11 11 0 0 0 0 9.88l3.66-2.84Z" />
      <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1A11 11 0 0 0 2.18 7.06l3.66 2.84C6.71 7.3 9.14 5.38 12 5.38Z" />
    </svg>
  );
}
