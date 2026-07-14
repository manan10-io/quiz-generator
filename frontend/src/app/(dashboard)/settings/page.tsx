"use client";

import { motion } from "framer-motion";
import { useSession, signOut } from "next-auth/react";
import Image from "next/image";
import { LogOut, User, Sliders, Palette, Info } from "lucide-react";
import { Header } from "@/components/layout/Header";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Separator } from "@/components/ui/separator";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { useSettings } from "@/hooks";
import { pageVariants, staggerContainer, fadeUp } from "@/lib/animations";
import { APP_NAME } from "@/lib/constants";
import { toast } from "sonner";

const AUTO_DIFFICULTY_VALUE = "_auto";

function SettingsSection({
  icon: Icon,
  title,
  children,
}: {
  icon: React.ElementType;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <motion.div
      variants={fadeUp}
      className="rounded-2xl border border-border bg-card shadow-card overflow-hidden"
    >
      <div className="flex items-center gap-2.5 px-5 py-4 border-b border-border bg-muted/30">
        <Icon className="h-4 w-4 text-muted-foreground" />
        <h2 className="text-sm font-semibold text-foreground">{title}</h2>
      </div>
      <div className="p-5 space-y-5">{children}</div>
    </motion.div>
  );
}

function SettingRow({
  label,
  description,
  children,
}: {
  label: string;
  description?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-center justify-between gap-4">
      <div className="min-w-0">
        <p className="text-sm text-foreground">{label}</p>
        {description && (
          <p className="text-xs text-muted-foreground mt-0.5">{description}</p>
        )}
      </div>
      <div className="shrink-0">{children}</div>
    </div>
  );
}

export default function SettingsPage() {
  const { data: session } = useSession();
  const { settings, save, isSaving } = useSettings();

  const handleToggle = async (key: keyof typeof settings, value: boolean) => {
    await save({ [key]: value });
    toast.success("Settings saved");
  };

  const handleSelect = async (key: keyof typeof settings, value: string) => {
    await save({ [key]: value });
    toast.success("Settings saved");
  };

  return (
    <>
      <Header title="Settings" subtitle="Manage your preferences" />

      <motion.div
        variants={pageVariants}
        initial="hidden"
        animate="visible"
        className="p-5 max-w-2xl space-y-5"
      >
        {/* ─── Account ─── */}
        <SettingsSection icon={User} title="Account">
          {session?.user && (
            <div className="flex items-center gap-4">
              {session.user.image ? (
                <Image
                  src={session.user.image}
                  alt={session.user.name ?? "User"}
                  width={48}
                  height={48}
                  className="rounded-full ring-2 ring-border"
                />
              ) : (
                <div className="h-12 w-12 rounded-full bg-primary/20 flex items-center justify-center text-lg font-semibold text-primary">
                  {session.user.name?.charAt(0) ?? "U"}
                </div>
              )}
              <div>
                <p className="font-semibold text-foreground">{session.user.name}</p>
                <p className="text-sm text-muted-foreground">{session.user.email}</p>
              </div>
              <Button
                variant="outline"
                size="sm"
                className="ml-auto"
                onClick={() => signOut({ callbackUrl: "/login" })}
              >
                <LogOut className="h-3.5 w-3.5" />
                Sign out
              </Button>
            </div>
          )}
        </SettingsSection>

        {/* ─── Appearance ─── */}
        <SettingsSection icon={Palette} title="Appearance">
          <SettingRow label="Theme" description="Choose your preferred colour scheme">
            <Select
              value={settings.theme}
              onValueChange={(v) => handleSelect("theme", v)}
            >
              <SelectTrigger className="w-32">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="light">Light</SelectItem>
                <SelectItem value="dark">Dark</SelectItem>
                <SelectItem value="system">System</SelectItem>
              </SelectContent>
            </Select>
          </SettingRow>
        </SettingsSection>

        {/* ─── Quiz defaults ─── */}
        <SettingsSection icon={Sliders} title="Quiz defaults">
          <SettingRow label="Default marks per question" description="Applied when marks are not specified in source">
            <Input
              type="number"
              step="0.5"
              min="0"
              value={settings.default_marks}
              onChange={(e) => save({ default_marks: parseFloat(e.target.value) || 1 })}
              className="w-24 h-8 text-sm"
            />
          </SettingRow>

          <Separator />

          <SettingRow label="Default difficulty" description="Fallback difficulty when not detected">
            <Select
              value={settings.default_difficulty || AUTO_DIFFICULTY_VALUE}
              onValueChange={(v) =>
                handleSelect(
                  "default_difficulty",
                  v === AUTO_DIFFICULTY_VALUE ? "" : v
                )
              }
            >
              <SelectTrigger className="w-32">
                <SelectValue placeholder="Auto" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={AUTO_DIFFICULTY_VALUE}>Auto-detect</SelectItem>
                <SelectItem value="easy">Easy</SelectItem>
                <SelectItem value="medium">Medium</SelectItem>
                <SelectItem value="hard">Hard</SelectItem>
              </SelectContent>
            </Select>
          </SettingRow>

          <Separator />

          <SettingRow
            label="Shuffle questions by default"
            description="Applied when generating new Google Forms"
          >
            <Switch
              checked={settings.shuffle_questions}
              onCheckedChange={(v) => handleToggle("shuffle_questions", v)}
            />
          </SettingRow>

          <SettingRow
            label="Shuffle options by default"
            description="Randomise answer choices in new forms"
          >
            <Switch
              checked={settings.shuffle_options}
              onCheckedChange={(v) => handleToggle("shuffle_options", v)}
            />
          </SettingRow>

          <Separator />

          <SettingRow
            label="Autosave interval (seconds)"
            description="How often to save editor changes"
          >
            <Input
              type="number"
              min="1"
              max="60"
              value={settings.autosave_interval}
              onChange={(e) => save({ autosave_interval: parseInt(e.target.value) || 5 })}
              className="w-20 h-8 text-sm"
            />
          </SettingRow>
        </SettingsSection>

        {/* ─── About ─── */}
        <SettingsSection icon={Info} title="About">
          <div className="space-y-2 text-sm text-muted-foreground">
            <p><span className="text-foreground font-medium">{APP_NAME}</span> — AI-powered MCQ to Google Forms converter</p>
            <p>Supports PDF, DOCX, images, and plain text in English, Hindi, and Gujarati.</p>
            <p className="text-xs">
              Uses Google OAuth 2.0. Questions are stored securely and never shared.
              Google Forms are created directly in your Google account.
            </p>
          </div>
        </SettingsSection>
      </motion.div>
    </>
  );
}
