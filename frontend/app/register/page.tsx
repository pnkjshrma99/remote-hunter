"use client";

import Link from "next/link";
import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { Briefcase, Mail, Lock, Eye, EyeOff, ArrowLeft, User } from "lucide-react";

function RegisterForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const nextParam = searchParams?.get("next");
  const nextPath = nextParam && nextParam.startsWith("/") && !nextParam.startsWith("//") ? nextParam : "/welcome";
  const { register, loginWithGoogle, loginWithGitHub, error, clearError } = useAuth();
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isOAuthLoading, setIsOAuthLoading] = useState(false);
  const [formData, setFormData] = useState({
    email: "",
    password: "",
    full_name: "",
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    clearError();

    try {
      await register({
        email: formData.email,
        password: formData.password,
        full_name: formData.full_name || undefined,
      });
      router.push(nextPath);
    } catch (err) {
      // Error is handled by auth context
    } finally {
      setIsLoading(false);
    }
  };

  const handleGoogleLogin = async () => {
    setIsOAuthLoading(true);
    clearError();

    try {
      const googleClientId = process.env.NEXT_PUBLIC_GOOGLE_OAUTH_CLIENT_ID;
      if (!googleClientId) {
        throw new Error("Google OAuth client ID not configured");
      }

      const authUrl = `https://accounts.google.com/o/oauth2/v2/auth?` +
        `client_id=${googleClientId}&` +
        `redirect_uri=${encodeURIComponent(window.location.origin + '/login/callback')}&` +
        `response_type=token&` +
        `scope=openid email profile&` +
        `state=google`;

      const popup = window.open(authUrl, 'google-auth', 'width=500,height=600');

      if (!popup) {
        throw new Error("Failed to open popup");
      }

      const token = await new Promise<string>((resolve, reject) => {
        const handleMessage = (event: MessageEvent) => {
          if (event.origin !== window.location.origin) {
            return;
          }

          if (event.data.type === "oauth-success" && event.data.provider === "google") {
            window.removeEventListener("message", handleMessage);
            resolve(event.data.token);
          } else if (event.data.type === "oauth-error") {
            window.removeEventListener("message", handleMessage);
            reject(new Error(event.data.error || "OAuth failed"));
          }
        };

        window.addEventListener("message", handleMessage);

        const checkPopup = setInterval(() => {
          if (popup.closed) {
            clearInterval(checkPopup);
            window.removeEventListener("message", handleMessage);
            reject(new Error("Popup closed"));
          }
        }, 1000);

        setTimeout(() => {
          clearInterval(checkPopup);
          window.removeEventListener("message", handleMessage);
          if (!popup.closed) popup.close();
          reject(new Error("OAuth timeout"));
        }, 300000);
      });

      await loginWithGoogle(token);
      router.push(nextPath);
    } catch (err) {
      // Error is handled by auth context
    } finally {
      setIsOAuthLoading(false);
    }
  };

  const handleGitHubLogin = async () => {
    setIsOAuthLoading(true);
    clearError();

    try {
      const githubClientId = process.env.NEXT_PUBLIC_GITHUB_OAUTH_CLIENT_ID;
      if (!githubClientId) {
        throw new Error("GitHub OAuth client ID not configured");
      }

      const authUrl = `https://github.com/login/oauth/authorize?` +
        `client_id=${githubClientId}&` +
        `redirect_uri=${encodeURIComponent(window.location.origin + '/login/callback')}&` +
        `scope=user:email&` +
        `state=github`;

      const popup = window.open(authUrl, 'github-auth', 'width=500,height=600');

      if (!popup) {
        throw new Error("Failed to open popup");
      }

      const token = await new Promise<string>((resolve, reject) => {
        const handleMessage = (event: MessageEvent) => {
          if (event.origin !== window.location.origin) {
            return;
          }

          if (event.data.type === "oauth-success" && event.data.provider === "github") {
            window.removeEventListener("message", handleMessage);
            resolve(event.data.token);
          } else if (event.data.type === "oauth-error") {
            window.removeEventListener("message", handleMessage);
            reject(new Error(event.data.error || "OAuth failed"));
          }
        };

        window.addEventListener("message", handleMessage);

        const checkPopup = setInterval(() => {
          if (popup.closed) {
            clearInterval(checkPopup);
            window.removeEventListener("message", handleMessage);
            reject(new Error("Popup closed"));
          }
        }, 1000);

        setTimeout(() => {
          clearInterval(checkPopup);
          window.removeEventListener("message", handleMessage);
          if (!popup.closed) popup.close();
          reject(new Error("OAuth timeout"));
        }, 300000);
      });

      await loginWithGitHub(token);
      router.push(nextPath);
    } catch (err) {
      // Error is handled by auth context
    } finally {
      setIsOAuthLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-sky-50 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <Link
            href="/"
            className="inline-flex items-center gap-2 text-sm text-stone-600 hover:text-stone-900 transition-colors mb-6"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to home
          </Link>
          <div className="flex items-center justify-center gap-2 mb-4">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-sky-500 to-sky-600 flex items-center justify-center">
              <Briefcase className="h-5 w-5 text-white" />
            </div>
          </div>
          <h1 className="text-2xl font-bold text-stone-900">Create your account</h1>
          <p className="mt-2 text-sm text-stone-600">
            Start your remote job hunting journey today
          </p>
        </div>

        <div className="bg-white rounded-2xl shadow-sm border border-stone-200 p-8">
          <form onSubmit={handleSubmit} className="space-y-5">
            {error && (
              <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-sm text-rose-700">
                {error}
              </div>
            )}

            <div>
              <label htmlFor="full_name" className="block text-sm font-medium text-stone-700 mb-2">
                Full name <span className="text-stone-400">(optional)</span>
              </label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-stone-400" />
                <input
                  id="full_name"
                  type="text"
                  value={formData.full_name}
                  onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                  className="w-full pl-10 pr-4 py-3 rounded-lg border border-stone-300 focus:border-sky-500 focus:ring-2 focus:ring-sky-200 outline-none transition-all text-sm"
                  placeholder="John Doe"
                />
              </div>
            </div>

            <div>
              <label htmlFor="email" className="block text-sm font-medium text-stone-700 mb-2">
                Email address
              </label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-stone-400" />
                <input
                  id="email"
                  type="email"
                  required
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  className="w-full pl-10 pr-4 py-3 rounded-lg border border-stone-300 focus:border-sky-500 focus:ring-2 focus:ring-sky-200 outline-none transition-all text-sm"
                  placeholder="you@example.com"
                />
              </div>
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-stone-700 mb-2">
                Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-stone-400" />
                <input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  required
                  minLength={8}
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  className="w-full pl-10 pr-12 py-3 rounded-lg border border-stone-300 focus:border-sky-500 focus:ring-2 focus:ring-sky-200 outline-none transition-all text-sm"
                  placeholder="Create a strong password"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-stone-400 hover:text-stone-600 transition-colors"
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
              <p className="mt-2 text-xs text-stone-500">
                Must be at least 8 characters long
              </p>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-3 px-4 rounded-lg relative z-10 bg-gradient-to-r from-indigo-600 to-indigo-700 text-white font-semibold text-sm hover:from-indigo-700 hover:to-indigo-800 focus:outline-none focus:ring-2 focus:ring-indigo-300 shadow-md transition-all disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {isLoading ? "Creating account..." : "Create account"}
            </button>
          </form>

          <p className="mt-4 text-xs text-stone-500 text-center">
            By creating an account, you agree to our{" "}
            <Link href="/terms" className="text-black-1200 hover:underline">
              Terms of Service
            </Link>{" "}
            and{" "}
            <Link href="/privacy" className="text-black-1200 hover:underline">
              Privacy Policy
            </Link>
            .
          </p>

          <div className="relative my-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-stone-200" />
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-4 bg-white text-stone-500">or</span>
            </div>
          </div>

          <div className="space-y-3">
            <button
              type="button"
              onClick={handleGoogleLogin}
              disabled={isOAuthLoading}
              className="w-full py-3 px-4 rounded-lg border border-stone-300 bg-white text-stone-700 font-medium text-sm hover:bg-stone-50 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              <svg className="h-4 w-4" viewBox="0 0 24 24">
                <path fill="currentColor" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path fill="currentColor" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="currentColor" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path fill="currentColor" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
              </svg>
              {isOAuthLoading ? "Signing in..." : "Sign up with Google"}
            </button>
            <button
              type="button"
              onClick={handleGitHubLogin}
              disabled={isOAuthLoading}
              className="w-full py-3 px-4 rounded-lg border border-stone-300 bg-white text-stone-700 font-medium text-sm hover:bg-stone-50 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 0C4.477 0 0 4.484 0 10.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0110 4.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0020 10.017C20 4.484 15.522 0 10 0z" clipRule="evenodd"/>
              </svg>
              {isOAuthLoading ? "Signing in..." : "Sign up with GitHub"}
            </button>
          </div>
        </div>

        <p className="text-center mt-6 text-sm text-stone-600">
          Already have an account?{" "}
          <Link href={`/login${nextPath !== "/" ? `?next=${encodeURIComponent(nextPath)}` : ""}`} className="font-medium text-sky-600 hover:text-sky-700">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}

export default function RegisterPage() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center text-stone-500">Loading...</div>}>
      <RegisterForm />
    </Suspense>
  );
}
