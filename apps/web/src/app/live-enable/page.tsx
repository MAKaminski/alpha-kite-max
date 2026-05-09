import { Nav } from "@/components/Nav";
import {
  fetchBrokerSnapshot,
  fetchKillSwitchState,
  fetchTodayRealizedUsd,
} from "@/lib/queries";
import PromoteForm from "./PromoteForm";

export const dynamic = "force-dynamic";
export const revalidate = 0;

const DEFAULT_DAILY_LOSS_LIMIT_USD = 50;

export default async function LiveEnablePage() {
  const [brokerSnap, killSwitch, todayRealized] = await Promise.all([
    fetchBrokerSnapshot(),
    fetchKillSwitchState(),
    fetchTodayRealizedUsd(),
  ]);

  const lossOk = todayRealized > -DEFAULT_DAILY_LOSS_LIMIT_USD;
  const checklist = [
    {
      label: "IBKR gateway connected",
      ok: brokerSnap.connected === true,
      detail:
        brokerSnap.connected === true
          ? `${brokerSnap.accountId ?? "—"} (${brokerSnap.brokerMode ?? "?"}) heartbeat OK`
          : brokerSnap.lastError
            ? `last error: ${brokerSnap.lastError}`
            : "no recent BROKER_HEARTBEAT in audit_log",
    },
    {
      label: "Kill switch disengaged",
      ok: !killSwitch.active,
      detail: killSwitch.active
        ? "kill switch is engaged — disengage it before going live"
        : killSwitch.lastSeen
          ? "no engaged event currently"
          : "no kill switch events on record",
    },
    {
      label: "Daily loss limit not breached",
      ok: lossOk,
      detail: `today's realized: $${todayRealized.toFixed(2)} (limit −$${DEFAULT_DAILY_LOSS_LIMIT_USD})`,
    },
    {
      label: "Backtest passed (BACKTEST_PASS audit row in last 24h)",
      // TODO: write the BACKTEST_PASS audit row from the /backtest UI on
      //       success, then check it here. For now the gate is informational.
      ok: false,
      detail:
        "Hook this up by writing a BACKTEST_PASS audit row from /backtest after a successful run with positive expectancy.",
    },
  ];

  const serviceRoleConfigured = !!process.env.SUPABASE_SERVICE_ROLE_KEY;
  const currentDryRun =
    brokerSnap.dryRun !== null ? brokerSnap.dryRun : null;

  return (
    <div>
      <Nav current="/live-enable" />
      <main className="mx-auto max-w-3xl px-6 py-8 space-y-6">
        <div>
          <h1 className="text-xl font-semibold">Live trading enable</h1>
          <p className="text-sm text-[var(--muted)]">
            Promotes the engine from{" "}
            <code className="font-mono">dry_run=true</code> to{" "}
            <code className="font-mono">dry_run=false</code> at runtime via
            the <code className="font-mono">runtime_settings</code> table.
            All four gates must be green before the Promote button enables.
          </p>
        </div>

        <PromoteForm
          checklist={checklist}
          currentDryRun={currentDryRun}
          serviceRoleConfigured={serviceRoleConfigured}
        />

        <div className="rounded-md border border-[var(--border)] bg-[var(--surface-muted)] p-3 text-xs text-[var(--muted)]">
          <p className="mb-1 font-medium text-[var(--fg)]">How this works</p>
          <ol className="list-decimal space-y-1 pl-5">
            <li>
              Promote writes <code className="font-mono">{`{value: false}`}</code>{" "}
              to <code className="font-mono">runtime_settings.dry_run_override</code>{" "}
              and a <code className="font-mono">LIVE_ENABLE</code> row to{" "}
              <code className="font-mono">audit_log</code>.
            </li>
            <li>
              The engine reads that row at the start of every heartbeat (~60 s
              cadence), overlays it on{" "}
              <code className="font-mono">cfg.broker.dry_run</code>, and emits
              <code className="font-mono">DRY_RUN_FLIPPED</code> the first
              cycle the value changes.
            </li>
            <li>
              Subsequent <code className="font-mono">place_order()</code>{" "}
              calls hit IBKR for real. The PaperAccountGuard still blocks any
              non-paper account_id, so a misconfigured live account
              cannot accidentally place orders.
            </li>
          </ol>
        </div>
      </main>
    </div>
  );
}
