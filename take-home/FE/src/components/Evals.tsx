import { useState } from "react";
import {
  runHarness,
  runAgentSdk,
  runTests,
  type HarnessResult,
  type HarnessStrategyResult,
  type AgentSdkResult,
  type AgentSdkStrategyResult,
  type TestsResult,
} from "../api";
import styles from "./Evals.module.css";

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
            ))}
          </tbody>
        </table>

        {expanded && (
          <HarnessDetail
            result={data.results.find((r) => r.strategy === expanded)!}
          />
        )}
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
            ))}
          </tbody>
        </table>

        {expanded && (
          <AgentSdkDetail
            result={data.results.find((r) => r.strategy === expanded)!}
          />
        )}
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
                <span key={i} className={styles.toolCallTag}>
                  {tc.tool}
                  {tc.input && (
                    <>
                      <span className={styles.toolCallArrow}>&rarr;</span>
                      <span className={styles.toolCallInput}>
                        {typeof tc.input === "string"
                          ? tc.input
                          : JSON.stringify(tc.input)}
                      </span>
                    </>
                  )}
                </span>
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
/*  Main Evals Page                                                    */
/* ------------------------------------------------------------------ */

export default function Evals({ onBack }: { onBack: () => void }) {
  const [harnessResult, setHarnessResult] = useState<HarnessResult | null>(
    null
  );
  const [agentSdkResult, setAgentSdkResult] =
    useState<AgentSdkResult | null>(null);
  const [testsResult, setTestsResult] = useState<TestsResult | null>(null);
  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleRunHarness = async () => {
    setLoading("Running harness comparison across memory strategies...");
    setError(null);
    setHarnessResult(null);
    try {
      const result = await runHarness();
      setHarnessResult(result);
    } catch (err) {
      setError(
        `Harness failed: ${err instanceof Error ? err.message : "Unknown error"}`
      );
    } finally {
      setLoading(null);
    }
  };

  const handleRunAgentSdk = async () => {
    setLoading(
      "Running Agent SDK comparison with memory tools..."
    );
    setError(null);
    setAgentSdkResult(null);
    try {
      const result = await runAgentSdk();
      setAgentSdkResult(result);
    } catch (err) {
      setError(
        `Agent SDK failed: ${err instanceof Error ? err.message : "Unknown error"}`
      );
    } finally {
      setLoading(null);
    }
  };

  const handleRunTests = async () => {
    setLoading("Running pytest suite...");
    setError(null);
    setTestsResult(null);
    try {
      const result = await runTests();
      setTestsResult(result);
    } catch (err) {
      setError(
        `Tests failed: ${err instanceof Error ? err.message : "Unknown error"}`
      );
    } finally {
      setLoading(null);
    }
  };

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

        {harnessResult && <HarnessResults data={harnessResult} />}
        {agentSdkResult && <AgentSdkResults data={agentSdkResult} />}
        {testsResult && <TestResults data={testsResult} />}

        {!harnessResult && !agentSdkResult && !testsResult && !loading && (
          <div className={styles.emptyResults}>
            Run an eval to see results here
          </div>
        )}
      </div>
    </div>
  );
}
