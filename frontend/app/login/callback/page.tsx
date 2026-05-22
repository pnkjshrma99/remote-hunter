"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function OAuthCallbackPage() {
  const router = useRouter();

  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      // Only accept messages from same origin
      if (event.origin !== window.location.origin) {
        return;
      }

      if (event.data.type === "oauth-callback") {
        // Send the token/code back to the parent window
        window.opener?.postMessage(
          {
            type: "oauth-success",
            provider: event.data.provider,
            token: event.data.token,
          },
          window.location.origin
        );
        window.close();
      }
    };

    // Check URL parameters for OAuth response
    const urlParams = new URLSearchParams(window.location.search);
    const accessToken = urlParams.get("access_token");
    const code = urlParams.get("code");
    const state = urlParams.get("state");
    const error = urlParams.get("error");

    if (error) {
      window.opener?.postMessage(
        {
          type: "oauth-error",
          error: error,
        },
        window.location.origin
      );
      window.close();
      return;
    }

    if (accessToken) {
      // Google OAuth returns access token directly
      window.opener?.postMessage(
        {
          type: "oauth-success",
          provider: "google",
          token: accessToken,
        },
        window.location.origin
      );
      window.close();
    } else if (code && state) {
      // GitHub OAuth returns a code that needs to be exchanged
      // For now, we'll send the code to the parent window
      // In production, you should exchange this on the backend
      window.opener?.postMessage(
        {
          type: "oauth-success",
          provider: state,
          token: code,
        },
        window.location.origin
      );
      window.close();
    } else {
      // No token or code found
      window.opener?.postMessage(
        {
          type: "oauth-error",
          error: "No token or code received",
        },
        window.location.origin
      );
      window.close();
    }

    window.addEventListener("message", handleMessage);
    return () => window.removeEventListener("message", handleMessage);
  }, [router]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 via-white to-sky-50">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-sky-600 mx-auto mb-4"></div>
        <p className="text-stone-600">Processing OAuth callback...</p>
      </div>
    </div>
  );
}
