import { redirect } from "next/navigation";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { Hero } from "@/components/landing/Hero";
import { FeatureGrid, HowItWorks, CTASection } from "@/components/landing";
import { APP_NAME } from "@/lib/constants";
import { Sparkles } from "lucide-react";

export default async function LandingPage() {
  const session = await getServerSession(authOptions);
  if (session) redirect("/dashboard");

  return (
    <div className="min-h-screen bg-background">
      {/* Navigation */}
      <nav className="fixed top-0 inset-x-0 z-50 flex h-14 items-center justify-between px-6 border-b border-border/60 bg-background/80 backdrop-blur-sm">
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary">
            <Sparkles className="h-3.5 w-3.5 text-primary-foreground" />
          </div>
          <span className="font-semibold text-sm text-foreground">{APP_NAME}</span>
        </div>
        <div className="flex items-center gap-2">
          <a
            href="#how-it-works"
            className="text-sm text-muted-foreground hover:text-foreground transition-colors hidden sm:block"
          >
            How it works
          </a>
        </div>
      </nav>

      <main className="pt-14">
        <Hero />
        <FeatureGrid />
        <HowItWorks />
        <CTASection />
      </main>

      <footer className="border-t border-border py-8 text-center text-xs text-muted-foreground">
        <p>© {new Date().getFullYear()} {APP_NAME}. Built for educators.</p>
      </footer>
    </div>
  );
}
