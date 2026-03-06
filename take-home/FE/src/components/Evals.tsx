import { useState, useEffect, useCallback } from "react";
import {
  runHarness,
  runAgentSdk,
  runTests,
  fetchEvalRuns,
  fetchEvalRun,
  type HarnessResult,
  type HarnessStrategyResult,
  type AgentSdkResult,
  type AgentSdkStrategyResult,
  type AgentSdkToolCall,
  type TestsResult,
  type EvalRunSummary,
  type EvalRunResult,
} from "../api";
import styles from "./Evals.module.css";

/* ------------------------------------------------------------------ */
/*  Helpers                                                             */
/* ------------------------------------------------------------------ */

const TYPE_LABELS: Record<string, string> = {
  harness: "Harness",
  agent_sdk: "Agent SDK",
  tests: "Tests",
};

function formatTime(iso: string) {
  const d = new Date(iso);
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/* ------------------------------------------------------------------ */
/*  Harness Results                                                    */
/* ------------------------------------------------------------------ */

function HarnessResults({ data }: { data: HarnessResult }) {
  const [expanded, setExpanded] = useState<string | null>(null);

  return (
    <div className={styles.resultSection}>
      <div className={styles.sectionHeader}>
        <span className={styles.sectionTitle}>Harness Recall Comparison</span>
        <span className={styles.badgeHarness}>LangChain</span>
      </div>
      <div className={styles.sectionBody}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Strategy</th>
              <th>Turn 7 (name + lang)</th>
              <th>Turn 8 (job)</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {data.results.map((r) => (
              <>
                <tr key={r.strategy}>
                  <td className={styles.strategyName}>
                    {r.description || r.strategy}
                  </td>
                  <td
                    className={
                      r.recall.turn_7.passed ? styles.pass : styles.fail
                    }
                  >
                    {r.recall.turn_7.passed
                      ? "PASS"
                      : `FAIL (${r.recall.turn_7.found.join(", ") || "none"})`}
                  </td>
                  <td
                    className={
                      r.recall.turn_8.passed ? styles.pass : styles.fail
                    }
                  >
                    {r.recall.turn_8.passed
                      ? "PASS"
                      : `FAIL (${r.recall.turn_8.found.join(", ") || "none"})`}
                  </td>
                  <td>
                    <button
                      className={styles.expandBtn}
                      onClick={() =>
                        setExpanded(
                          expanded === r.strategy ? null : r.strategy
                        )
                      }
                    >
                      {expanded === r.strategy ? "Hide" : "Details"}
                    </button>
                  </td>
                </tr>
                {expanded === r.strategy && (
                  <tr key={`${r.strategy}-detail`}>
                    <td colSpan={4} style={{ padding: 0 }}>
                      <HarnessDetail result={r} />
                    </td>
                  </tr>
                )}
              </>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function HarnessDetail({ result }: { result: HarnessStrategyResult }) {
  return (
    <div className={styles.turnDetail}>
      {result.responses.map((r) => (
        <div key={r.turn} className={styles.turnItem}>
          <span className={styles.turnLabel}>Turn {r.turn}</span>
          <p className={styles.turnUser}>User: {r.user}</p>
          <p className={styles.turnAssistant}>
            Assistant: {r.assistant.slice(0, 300)}
            {r.assistant.length > 300 && "..."}
          </p>
        </div>
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Agent SDK Results                                                  */
/* ------------------------------------------------------------------ */

function AgentSdkResults({ data }: { data: AgentSdkResult }) {
  const [expanded, setExpanded] = useState<string | null>(null);

  return (
    <div className={styles.resultSection}>
      <div className={styles.sectionHeader}>
        <span className={styles.sectionTitle}>
          Agent SDK Recall Comparison
        </span>
        <span className={styles.badgeSdk}>Agent SDK</span>
      </div>
      <div className={styles.sectionBody}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Strategy</th>
              <th>Turn 7 (name + lang)</th>
              <th>Turn 8 (job)</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {data.results.map((r) => (
              <>
                <tr key={r.strategy}>
                  <td className={styles.strategyName}>{r.strategy}</td>
                  <td
                    className={
                      r.recall.turn_7.passed ? styles.pass : styles.fail
                    }
                  >
                    {r.recall.turn_7.passed
                      ? "PASS"
                      : `FAIL (${r.recall.turn_7.found.join(", ") || "none"})`}
                  </td>
                  <td
                    className={
                      r.recall.turn_8.passed ? styles.pass : styles.fail
                    }
                  >
                    {r.recall.turn_8.passed
                      ? "PASS"
                      : `FAIL (${r.recall.turn_8.found.join(", ") || "none"})`}
                  </td>
                  <td>
                    <button
                      className={styles.expandBtn}
                      onClick={() =>
                        setExpanded(
                          expanded === r.strategy ? null : r.strategy
                        )
                      }
                    >
                      {expanded === r.strategy ? "Hide" : "Details"}
                    </button>
                  </td>
                </tr>
                {expanded === r.strategy && (
                  <tr key={`${r.strategy}-detail`}>
                    <td colSpan={4} style={{ padding: 0 }}>
                      <AgentSdkDetail result={r} />
                    </td>
                  </tr>
                )}
              </>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ToolCallIndicator({ tc }: { tc: AgentSdkToolCall }) {
  const inputStr =
    typeof tc.input === "string"
      ? tc.input
      : Object.values(tc.input).join(", ") || "{}";

  return (
    <div className={styles.toolCallPanel}>
      <div className={styles.toolCallHeader}>
        <span className={styles.toolCallName}>{tc.tool}</span>
        <span className={styles.toolCallSep}>&rarr;</span>
        <span className={styles.toolCallQuery}>{inputStr}</span>
      </div>
    </div>
  );
}

function AgentSdkDetail({ result }: { result: AgentSdkStrategyResult }) {
  return (
    <div className={styles.turnDetail}>
      {result.turns.map((t) => (
        <div key={t.turn} className={styles.turnItem}>
          <span className={styles.turnLabel}>Turn {t.turn}</span>
          <p className={styles.turnUser}>User: {t.user}</p>
          <p className={styles.turnAssistant}>
            Assistant: {t.assistant.slice(0, 300)}
            {t.assistant.length > 300 && "..."}
          </p>
          {t.tool_calls.length > 0 && (
            <div className={styles.toolCalls}>
              {t.tool_calls.map((tc, i) => (
                <ToolCallIndicator key={i} tc={tc} />
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Test Results                                                       */
/* ------------------------------------------------------------------ */

function TestResults({ data }: { data: TestsResult }) {
  const [showStdout, setShowStdout] = useState(false);

  return (
    <div className={styles.resultSection}>
      <div className={styles.sectionHeader}>
        <span className={styles.sectionTitle}>
          Test Results &mdash; {data.test_path}
        </span>
        <span className={styles.badgeTests}>pytest</span>
      </div>
      <div className={styles.sectionBody}>
        <div className={styles.testSummary}>
          <span className={`${styles.testStat} ${styles.pass}`}>
            {data.passed} passed
          </span>
          {data.failed > 0 && (
            <span className={`${styles.testStat} ${styles.fail}`}>
              {data.failed} failed
            </span>
          )}
          {data.errored > 0 && (
            <span
              className={styles.testStat}
              style={{ color: "var(--yellow)" }}
            >
              {data.errored} errored
            </span>
          )}
        </div>

        {data.tests.map((t, i) => (
          <div key={i} className={styles.testItem}>
            <span className={styles.testName}>{t.test}</span>
            <span
              className={`${styles.badge} ${
                t.status === "PASSED"
                  ? styles.badgePass
                  : t.status === "FAILED"
                  ? styles.badgeFail
                  : styles.badgeError
              }`}
            >
              {t.status}
            </span>
          </div>
        ))}

        {data.stdout && (
          <>
            <button
              className={styles.expandBtn}
              onClick={() => setShowStdout(!showStdout)}
              style={{ marginTop: 12 }}
            >
              {showStdout ? "Hide output" : "Show full output"}
            </button>
            {showStdout && <pre className={styles.stdout}>{data.stdout}</pre>}
          </>
        )}
        {data.stderr && <pre className={styles.stdout}>{data.stderr}</pre>}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Result renderer (dispatches by type)                               */
/* ------------------------------------------------------------------ */

function ResultView({ data }: { data: EvalRunResult }) {
  if (data.type === "harness") return <HarnessResults data={data as HarnessResult} />;
  if (data.type === "agent_sdk") return <AgentSdkResults data={data as AgentSdkResult} />;
  if (data.type === "tests") return <TestResults data={data as TestsResult} />;
  return null;
}

/* ------------------------------------------------------------------ */
/*  Run indicator                                                      */
/* ------------------------------------------------------------------ */

function RunIndicator({ data }: { data: EvalRunResult }) {
  return (
    <div className={styles.runIndicator}>
      <span className={styles.runIndicatorLabel}>Run</span>
      <span className={styles.runIndicatorId}>{data.run_id.slice(0, 8)}</span>
      <span className={styles.runIndicatorTime}>{formatTime(data.created_at)}</span>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main Evals Page                                                    */
/* ------------------------------------------------------------------ */

export default function Evals({ onBack }: { onBack: () => void }) {
  const [runs, setRuns] = useState<EvalRunSummary[]>([]);
  const [activeResult, setActiveResult] = useState<EvalRunResult | null>(null);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refreshRuns = useCallback(async () => {
    try {
      const list = await fetchEvalRuns();
      setRuns(list);
    } catch {
      /* silently ignore — runs list is supplementary */
    }
  }, []);

  useEffect(() => {
    refreshRuns();
  }, [refreshRuns]);

  const loadRun = async (runId: string) => {
    if (selectedRunId === runId) return;
    setSelectedRunId(runId);
    setError(null);
    try {
      const result = await fetchEvalRun(runId);
      setActiveResult(result);
    } catch {
      setError("Failed to load eval run.");
    }
  };

  const runAndShow = async (
    label: string,
    runner: () => Promise<EvalRunResult>
  ) => {
    setLoading(label);
    setError(null);
    setActiveResult(null);
    setSelectedRunId(null);
    try {
      const result = await runner();
      setActiveResult(result);
      setSelectedRunId(result.run_id);
      await refreshRuns();
    } catch (err) {
      setError(
        `${label} failed: ${err instanceof Error ? err.message : "Unknown error"}`
      );
    } finally {
      setLoading(null);
    }
  };

  const handleRunHarness = () =>
    runAndShow("Running harness comparison across memory strategies...", runHarness as () => Promise<EvalRunResult>);

  const handleRunAgentSdk = () =>
    runAndShow("Running Agent SDK comparison with memory tools...", runAgentSdk as () => Promise<EvalRunResult>);

  const handleRunTests = () =>
    runAndShow("Running pytest suite...", runTests as () => Promise<EvalRunResult>);

  const hasResults = activeResult !== null;

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <button className={styles.backBtn} onClick={onBack}>
          Back
        </button>
        <h1 className={styles.title}>Evals &amp; Harness</h1>
      </header>

      <div className={styles.content}>
        <div className={styles.evalGroups}>
          {/* Memory comparison group */}
          <div className={styles.evalGroup}>
            <div className={styles.groupLabel}>Memory Comparison</div>
            <div className={styles.groupButtons}>
              <button
                className={styles.runBtnAccent}
                onClick={handleRunHarness}
                disabled={!!loading}
              >
                <span className={styles.btnTitle}>Run Harness</span>
                <span className={styles.btnDesc}>
                  Direct strategy comparison via LangChain agent
                </span>
              </button>
              <button
                className={styles.runBtnAccent}
                onClick={handleRunAgentSdk}
                disabled={!!loading}
              >
                <span className={styles.btnTitle}>Run Agent SDK</span>
                <span className={styles.btnDesc}>
                  Tool-based memory via Claude Agent SDK
                </span>
              </button>
            </div>
          </div>

          {/* Test suite group */}
          <div className={styles.evalGroup}>
            <div className={styles.groupLabel}>Test Suite</div>
            <div className={styles.groupButtons}>
              <button
                className={styles.runBtn}
                onClick={handleRunTests}
                disabled={!!loading}
              >
                <span className={styles.btnTitle}>Run Tests</span>
                <span className={styles.btnDesc}>
                  Execute pytest eval suite
                </span>
              </button>
            </div>
          </div>
        </div>

        {loading && (
          <div className={styles.statusLoading}>
            <span className={styles.spinner} />
            {loading}
          </div>
        )}
        {error && <div className={styles.statusError}>{error}</div>}

        {/* Past runs list */}
        {runs.length > 0 && (
          <div className={styles.runsSection}>
            <div className={styles.runsSectionLabel}>Past Runs</div>
            <div className={styles.runsList}>
              {runs.map((r) => (
                <button
                  key={r.id}
                  className={`${styles.runItem} ${selectedRunId === r.id ? styles.runItemActive : ""}`}
                  onClick={() => loadRun(r.id)}
                >
                  <span className={styles.runItemType}>
                    {TYPE_LABELS[r.eval_type] || r.eval_type}
                  </span>
                  <span className={styles.runItemTime}>
                    {formatTime(r.created_at)}
                  </span>
                  <span className={styles.runItemId}>{r.id.slice(0, 8)}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Active result display */}
        {activeResult && (
          <>
            <RunIndicator data={activeResult} />
            <ResultView data={activeResult} />
          </>
        )}

        {!hasResults && !loading && runs.length === 0 && (
          <div className={styles.emptyResults}>
            Run an eval to see results here
          </div>
        )}
      </div>
    </div>
  );
}
