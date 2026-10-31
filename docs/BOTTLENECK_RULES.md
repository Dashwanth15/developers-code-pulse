# DEVELOPERS CODE PULSE (DCP)
## Bottleneck Detection Rules & Methodology Specification

---

### 1. Detection Rule Catalog

| Rule ID | Category | Detection Metric | Trigger Threshold | Baseline SLA |
| :--- | :--- | :--- | :--- | :--- |
| **BOT-01** | PR Review Delay | Median TTFR & Pending Queue | $\text{TTFR} \ge 12\text{h}$ or Queue $\ge 3$ PRs | $8.0\text{h}$ |
| **BOT-02** | Approval Delay | Approval Turnaround & Rounds | Turnaround $\ge 18\text{h}$ or Rounds $\ge 2.0$ | $12.0\text{h}$ |
| **BOT-03** | Merge Delay | Approved Unmerged Post-Approval Lag | Approved unmerged $\ge 12\text{h}$ or Merge $\ge 24\text{h}$ | $0.0\text{h}$ / $12.0\text{h}$ |
| **BOT-04** | Reviewer Capacity | Gini Index & Top Share % | Gini $> 0.35$ or Max Share $\ge 45\%$ | $0.30$ |
| **BOT-05** | PR Size Divergence | Large-to-Small PR Merge Ratio | Large/Small merge latency $\ge 2.5\times$ | $1.5\times$ |
| **BOT-06** | Repository Backlog | Cycle Time & Merge Completion Rate | Cycle $\ge 48\text{h}$ or Merge Rate $< 60\%$ | $24.0\text{h}$ / $80\%$ |

---

### 2. Detailed Rule Specifications

#### Rule BOT-01: PR Review Delay
- **Target Condition**: Pull requests waiting excessive periods before initial peer feedback or large unreviewed queues.
- **Formulas**:
  $$\text{TTFR} = \min_{r \in \text{PeerReviews}} (T_{r} - T_{\text{PR\_created}})$$
- **Exclusion Rules**: Self-reviews ($R_{\text{reviewer}} = R_{\text{author}}$) and automated bot reviews (`user_type != 'User'`) are strictly excluded.
- **Severity**:
  - `CRITICAL`: Median TTFR $\ge 48\text{h}$
  - `HIGH`: Median TTFR $\ge 24\text{h}$
  - `MEDIUM`: Median TTFR $\ge 12\text{h}$
  - `LOW`: $< 12\text{h}$

#### Rule BOT-02: Approval Turnaround Delay
- **Target Condition**: Protracted iterations or delays between first feedback and formal sign-off.
- **Formulas**:
  $$\text{Turnaround} = T_{\text{first\_approval}} - T_{\text{first\_qualifying\_review}}$$
- **Severity**:
  - `CRITICAL`: Turnaround $\ge 72\text{h}$ or Review Rounds $\ge 4.0$
  - `HIGH`: Turnaround $\ge 36\text{h}$ or Review Rounds $\ge 2.5$
  - `MEDIUM`: Turnaround $\ge 18\text{h}$ or Review Rounds $\ge 2.0$
  - `LOW`: $< 18\text{h}$

#### Rule BOT-03: Merge Delay
- **Target Condition**: Changes that are fully approved by peers and CI but remain unmerged in trunk branches.
- **Formulas**:
  $$\text{PostApprovalLag} = T_{\text{now}} - T_{\text{latest\_approval}}$$
- **Severity**:
  - `CRITICAL`: Average lag $\ge 48\text{h}$
  - `HIGH`: Average lag $\ge 24\text{h}$
  - `MEDIUM`: Average lag $\ge 12\text{h}$
  - `LOW`: $< 12\text{h}$

#### Rule BOT-04: Reviewer Capacity & Load Concentration
- **Target Condition**: Review workload concentrated in too few team members, creating single points of failure.
- **Formulas**:
  $$G = \frac{\sum_{i=1}^n \sum_{j=1}^n |R_i - R_j|}{2n \sum_{i=1}^n R_i}$$
  $$\text{MaxShare} = \frac{\max(R_i)}{\sum R_i} \times 100\%$$
- **Severity**:
  - `CRITICAL`: $G \ge 0.60$ or $\text{MaxShare} \ge 60\%$
  - `HIGH`: $G \ge 0.45$ or $\text{MaxShare} \ge 45\%$
  - `MEDIUM`: $G \ge 0.35$
  - `LOW`: $G < 0.35$

#### Rule BOT-05: PR Size Latency Divergence
- **Target Condition**: Disproportionate merge delays on oversized pull requests (>500 lines) relative to small PRs (<100 lines).
- **Formulas**:
  $$\text{DivergenceRatio} = \frac{\bar{T}_{\text{merge, large}}}{\bar{T}_{\text{merge, small}}}$$
- **Severity**:
  - `HIGH`: Divergence $\ge 4.0\times$
  - `MEDIUM`: Divergence $\ge 2.5\times$
  - `LOW`: $< 2.5\times$
- **Ethical Caveat**: Does not assume developer fault; highlights review cognitive overload and testing friction.

#### Rule BOT-06: Repository Backlog & Macro Cycle Time
- **Target Condition**: Repositories where total cycle time is high and merge completion is low, resulting in accumulating work-in-progress (WIP).
- **Severity**:
  - `CRITICAL`: Cycle time $\ge 96\text{h}$ or (Merge Rate $< 40\%$ and Cycle Time $\ge 48\text{h}$)
  - `HIGH`: Cycle time $\ge 48\text{h}$ or Merge Rate $< 60\%$
  - `MEDIUM`: Cycle time $\ge 24\text{h}$ or Merge Rate $< 75\%$
  - `LOW`: Cycle time $< 24\text{h}$

---

### 3. Confidence Evaluation Methodology

Confidence measures statistical sample size completeness and pattern reliability:

| Confidence Level | Sample Size | Classification Meaning |
| :--- | :--- | :--- |
| **LOW** | $< 5$ observed items | **Operational Threshold Alert**: Observed data exceeds hard thresholds, but sample size is too small to claim a statistically established historical baseline. |
| **MEDIUM** | $5 - 14$ observed items | **Emerging Baseline**: Pattern is verified across a representative sample size. |
| **HIGH** | $\ge 15$ observed items | **Verified Trend**: Statistically robust dataset confirming systemic friction. |

---

### 4. Known Limitations

1. **GitHub Discussion Comments**: Line-by-line review comment threads that do not trigger formal PR review submissions are tracked as `COMMENTED` reviews when submitted through the GitHub review interface.
2. **External CI Latencies**: External CI build durations (e.g. Jenkins/CircleCI) are captured indirectly through the post-approval merge lag when auto-merge is waiting for green status checks.
3. **Draft Pull Requests**: Draft PRs are intentionally excluded from active review queue alerts until marked "Ready for Review".
