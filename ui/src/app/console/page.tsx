"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Textarea } from "@/components/ui/Textarea";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { useAuthSession } from "@/hooks/useAuthSession";

type Subscription = {
  id: string;
  code: string;
  name: string;
  status: string;
  activated_at?: string;
  expires_at?: string;
};

type Ticket = {
  external_id: string;
  subject: string;
  priority: string;
  status: string;
  created_at: string;
  updated_at: string;
};

async function apiFetch(
  path: string,
  options: RequestInit = {},
  token?: string | null
) {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) headers.Authorization = `Bearer ${token}`;

  const resp = await fetch(path, {
    ...options,
    headers,
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.error || err.detail || `Request failed: ${resp.status}`);
  }
  return resp.json();
}

export default function ConsolePage() {
  const { token, setToken } = useAuthSession();

  const [email, setEmail] = useState<string>("kasuncsb@gmail.com");
  const [otpCode, setOtpCode] = useState("");
  const [otpStatus, setOtpStatus] = useState("");

  const [subject, setSubject] = useState("Billing question");
  const [description, setDescription] = useState("I was charged twice for my data pack.");
  const [priority, setPriority] = useState("normal");

  const [serviceCode, setServiceCode] = useState("DATA_5GB");

  const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [loadingSubs, setLoadingSubs] = useState(false);
  const [loadingTickets, setLoadingTickets] = useState(false);
  const [actionStatus, setActionStatus] = useState("");

  const isVerified = Boolean(token);

  const fetchSubs = async () => {
    if (!token) return;
    setLoadingSubs(true);
    try {
      const data = await apiFetch(
        `/api/actions/subscriptions?email=${encodeURIComponent(email)}`,
        { method: "GET" },
        token
      );
      setSubscriptions(data.subscriptions || []);
    } catch (err) {
      setActionStatus(err instanceof Error ? err.message : "Failed to load subscriptions");
    } finally {
      setLoadingSubs(false);
    }
  };

  const fetchTickets = async () => {
    if (!token) return;
    setLoadingTickets(true);
    try {
      const data = await apiFetch(
        `/api/actions/tickets?email=${encodeURIComponent(email)}`,
        { method: "GET" },
        token
      );
      setTickets(data.tickets || []);
    } catch (err) {
      setActionStatus(err instanceof Error ? err.message : "Failed to load tickets");
    } finally {
      setLoadingTickets(false);
    }
  };

  useEffect(() => {
    if (token) {
      fetchSubs();
      fetchTickets();
    } else {
      setSubscriptions([]);
      setTickets([]);
    }
  }, [token]);

  const startOtp = async () => {
    try {
      setOtpStatus("Sending code...");
      await apiFetch("/api/auth/otp/start", {
        method: "POST",
        body: JSON.stringify({ email }),
      });
      setOtpStatus("Code sent. Check your inbox.");
    } catch (err) {
      setOtpStatus(err instanceof Error ? err.message : "Failed to send code");
    }
  };

  const confirmOtp = async () => {
    try {
      setOtpStatus("Confirming...");
      const data = await apiFetch("/api/auth/otp/confirm", {
        method: "POST",
        body: JSON.stringify({ email, code: otpCode }),
      });
      setToken(data.token);
      setOtpStatus("Verified. Session active.");
    } catch (err) {
      setOtpStatus(err instanceof Error ? err.message : "Verification failed");
    }
  };

  const createTicket = async () => {
    if (!token) {
      setActionStatus("Please verify first.");
      return;
    }
    try {
      setActionStatus("Creating ticket...");
      await apiFetch(
        "/api/actions/create-ticket",
        {
          method: "POST",
          body: JSON.stringify({
            email,
            subject,
            description,
            priority,
            idempotency_key: `ticket-${subject}-${email}`,
          }),
        },
        token
      );
      setActionStatus("Ticket created.");
      fetchTickets();
    } catch (err) {
      setActionStatus(err instanceof Error ? err.message : "Failed to create ticket");
    }
  };

  const activate = async () => {
    if (!token) {
      setActionStatus("Please verify first.");
      return;
    }
    try {
      setActionStatus("Activating...");
      await apiFetch(
        "/api/actions/activate",
        {
          method: "POST",
          body: JSON.stringify({
            email,
            service_code: serviceCode,
            idempotency_key: `activate-${serviceCode}-${email}`,
          }),
        },
        token
      );
      setActionStatus("Service activated.");
      fetchSubs();
    } catch (err) {
      setActionStatus(err instanceof Error ? err.message : "Failed to activate service");
    }
  };

  const deactivate = async () => {
    if (!token) {
      setActionStatus("Please verify first.");
      return;
    }
    try {
      setActionStatus("Deactivating...");
      await apiFetch(
        "/api/actions/deactivate",
        {
          method: "POST",
          body: JSON.stringify({
            email,
            service_code: serviceCode,
            idempotency_key: `deactivate-${serviceCode}-${email}`,
          }),
        },
        token
      );
      setActionStatus("Service deactivated.");
      fetchSubs();
    } catch (err) {
      setActionStatus(err instanceof Error ? err.message : "Failed to deactivate service");
    }
  };

  const logout = () => {
    setToken(null);
    setOtpStatus("Logged out.");
  };

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-neutral-900 dark:text-neutral-50">
            Console
          </h1>
          <p className="text-neutral-500">
            Verify via email OTP, then manage tickets and services.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant={isVerified ? "success" : "secondary"}>
            {isVerified ? "Verified" : "Not verified"}
          </Badge>
          {isVerified && (
            <Button variant="ghost" size="sm" onClick={logout}>
              Log out
            </Button>
          )}
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <Card className="p-6 space-y-4">
          <h2 className="text-lg font-semibold text-neutral-900 dark:text-neutral-50">
            Email Verification
          </h2>
          <Input
            label="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
          />
          <div className="flex gap-3">
            <Button onClick={startOtp} variant="primary">
              Send Code
            </Button>
            <Input
              label="Code"
              value={otpCode}
              onChange={(e) => setOtpCode(e.target.value)}
              placeholder="123456"
              className="max-w-[200px]"
            />
            <Button onClick={confirmOtp} variant="secondary">
              Confirm
            </Button>
          </div>
          <p className="text-sm text-neutral-500">{otpStatus}</p>
        </Card>

        <Card className="p-6 space-y-4">
          <h2 className="text-lg font-semibold text-neutral-900 dark:text-neutral-50">
            Actions
          </h2>
          <div className="grid gap-3">
            <Textarea
              label="Ticket description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
            <div className="grid grid-cols-2 gap-3">
              <Input
                label="Ticket subject"
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
              />
              <Input
                label="Priority"
                value={priority}
                onChange={(e) => setPriority(e.target.value)}
                placeholder="low|normal|high|urgent"
              />
            </div>
            <Button variant="primary" onClick={createTicket} disabled={!isVerified}>
              Create Ticket
            </Button>
          </div>

          <div className="grid grid-cols-2 gap-3 pt-4 border-t border-neutral-200 dark:border-neutral-800">
            <Input
              label="Service code"
              value={serviceCode}
              onChange={(e) => setServiceCode(e.target.value)}
              placeholder="DATA_5GB"
            />
            <div className="flex items-end gap-2">
              <Button variant="accent" onClick={activate} disabled={!isVerified}>
                Activate
              </Button>
              <Button variant="ghost" onClick={deactivate} disabled={!isVerified}>
                Deactivate
              </Button>
            </div>
          </div>

          <p className="text-sm text-neutral-500">{actionStatus}</p>
        </Card>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <Card className="p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-50">
              Subscriptions
            </h3>
            <Button size="sm" variant="ghost" onClick={fetchSubs} disabled={!isVerified} isLoading={loadingSubs}>
              Refresh
            </Button>
          </div>
          <div className="space-y-3">
            {subscriptions.length === 0 && (
              <p className="text-sm text-neutral-500">No subscriptions.</p>
            )}
            {subscriptions.map((sub) => (
              <div
                key={`${sub.id}-${sub.code}`}
                className="p-3 rounded-lg border border-neutral-200 dark:border-neutral-800 bg-white/50 dark:bg-neutral-900/50"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-semibold">{sub.name}</p>
                    <p className="text-sm text-neutral-500">{sub.code}</p>
                  </div>
                  <Badge variant={sub.status === "active" ? "success" : "secondary"}>
                    {sub.status}
                  </Badge>
                </div>
                <p className="text-xs text-neutral-500 mt-1">
                  Activated: {sub.activated_at || "—"} | Expires: {sub.expires_at || "—"}
                </p>
              </div>
            ))}
          </div>
        </Card>

        <Card className="p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-50">
              Tickets
            </h3>
            <Button size="sm" variant="ghost" onClick={fetchTickets} disabled={!isVerified} isLoading={loadingTickets}>
              Refresh
            </Button>
          </div>
          <div className="space-y-3">
            {tickets.length === 0 && (
              <p className="text-sm text-neutral-500">No tickets.</p>
            )}
            {tickets.map((t) => (
              <div
                key={t.external_id}
                className="p-3 rounded-lg border border-neutral-200 dark:border-neutral-800 bg-white/50 dark:bg-neutral-900/50"
              >
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-semibold">{t.subject}</p>
                      <p className="text-sm text-neutral-500">{t.external_id}</p>
                    </div>
                    <div className="flex gap-2">
                      <Badge variant="secondary">{t.priority}</Badge>
                      <Badge variant={t.status === "open" ? "success" : "secondary"}>
                        {t.status}
                      </Badge>
                    </div>
                  </div>
                <p className="text-xs text-neutral-500 mt-1">
                  Created: {t.created_at} | Updated: {t.updated_at}
                </p>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}
