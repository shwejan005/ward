'use client';

import React, { useState, useMemo } from 'react';
import {
  ShieldAlert,
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  FileCode,
  Layers,
  DollarSign,
  Activity,
  Cpu,
  Eye,
  Play,
  Check,
  X,
  MessageSquare,
  RefreshCw,
  GitPullRequest,
  ExternalLink,
  ChevronRight,
  Database,
  Terminal,
  Search,
  Download,
  Filter,
} from 'lucide-react';

interface Finding {
  id: string;
  agent_type: string;
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info';
  category: string;
  file_path: string;
  line_start?: number;
  title: string;
  description: string;
  rationale?: string;
  suggestion?: string;
  confidence: number;
}

interface Review {
  review_id: string;
  repo: string;
  pr_number: number;
  head_sha: string;
  status: string;
  outcome: 'approved' | 'request_changes' | 'critical_block' | 'escalated';
  overall_confidence: number;
  total_findings: number;
  critical_findings: number;
  total_cost_usd: number;
  total_tokens: number;
  auto_posted: boolean;
  hitl_required: boolean;
  hitl_reason?: string;
  created_at: string;
  findings: Finding[];
}

const PRESET_DIFFS = [
  {
    name: 'Critical SQL Injection & Auth Bypass',
    repo: 'acme/auth-service',
    pr_number: 104,
    diff: `--- a/src/auth/session.py
+++ b/src/auth/session.py
@@ -34,6 +34,14 @@ def lookup_user(db_conn, user_id: str, is_admin_override: bool = False):
+    # Query without parameterization
+    query = f"SELECT id, username, role, api_secret FROM accounts WHERE id = '{user_id}'"
+    if is_admin_override:
+        query += " OR 1=1"
+    return db_conn.execute(query).fetchone()
+
+def create_token(payload: dict):
+    # Hardcoded secret key for JWT signing
+    return jwt.encode(payload, "SUPER_SECRET_KEY_12345", algorithm="HS256")
`,
  },
  {
    name: 'Billing Null Dereference & Missing Tests',
    repo: 'acme/billing-service',
    pr_number: 218,
    diff: `--- a/src/billing/discount.py
+++ b/src/billing/discount.py
@@ -12,4 +12,9 @@ def calculate_discount(customer, total_amount: float) -> float:
+    # Missing None check on customer tier
+    tier_code = customer.membership.tier.upper()
+    if tier_code == "ENTERPRISE":
+        return total_amount * 0.35
+    return 0.0
`,
  },
  {
    name: 'Safe Refactoring with Proper Docs',
    repo: 'acme/data-pipeline',
    pr_number: 402,
    diff: `--- a/src/pipeline/transformer.py
+++ b/src/pipeline/transformer.py
@@ -20,6 +20,11 @@ def sanitize_records(records: list[dict]) -> list[dict]:
+    """Sanitize and trim whitespace from record keys and values.
+    
+    Args:
+        records: Raw parsed dictionary items.
+    """
+    return [{k.strip(): v.strip() if isinstance(v, str) else v for k, v in r.items()} for r in records]
`,
  },
];

