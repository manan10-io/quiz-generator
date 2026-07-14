import type { NextAuthOptions } from "next-auth";
import GoogleProvider from "next-auth/providers/google";
import { API_URL } from "@/lib/constants";

export const authOptions: NextAuthOptions = {
  providers: [
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
      authorization: {
        params: {
          scope: [
            "openid",
            "email",
            "profile",
            "https://www.googleapis.com/auth/forms.body",
            "https://www.googleapis.com/auth/drive.file",
          ].join(" "),
          access_type: "offline",
          prompt: "consent",
        },
      },
    }),
  ],

  session: {
    strategy: "jwt",
    maxAge: 7 * 24 * 60 * 60, // 7 days
  },

  pages: {
    signIn: "/login",
    error: "/login",
  },

  callbacks: {
    async jwt({ token, account, user }) {
      // First sign-in: account contains the Google tokens
      if (account && user) {
        token.accessToken = account.access_token;
        token.refreshToken = account.refresh_token;
        token.accessTokenExpires = account.expires_at
          ? account.expires_at * 1000
          : null;
        token.googleId = account.providerAccountId;

        // Register/login user in our backend
        try {
          const res = await fetch(`${API_URL}/auth/google`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              google_id: account.providerAccountId,
              email: user.email,
              name: user.name,
              avatar_url: user.image,
              access_token: account.access_token,
              refresh_token: account.refresh_token,
              expires_at: account.expires_at,
            }),
          });
          if (res.ok) {
            const data = await res.json();
            token.backendToken = data.access_token;
            token.userId = data.user_id;
          }
        } catch (err) {
          console.error("Backend auth failed:", err);
        }
      }
      return token;
    },

    async session({ session, token }) {
      session.user.id = token.userId as string;
      session.accessToken = token.backendToken as string;
      session.googleAccessToken = token.accessToken as string;
      return session;
    },
  },

  debug: process.env.NODE_ENV === "development",
};

// ─── NextAuth type augmentations ──────────────────────────────────────────────
declare module "next-auth" {
  interface Session {
    accessToken: string;
    googleAccessToken: string;
    user: {
      id: string;
      name?: string | null;
      email?: string | null;
      image?: string | null;
    };
  }
}

declare module "next-auth/jwt" {
  interface JWT {
    accessToken?: string;
    refreshToken?: string;
    accessTokenExpires?: number | null;
    backendToken?: string;
    userId?: string;
    googleId?: string;
  }
}
