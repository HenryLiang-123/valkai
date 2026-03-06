import { useState } from "react";
import {
  runHarness,
  runTests,
  type HarnessResult,
  type HarnessStrategyResult,
  type TestsResult,
} from "../api";
import styles from "./Evals.module.css";

function HarnessResults({ data }: { data: HarnessResult }) {
  const [expanded, setExpanded] = useState<string | null>(null);

  return (
    <div className={styles.section}>
      <h3 className={styles.sectionTitle}>Harness Recall Comparison</h3>
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
              <td style={{ color: "#fff", fontWeight: 500 }}>{r.strategy}</td>
              <td className={r.recall.turn_7.pass ? styles.pass : styles.fail}>
                {r.recall.turn_7.pass
                  ? "PASS"
                  : `FAIL (found: ${r.recall.turn_7.found.join(", ") || "none"})`}
              </td>
              <td className={r.recall.turn_8.pass ? styles.pass : styles.fail}>
                {r.recall.turn_8.pass
                  ? "PASS"
                  : `FAIL (found: ${r.recall.turn_8.found.join(", ") || "none"})`}
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
        <StrategyDetail
          result={data.results.find((r) => r.strategy === expanded)!}
        />
      )}
    </div>
  );
}

function StrategyDetail({ result }: { result: HarnessStrategyResult }) {
  return (
    <div className={styles.turnDetail}>
      {result.responses.map((r) => (
        <div key={r.turn} style={{ marginBottom: 8 }}>
          <p>
            <span className={styles.turnLabel}>Turn {r.turn}</span>
          </p>
          <p className={styles.turnUser}>User: {r.user}</p>
          <p className={styles.turnAssistant}>
            Assistant: {r.assistant.slice(0, 300)}
            {r.assistant.length > 300 && "..."}
          </p>
          {result.tool_calls
            .filter((tc) => tc.turn === r.turn)
            .map((tc, i) => (
              <span key={i} className={styles.toolCallTag}>
                {tc.tool}({JSON.stringify(tc.input)})
              </span>
            ))}
        </div>
      ))}
    </div>
  );
}

function TestResults({ data }: { data: TestsResult }) {
  const [showStdout, setShowStdout] = useState(false);

  return (
    <div className={styles.section}>
      <h3 className={styles.sectionTitle}>
        Test Results — {data.test_path}
      </h3>
      <div className={styles.summary}>
        <span className={styles.pass}>{data.passed} passed</span>
        {data.failed > 0 && (
          <span className={styles.fail}> · {data.failed} failed</span>
        )}
        {data.errored > 0 && (
          <span style={{ color: "#f59e0b" }}>
            {" "}
            · {data.errored} errored
          </span>
        )}
      </div>

      <div style={{ marginTop: 12 }}>
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
      </div>

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
  );
}

export default function Evals({ onBack }: { onBack: () => void }) {
  const [harnessResult, setHarnessResult] = useState<HarnessResult | null>(
    null
  );
  const [testsResult, setTestsResult] = useState<TestsResult | null>(null);
  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleRunHarness = async () => {
    setLoading("Running harness comparison...");
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

  const handleRunTests = async () => {
    setLoading("Running tests...");
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
        <h1 className={styles.title}>Evals & Harness</h1>
      </header>

      <div className={styles.content}>
        <div className={styles.actions}>
          <button
            className={styles.runBtn}
            onClick={handleRunHarness}
            disabled={!!loading}
          >
            Run Harness
          </button>
          <button
            className={styles.runBtn}
            onClick={handleRunTests}
            disabled={!!loading}
          >
            Run Tests
          </button>
        </div>

        {loading && <p className={styles.loading}>{loading}</p>}
        {error && <p className={styles.error}>{error}</p>}
        {harnessResult && <HarnessResults data={harnessResult} />}
        {testsResult && <TestResults data={testsResult} />}
      </div>
    </div>
  );
}