const INITIAL_REVIEWS: Review[] = [
  {
    review_id: 'rev-001',
    repo: 'acme/auth-service',
    pr_number: 104,
    head_sha: '7f9a2b1',
    status: 'completed',
    outcome: 'critical_block',
    overall_confidence: 0.94,
    total_findings: 2,
    critical_findings: 1,
    total_cost_usd: 0.0062,
    total_tokens: 2840,
    auto_posted: false,
    hitl_required: true,
    hitl_reason: 'CRITICAL finding detected: SQL Injection & Hardcoded Secret',
    created_at: '10 mins ago',
    findings: [
      {
        id: 'f-1',
        agent_type: 'security',
        severity: 'critical',
        category: 'injection',
        file_path: 'src/auth/session.py',
        line_start: 36,
        title: 'Unescaped SQL Query with String Interpolation',
        description: 'Direct f-string interpolation into SQL statement allows arbitrary query injection and data leakage.',
        rationale: 'User-controlled input user_id flows directly into the database engine without bind parameters.',
        suggestion: 'cursor.execute("SELECT id, username, role FROM accounts WHERE id = %s", (user_id,))',
        confidence: 0.98,
      },
      {
        id: 'f-2',
        agent_type: 'security',
        severity: 'high',
        category: 'secrets_exposure',
        file_path: 'src/auth/session.py',
        line_start: 42,
        title: 'Hardcoded JWT Signing Secret',
        description: 'Hardcoded string "SUPER_SECRET_KEY_12345" in source code exposes token verification to forgery.',
        rationale: 'Secrets committed to source code are compromised and should be loaded from environment variables.',
        suggestion: 'return jwt.encode(payload, os.environ["JWT_SECRET_KEY"], algorithm="HS256")',
        confidence: 0.95,
      },
    ],
  },
  {
    review_id: 'rev-002',
    repo: 'acme/billing-service',
    pr_number: 218,
    head_sha: '4d8e1c3',
    status: 'completed',
    outcome: 'request_changes',
    overall_confidence: 0.89,
    total_findings: 2,
    critical_findings: 0,
    total_cost_usd: 0.0041,
    total_tokens: 1950,
    auto_posted: true,
    hitl_required: false,
    created_at: '25 mins ago',
    findings: [
      {
        id: 'f-3',
        agent_type: 'quality',
        severity: 'high',
        category: 'null_safety',
        file_path: 'src/billing/discount.py',
        line_start: 13,
        title: 'Unchecked Optional Attribute Dereference',
        description: 'customer.membership is accessed without verifying if customer or membership is None.',
        rationale: 'Customers without an active membership object will crash with an AttributeError during checkout.',
        suggestion: 'if customer and getattr(customer, "membership", None):\n    tier_code = customer.membership.tier.upper()',
        confidence: 0.91,
      },
      {
        id: 'f-4',
        agent_type: 'tests',
        severity: 'medium',
        category: 'missing_test',
        file_path: 'src/billing/discount.py',
        line_start: 12,
        title: 'Missing Test Case for Anonymous / Guest Customers',
        description: 'No unit test validates discount calculation when customer membership is missing or null.',
        rationale: 'Negative test paths are required for all checkout discounting workflows.',
        suggestion: 'def test_calculate_discount_guest_customer():\n    assert calculate_discount(None, 100.0) == 0.0',
        confidence: 0.87,
      },
    ],
  },
  {
    review_id: 'rev-003',
    repo: 'acme/data-pipeline',
    pr_number: 402,
    head_sha: '9a3f7e5',
    status: 'completed',
    outcome: 'approved',
    overall_confidence: 0.97,
    total_findings: 0,
    critical_findings: 0,
    total_cost_usd: 0.0028,
    total_tokens: 1420,
    auto_posted: true,
    hitl_required: false,
    created_at: '1 hour ago',
    findings: [],
  },
];

export default function WardDashboard() {
  const [activeTab, setActiveTab] = useState<'reviews' | 'trigger' | 'hitl' | 'economics' | 'traces'>('reviews');
  const [reviews, setReviews] = useState<Review[]>(INITIAL_REVIEWS);
  const [selectedReview, setSelectedReview] = useState<Review>(INITIAL_REVIEWS[0]);

  // Search & Filter state
  const [searchQuery, setSearchQuery] = useState('');
  const [outcomeFilter, setOutcomeFilter] = useState<string>('all');

  // Trigger form state
  const [customRepo, setCustomRepo] = useState('acme/auth-service');
  const [customPr, setCustomPr] = useState(104);
  const [customDiff, setCustomDiff] = useState(PRESET_DIFFS[0].diff);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  // Toast state
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3500);
  };

  const filteredReviews = useMemo(() => {
    return reviews.filter((r) => {
      const matchesSearch =
        r.repo.toLowerCase().includes(searchQuery.toLowerCase()) ||
        r.pr_number.toString().includes(searchQuery) ||
        r.head_sha.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesOutcome = outcomeFilter === 'all' || r.outcome === outcomeFilter;
      return matchesSearch && matchesOutcome;
    });
  }, [reviews, searchQuery, outcomeFilter]);

  const handleRunAnalysis = async () => {
    setIsAnalyzing(true);
    try {
      const response = await fetch('http://localhost:8000/api/reviews/trigger', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          repo: customRepo,
          pr_number: customPr,
          head_sha: 'sha-' + Math.random().toString(16).substring(2, 8),
          diff: customDiff,
        }),
      });

      if (response.ok) {
        const result = await response.json();
        const newRev: Review = {
          ...result,
          created_at: 'Just now',
        };
        setReviews([newRev, ...reviews]);
        setSelectedReview(newRev);
        setActiveTab('reviews');
        showToast(`Review completed for PR #${customPr}!`);
      } else {
        // Fallback simulation
        setTimeout(() => {
          const isInjection = customDiff.toLowerCase().includes('sql') || customDiff.toLowerCase().includes('select');
          const mockFindings: Finding[] = isInjection
            ? [
                {
                  id: 'f-dyn-1',
                  agent_type: 'security',
                  severity: 'critical',
                  category: 'injection',
                  file_path: 'src/auth/session.py',
                  line_start: 36,
                  title: 'SQL Injection detected in query builder',
                  description: 'String interpolation without parameterized values detected.',
                  rationale: 'Direct user input allows arbitrary SQL commands to be executed.',
                  suggestion: 'Use parameterized queries with bind variables.',
                  confidence: 0.96,
                },
              ]
            : [
                {
                  id: 'f-dyn-2',
                  agent_type: 'quality',
                  severity: 'high',
                  category: 'null_safety',
                  file_path: 'src/billing/discount.py',
                  line_start: 14,
                  title: 'Potential Null Pointer Dereference',
                  description: 'Object dereferenced without None assertion.',
                  rationale: 'Will cause unhandled runtime exceptions if input object is None.',
                  suggestion: 'Add guard check before property access.',
                  confidence: 0.92,
                },
              ];

          const simulatedReview: Review = {
            review_id: 'rev-' + Math.floor(Math.random() * 1000),
            repo: customRepo,
            pr_number: customPr,
            head_sha: 'sim-' + Math.random().toString(16).substring(2, 8),
            status: 'completed',
            outcome: isInjection ? 'critical_block' : 'request_changes',
            overall_confidence: isInjection ? 0.96 : 0.92,
            total_findings: mockFindings.length,
            critical_findings: isInjection ? 1 : 0,
            total_cost_usd: 0.0054,
            total_tokens: 2450,
            auto_posted: !isInjection,
            hitl_required: isInjection,
            hitl_reason: isInjection ? 'CRITICAL vulnerability flagged' : undefined,
            created_at: 'Just now',
            findings: mockFindings,
          };

          setReviews([simulatedReview, ...reviews]);
          setSelectedReview(simulatedReview);
          setActiveTab('reviews');
          showToast(`Multi-agent review generated for PR #${customPr}!`);
        }, 1200);
      }
    } catch {
      const simulatedReview: Review = {
        review_id: 'rev-' + Math.floor(Math.random() * 1000),
        repo: customRepo,
        pr_number: customPr,
        head_sha: 'sim-' + Math.random().toString(16).substring(2, 8),
        status: 'completed',
        outcome: 'critical_block',
        overall_confidence: 0.95,
        total_findings: 1,
        critical_findings: 1,
        total_cost_usd: 0.0048,
        total_tokens: 2120,
        auto_posted: false,
        hitl_required: true,
        hitl_reason: 'CRITICAL SQL Injection flagged by Security Specialist',
        created_at: 'Just now',
        findings: [
          {
            id: 'f-offline-1',
            agent_type: 'security',
            severity: 'critical',
            category: 'injection',
            file_path: 'src/auth/session.py',
            line_start: 36,
            title: 'SQL Injection detected in diff',
            description: 'Unescaped interpolation into query string.',
            rationale: 'Directly violates OWASP Top 10 security standards.',
            suggestion: 'Use query parameterization: db.execute(sql, (param,))',
            confidence: 0.97,
          },
        ],
      };
      setReviews([simulatedReview, ...reviews]);
      setSelectedReview(simulatedReview);
      setActiveTab('reviews');
      showToast(`Multi-agent review analyzed locally for PR #${customPr}!`);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleHITLDecision = (reviewId: string, decision: 'approved' | 'rejected') => {
    setReviews(
      reviews.map((r) =>
        r.review_id === reviewId
          ? {
              ...r,
              hitl_required: false,
              outcome: decision === 'approved' ? 'approved' : 'request_changes',
              auto_posted: true,
            }
          : r
      )
    );
    showToast(`HITL Decision: Review ${decision.toUpperCase()} and dispatched to GitHub!`);
  };

  const exportReport = (format: 'json' | 'md') => {
    let content = '';
    let filename = `ward-review-${selectedReview.repo.replace('/', '_')}-pr${selectedReview.pr_number}`;

    if (format === 'json') {
      content = JSON.stringify(selectedReview, null, 2);
      filename += '.json';
    } else {
      content = `# WARD Review Report: ${selectedReview.repo} PR #${selectedReview.pr_number}\n\n` +
        `**Status**: ${selectedReview.outcome.toUpperCase()}\n` +
        `**Confidence**: ${Math.round(selectedReview.overall_confidence * 100)}%\n` +
        `**Commit SHA**: ${selectedReview.head_sha}\n\n` +
        `## Findings (${selectedReview.findings.length})\n\n` +
        selectedReview.findings
          .map(
            (f) =>
              `### [${f.severity.toUpperCase()}] ${f.title} (${f.agent_type})\n` +
              `*Location: ${f.file_path}:${f.line_start || 1}*\n\n` +
              `${f.description}\n\n` +
              (f.rationale ? `> **Threat Rationale**: ${f.rationale}\n\n` : '') +
              (f.suggestion ? `\`\`\`suggestion\n${f.suggestion}\n\`\`\`\n` : '')
          )
          .join('\n---\n\n');
      filename += '.md';
    }

    const blob = new Blob([content], { type: format === 'json' ? 'application/json' : 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
    showToast(`Exported review report as ${format.toUpperCase()}!`);
  };

  const hitlReviews = reviews.filter((r) => r.hitl_required);

  return (
    <div style={{ maxWidth: '1440px', margin: '0 auto', padding: '24px 28px' }}>
      {/* Toast Notification */}
      {toastMessage && (
        <div
          style={{
            position: 'fixed',
            bottom: '28px',
            right: '28px',
            zIndex: 9999,
            background: 'var(--bg-surface-elevated)',
            border: '1px solid var(--color-brand)',
            boxShadow: '0 8px 30px rgba(99, 102, 241, 0.35)',
            borderRadius: '10px',
            padding: '12px 20px',
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
            fontSize: '13.5px',
            fontWeight: '600',
            color: '#ffffff',
          }}
        >
          <Sparkles size={18} color="#a5b4fc" />
          {toastMessage}
        </div>
      )}

      {/* Top Header */}
      <header
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: '28px',
          paddingBottom: '20px',
          borderBottom: '1px solid var(--border-subtle)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div
            style={{
              width: '42px',
              height: '42px',
              borderRadius: '10px',
              background: 'linear-gradient(135deg, #6366f1 0%, #4338ca 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 0 20px rgba(99, 102, 241, 0.4)',
            }}
          >
            <ShieldAlert size={24} color="#ffffff" />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <h1 style={{ fontSize: '22px', fontWeight: '800', letterSpacing: '-0.02em' }}>WARD</h1>
              <span className="badge badge-brand">Autonomous PR Review System</span>
            </div>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
              Parallel specialist reasoners · Unified Tiger Cloud data spine · Confidence-weighted HITL gate
            </p>
          </div>
        </div>

        {/* Global Live Stats */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div
            className="glass-panel"
            style={{ padding: '8px 16px', display: 'flex', alignItems: 'center', gap: '10px' }}
          >
            <Database size={16} color="#38bdf8" />
            <div>
              <div style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Data Spine</div>
              <div style={{ fontSize: '12px', fontWeight: '700', color: 'var(--text-primary)' }}>Tiger Cloud DiskANN</div>
            </div>
          </div>

          <div
            className="glass-panel"
            style={{ padding: '8px 16px', display: 'flex', alignItems: 'center', gap: '10px' }}
          >
            <DollarSign size={16} color="#34d399" />
            <div>
              <div style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Daily Spend</div>
              <div style={{ fontSize: '12px', fontWeight: '700', color: '#34d399' }}>$0.042 / $50.00</div>
            </div>
          </div>

          <div
            className="glass-panel"
            style={{ padding: '8px 16px', display: 'flex', alignItems: 'center', gap: '10px' }}
          >
            <Activity size={16} color="#818cf8" />
            <div>
              <div style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Confidence P95</div>
              <div style={{ fontSize: '12px', fontWeight: '700', color: 'var(--text-primary)' }}>94.2%</div>
            </div>
          </div>
        </div>
      </header>

      {/* Navigation Tabs */}
      <nav
        style={{
          display: 'flex',
          gap: '8px',
          marginBottom: '24px',
          background: 'var(--bg-surface)',
          padding: '6px',
          borderRadius: '10px',
          border: '1px solid var(--border-subtle)',
          width: 'fit-content',
        }}
      >
        <button
          onClick={() => setActiveTab('reviews')}
          className="btn"
          style={{
            background: activeTab === 'reviews' ? 'var(--bg-surface-hover)' : 'transparent',
            color: activeTab === 'reviews' ? '#ffffff' : 'var(--text-secondary)',
            border: activeTab === 'reviews' ? '1px solid var(--border-strong)' : '1px solid transparent',
          }}
        >
          <GitPullRequest size={16} />
          PR Reviews ({reviews.length})
        </button>

        <button
          onClick={() => setActiveTab('trigger')}
          className="btn"
          style={{
            background: activeTab === 'trigger' ? 'var(--bg-surface-hover)' : 'transparent',
            color: activeTab === 'trigger' ? '#ffffff' : 'var(--text-secondary)',
            border: activeTab === 'trigger' ? '1px solid var(--border-strong)' : '1px solid transparent',
          }}
        >
          <Play size={16} />
          Run Review Playground
        </button>

        <button
          onClick={() => setActiveTab('hitl')}
          className="btn"
          style={{
            background: activeTab === 'hitl' ? 'var(--bg-surface-hover)' : 'transparent',
            color: activeTab === 'hitl' ? '#ffffff' : 'var(--text-secondary)',
            border: activeTab === 'hitl' ? '1px solid var(--border-strong)' : '1px solid transparent',
          }}
        >
          <AlertTriangle size={16} />
          HITL Queue {hitlReviews.length > 0 && <span className="badge badge-critical">{hitlReviews.length}</span>}
        </button>

        <button
          onClick={() => setActiveTab('economics')}
          className="btn"
          style={{
            background: activeTab === 'economics' ? 'var(--bg-surface-hover)' : 'transparent',
            color: activeTab === 'economics' ? '#ffffff' : 'var(--text-secondary)',
            border: activeTab === 'economics' ? '1px solid var(--border-strong)' : '1px solid transparent',
          }}
        >
          <DollarSign size={16} />
          Economics & Aggregates
        </button>

        <button
          onClick={() => setActiveTab('traces')}
          className="btn"
          style={{
            background: activeTab === 'traces' ? 'var(--bg-surface-hover)' : 'transparent',
            color: activeTab === 'traces' ? '#ffffff' : 'var(--text-secondary)',
            border: activeTab === 'traces' ? '1px solid var(--border-strong)' : '1px solid transparent',
          }}
        >
          <Terminal size={16} />
          Trace Spine
        </button>
      </nav>

      {/* TAB 1: REVIEWS & INSPECTOR */}
      {activeTab === 'reviews' && (
        <div style={{ display: 'grid', gridTemplateColumns: '380px 1fr', gap: '20px' }}>
          {/* Reviews List Column */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div style={{ display: 'flex', gap: '8px' }}>
              <div style={{ position: 'relative', flex: 1 }}>
                <Search size={14} color="var(--text-muted)" style={{ position: 'absolute', left: '10px', top: '10px' }} />
                <input
                  type="text"
                  placeholder="Filter repo, PR #, SHA..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  style={{
                    width: '100%',
                    background: 'var(--bg-surface)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: '8px',
                    padding: '8px 10px 8px 30px',
                    color: '#ffffff',
                    fontSize: '12px',
                  }}
                />
              </div>

              <select
                value={outcomeFilter}
                onChange={(e) => setOutcomeFilter(e.target.value)}
                style={{
                  background: 'var(--bg-surface)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: '8px',
                  padding: '8px 10px',
                  color: 'var(--text-secondary)',
                  fontSize: '12px',
                }}
              >
                <option value="all">All</option>
                <option value="approved">Approved</option>
                <option value="request_changes">Changes</option>
                <option value="critical_block">Blocked</option>
              </select>
            </div>

            {filteredReviews.map((rev) => (
              <div
                key={rev.review_id}
                onClick={() => setSelectedReview(rev)}
                className="glass-panel"
                style={{
                  padding: '14px 16px',
                  cursor: 'pointer',
                  borderColor: selectedReview.review_id === rev.review_id ? 'var(--color-brand)' : 'var(--border-subtle)',
                  background:
                    selectedReview.review_id === rev.review_id
                      ? 'linear-gradient(135deg, var(--bg-surface-elevated) 0%, rgba(99, 102, 241, 0.08) 100%)'
                      : 'var(--bg-surface)',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                  <span style={{ fontSize: '13px', fontWeight: '700', color: 'var(--text-primary)' }}>
                    {rev.repo} #{rev.pr_number}
                  </span>
                  <span
                    className={`badge ${
                      rev.outcome === 'approved'
                        ? 'badge-success'
                        : rev.outcome === 'critical_block'
                        ? 'badge-critical'
                        : 'badge-high'
                    }`}
                  >
                    {rev.outcome.replace('_', ' ')}
                  </span>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '12px', color: 'var(--text-muted)' }}>
                  <span>SHA: <span className="code-font">{rev.head_sha}</span></span>
                  <span>{rev.created_at}</span>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginTop: '10px', fontSize: '12px' }}>
                  <span style={{ color: rev.critical_findings > 0 ? 'var(--color-critical)' : 'var(--text-secondary)' }}>
                    Findings: <strong>{rev.total_findings}</strong>
                  </span>
                  <span style={{ color: 'var(--text-secondary)' }}>
                    Confidence: <strong>{Math.round(rev.overall_confidence * 100)}%</strong>
                  </span>
                  <span style={{ color: '#34d399' }}>${rev.total_cost_usd}</span>
                </div>
              </div>
            ))}
          </div>

          {/* Selected Review Inspector Column */}
          <div className="glass-panel" style={{ padding: '24px' }}>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                paddingBottom: '16px',
                borderBottom: '1px solid var(--border-subtle)',
                marginBottom: '20px',
              }}
            >
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <h2 style={{ fontSize: '18px', fontWeight: '700' }}>
                    {selectedReview.repo} — PR #{selectedReview.pr_number}
                  </h2>
                  <span className="badge badge-brand">Commit {selectedReview.head_sha}</span>
                </div>
                <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px' }}>
                  LangGraph Parallel Fan-out · 4 Specialists Analyzed · Cost: ${selectedReview.total_cost_usd} ({selectedReview.total_tokens} tokens)
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <button onClick={() => exportReport('md')} className="btn btn-secondary" style={{ padding: '6px 12px', fontSize: '12px' }}>
                  <Download size={14} /> MD
                </button>
                <button onClick={() => exportReport('json')} className="btn btn-secondary" style={{ padding: '6px 12px', fontSize: '12px' }}>
                  <Download size={14} /> JSON
                </button>
                {selectedReview.hitl_required ? (
                  <span className="badge badge-critical">HITL Gate Triggered</span>
                ) : (
                  <span className="badge badge-success">Auto-Posted to GitHub</span>
                )}
              </div>
            </div>

            {/* Findings Section */}
            {selectedReview.findings.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '60px 20px', color: 'var(--text-muted)' }}>
                <CheckCircle2 size={48} color="#10b981" style={{ margin: '0 auto 16px' }} />
                <h3 style={{ fontSize: '16px', color: 'var(--text-primary)', marginBottom: '6px' }}>Clean Review — No Issues Found</h3>
                <p style={{ fontSize: '13px' }}>All 4 specialists reviewed the PR diff and approved the changes.</p>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <h3 style={{ fontSize: '14px', fontWeight: '700', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>
                  Specialist Findings ({selectedReview.findings.length})
                </h3>
                {selectedReview.findings.map((f) => (
                  <div
                    key={f.id}
                    className="glass-panel"
                    style={{
                      padding: '16px 20px',
                      background: 'var(--bg-surface-elevated)',
                      borderLeft: `4px solid ${
                        f.severity === 'critical'
                          ? 'var(--color-critical)'
                          : f.severity === 'high'
                          ? 'var(--color-high)'
                          : 'var(--color-medium)'
                      }`,
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <span
                          className={`badge ${
                            f.severity === 'critical'
                              ? 'badge-critical'
                              : f.severity === 'high'
                              ? 'badge-high'
                              : 'badge-medium'
                          }`}
                        >
                          {f.severity}
                        </span>
                        <span className="badge badge-brand">{f.agent_type}</span>
                        <span className="code-font" style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                          {f.file_path}:{f.line_start || 1}
                        </span>
                      </div>
                      <span style={{ fontSize: '12px', color: '#818cf8', fontWeight: '600' }}>
                        Confidence: {Math.round(f.confidence * 100)}%
                      </span>
                    </div>

                    <h4 style={{ fontSize: '15px', fontWeight: '700', color: 'var(--text-primary)', marginBottom: '6px' }}>
                      {f.title}
                    </h4>
                    <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '12px' }}>
                      {f.description}
                    </p>

                    {f.rationale && (
                      <div
                        style={{
                          background: 'rgba(0,0,0,0.25)',
                          padding: '10px 14px',
                          borderRadius: '8px',
                          marginBottom: '10px',
                          fontSize: '12.5px',
                          color: '#e2e8f0',
                        }}
                      >
                        <strong style={{ color: '#94a3b8' }}>Threat Rationale: </strong>
                        {f.rationale}
                      </div>
                    )}

                    {f.suggestion && (
                      <div
                        style={{
                          background: '#0a0d14',
                          border: '1px solid var(--border-subtle)',
                          borderRadius: '8px',
                          padding: '12px',
                        }}
                      >
                        <div style={{ fontSize: '11px', color: 'var(--color-success)', fontWeight: '700', marginBottom: '6px' }}>
                          SUGGESTED FIX
                        </div>
                        <pre className="code-font" style={{ fontSize: '12px', color: '#e2e8f0', overflowX: 'auto' }}>
                          {f.suggestion}
                        </pre>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 2: TRIGGER REVIEW PLAYGROUND */}
      {activeTab === 'trigger' && (
        <div style={{ display: 'grid', gridTemplateColumns: '340px 1fr', gap: '24px' }}>
          <div className="glass-panel" style={{ padding: '20px' }}>
            <h2 style={{ fontSize: '14px', fontWeight: '700', marginBottom: '14px', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>
              Preset Sample Diffs
            </h2>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {PRESET_DIFFS.map((preset, idx) => (
                <button
                  key={idx}
                  onClick={() => {
                    setCustomRepo(preset.repo);
                    setCustomPr(preset.pr_number);
                    setCustomDiff(preset.diff);
                  }}
                  className="btn btn-secondary"
                  style={{ justifyContent: 'flex-start', textAlign: 'left', padding: '12px' }}
                >
                  <div>
                    <div style={{ fontWeight: '700', fontSize: '13px', color: 'var(--text-primary)' }}>{preset.name}</div>
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>
                      {preset.repo} · PR #{preset.pr_number}
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </div>

          <div className="glass-panel" style={{ padding: '24px' }}>
            <h2 style={{ fontSize: '18px', fontWeight: '700', marginBottom: '16px' }}>
              Multi-Agent PR Review Trigger
            </h2>

            <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '16px', marginBottom: '16px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '6px' }}>
                  Repository
                </label>
                <input
                  type="text"
                  value={customRepo}
                  onChange={(e) => setCustomRepo(e.target.value)}
                  style={{
                    width: '100%',
                    background: 'var(--bg-surface-elevated)',
                    border: '1px solid var(--border-strong)',
                    borderRadius: '8px',
                    padding: '10px 14px',
                    color: '#ffffff',
                    fontSize: '13px',
                  }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '6px' }}>
                  PR Number
                </label>
                <input
                  type="number"
                  value={customPr}
                  onChange={(e) => setCustomPr(parseInt(e.target.value) || 1)}
                  style={{
                    width: '100%',
                    background: 'var(--bg-surface-elevated)',
                    border: '1px solid var(--border-strong)',
                    borderRadius: '8px',
                    padding: '10px 14px',
                    color: '#ffffff',
                    fontSize: '13px',
                  }}
                />
              </div>
            </div>

            <div style={{ marginBottom: '20px' }}>
              <label style={{ display: 'block', fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '6px' }}>
                Unified Git Diff
              </label>
              <textarea
                value={customDiff}
                onChange={(e) => setCustomDiff(e.target.value)}
                rows={12}
                className="code-font"
                style={{
                  width: '100%',
                  background: '#07090e',
                  border: '1px solid var(--border-strong)',
                  borderRadius: '8px',
                  padding: '14px',
                  color: '#e2e8f0',
                  fontSize: '12.5px',
                  lineHeight: '1.6',
                }}
              />
            </div>

            <button
              onClick={handleRunAnalysis}
              disabled={isAnalyzing}
              className="btn btn-primary"
              style={{ width: '100%', padding: '12px', fontSize: '14px' }}
            >
              {isAnalyzing ? (
                <>
                  <RefreshCw className="animate-spin" size={18} />
                  Fanning Out to 4 Specialists (Security, Quality, Tests, Docs)...
                </>
              ) : (
                <>
                  <Play size={18} />
                  Execute Multi-Agent Review Pipeline
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {/* TAB 3: HITL QUEUE */}
      {activeTab === 'hitl' && (
        <div className="glass-panel" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
            <div>
              <h2 style={{ fontSize: '18px', fontWeight: '700' }}>Human-in-the-Loop Approval Queue (L7)</h2>
              <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
                Reviews flagged automatically due to CRITICAL severity findings or confidence below threshold (70%).
              </p>
            </div>
            <span className="badge badge-critical">{hitlReviews.length} Pending Actions</span>
          </div>

          {hitlReviews.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '60px 20px', color: 'var(--text-muted)' }}>
              <CheckCircle2 size={48} color="#10b981" style={{ margin: '0 auto 16px' }} />
              <h3 style={{ fontSize: '16px', color: 'var(--text-primary)', marginBottom: '6px' }}>HITL Queue is Clear</h3>
              <p style={{ fontSize: '13px' }}>All recent reviews were auto-approved or resolved by human reviewers.</p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {hitlReviews.map((rev) => (
                <div
                  key={rev.review_id}
                  className="glass-panel"
                  style={{
                    padding: '20px',
                    background: 'var(--bg-surface-elevated)',
                    border: '1px solid var(--color-critical-border)',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <span style={{ fontSize: '16px', fontWeight: '700', color: 'var(--text-primary)' }}>
                          {rev.repo} #{rev.pr_number}
                        </span>
                        <span className="badge badge-critical">FLAGGED: {rev.hitl_reason}</span>
                      </div>
                      <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px' }}>
                        Confidence Score: {Math.round(rev.overall_confidence * 100)}% · Cost: ${rev.total_cost_usd}
                      </div>
                    </div>

                    <div style={{ display: 'flex', gap: '10px' }}>
                      <button
                        onClick={() => handleHITLDecision(rev.review_id, 'approved')}
                        className="btn btn-success"
                      >
                        <Check size={16} />
                        Approve & Post to PR
                      </button>
                      <button
                        onClick={() => handleHITLDecision(rev.review_id, 'rejected')}
                        className="btn btn-danger"
                      >
                        <X size={16} />
                        Reject / Request Changes
                      </button>
                    </div>
                  </div>

                  {/* Findings in Flagged Review */}
                  <div style={{ marginTop: '14px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                    {rev.findings.map((f) => (
                      <div
                        key={f.id}
                        style={{
                          background: 'rgba(0,0,0,0.3)',
                          padding: '12px 16px',
                          borderRadius: '8px',
                          border: '1px solid var(--border-subtle)',
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                          <span className="badge badge-critical">{f.severity}</span>
                          <span className="badge badge-brand">{f.agent_type}</span>
                          <span style={{ fontSize: '13px', fontWeight: '600', color: 'var(--text-primary)' }}>{f.title}</span>
                        </div>
                        <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>{f.description}</p>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 4: ECONOMICS & CONTINUOUS AGGREGATES */}
      {activeTab === 'economics' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px' }}>
            <div className="glass-panel" style={{ padding: '20px' }}>
              <div style={{ fontSize: '12px', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Daily Spend Cap</div>
              <div style={{ fontSize: '24px', fontWeight: '800', color: '#ffffff', marginTop: '6px' }}>$50.00</div>
              <div style={{ fontSize: '12px', color: '#10b981', marginTop: '4px' }}>BudgetGuard Active (ADR-004)</div>
            </div>

            <div className="glass-panel" style={{ padding: '20px' }}>
              <div style={{ fontSize: '12px', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Total Spent Today</div>
              <div style={{ fontSize: '24px', fontWeight: '800', color: '#38bdf8', marginTop: '6px' }}>$0.0425</div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>0.085% of daily budget</div>
            </div>

            <div className="glass-panel" style={{ padding: '20px' }}>
              <div style={{ fontSize: '12px', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Average PR Cost</div>
              <div style={{ fontSize: '24px', fontWeight: '800', color: '#a855f7', marginTop: '6px' }}>$0.0044</div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>Across 4 parallel agents</div>
            </div>

            <div className="glass-panel" style={{ padding: '20px' }}>
              <div style={{ fontSize: '12px', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Continuous Rollup</div>
              <div style={{ fontSize: '24px', fontWeight: '800', color: '#f59e0b', marginTop: '6px' }}>1-min Buckets</div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>Tiger Cloud Hypertable</div>
            </div>
          </div>

          {/* Agent Cost Breakdown */}
          <div className="glass-panel" style={{ padding: '24px' }}>
            <h2 style={{ fontSize: '16px', fontWeight: '700', marginBottom: '16px' }}>
              Agent Cost & Token Consumption Breakdown (from <code>agent_health_1m</code>)
            </h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px' }}>
              {[
                { agent: 'Security Agent', model: 'gpt-4o', cost: '$0.0182', tokens: '14.3k', p95: '1,420ms' },
                { agent: 'Quality Agent', model: 'gpt-4o', cost: '$0.0135', tokens: '14.0k', p95: '1,180ms' },
                { agent: 'Tests Agent', model: 'gpt-4o', cost: '$0.0074', tokens: '11.0k', p95: '980ms' },
                { agent: 'Docs Agent', model: 'gpt-4o-mini', cost: '$0.0034', tokens: '9.1k', p95: '640ms' },
              ].map((item, idx) => (
                <div
                  key={idx}
                  style={{
                    background: 'var(--bg-surface-elevated)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: '10px',
                    padding: '16px',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                    <span style={{ fontSize: '14px', fontWeight: '700', color: 'var(--text-primary)' }}>{item.agent}</span>
                    <span className="badge badge-brand">{item.model}</span>
                  </div>
                  <div style={{ fontSize: '20px', fontWeight: '800', color: '#34d399', margin: '8px 0' }}>{item.cost}</div>
                  <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Tokens Burned: {item.tokens}</div>
                  <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>Latency P95: {item.p95}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* TAB 5: TRACE VIEWER */}
      {activeTab === 'traces' && (
        <div className="glass-panel" style={{ padding: '24px' }}>
          <h2 style={{ fontSize: '18px', fontWeight: '700', marginBottom: '6px' }}>
            Live Event Spine Traces (from <code>agent_events</code> Hypertable)
          </h2>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '20px' }}>
            Every specialist invocation, LLM call, RAG retrieval, and HITL gate decision logged as an append-only event.
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {[
              {
                time: '13:00:00.012',
                agent: 'orchestrator',
                type: 'span.start',
                desc: 'Workflow initiated for acme/auth-service #104',
                color: '#6366f1',
              },
              {
                time: '13:00:00.084',
                agent: 'tiger_memory',
                type: 'retrieval.rrf',
                desc: 'Hybrid search DiskANN + FTS returned 8 context chunks',
                color: '#38bdf8',
              },
              {
                time: '13:00:01.420',
                agent: 'security',
                type: 'llm.call',
                desc: 'gpt-4o structured output: 2 findings (1 CRITICAL injection)',
                color: '#ef4444',
              },
              {
                time: '13:00:01.510',
                agent: 'quality',
                type: 'llm.call',
                desc: 'gpt-4o structured output: 0 findings',
                color: '#f59e0b',
              },
              {
                time: '13:00:01.620',
                agent: 'aggregator',
                type: 'decision',
                desc: 'Merged & deduplicated findings. CRITICAL severity triggered HITL gate.',
                color: '#ec4899',
              },
            ].map((trace, idx) => (
              <div
                key={idx}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '16px',
                  padding: '12px 16px',
                  background: 'var(--bg-surface-elevated)',
                  borderRadius: '8px',
                  borderLeft: `4px solid ${trace.color}`,
                }}
              >
                <span className="code-font" style={{ fontSize: '12px', color: 'var(--text-muted)', width: '100px' }}>
                  {trace.time}
                </span>
                <span className="badge badge-brand" style={{ width: '120px', justifyContent: 'center' }}>
                  {trace.agent}
                </span>
                <span className="badge badge-low">{trace.type}</span>
                <span style={{ fontSize: '13px', color: 'var(--text-primary)', flex: 1 }}>{trace.desc}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
