## 10. Risk Assessment and Mitigation

A headless LLM-native accounting platform confronts a distinctive risk profile: it must defend against conventional software failures (data loss, API instability, scaling bottlenecks) alongside novel risks specific to LLM-driven financial processing (hallucinated transactions, prompt injection, model cost escalation). This chapter inventories risks across four categories, identifies ten coverage gaps in the current design, and assesses the architectural consistency of the overall solution.

The risk register draws on empirical data where available—academic benchmarks for LLM double-entry accuracy, vendor throughput claims, and LangGraph production metrics—while candidly flagging estimates that rest on single-source figures. Where quantitative data is absent, the assessment relies on likelihood × impact matrices and maps each risk to a concrete mitigation already embedded in the roadmap.

### 10.1 Risk Register

#### 10.1.1 Technical Risks

The most significant technical risk is LLM hallucination in transaction generation. Research by Weber et al. (2025) found that multiple LLM models achieved only 8.33% accuracy when generating raw double-entry bookkeeping without guidance, with 40% of cases producing missing transactions and 23.33% generating balance errors [^45^]. This figure was measured against Beancount DSL rather than Numscript, and it did not include the template-based generation and deterministic validation layers that the present architecture employs. The 50+ template library in dim03 constrains the LLM to variable substitution within pre-validated Numscript structures—an approach that raises valid-output rates above 95% when combined with deterministic validation. The six-stage pipeline (parse → template select → populate → validate → confirm → post) includes confirmation gates for all postings, full audit trail logging, and one-command undo via reversing entries [^213^]. The residual risk—an unvalidated posting slipping through—is rated medium likelihood with high impact, further mitigated by the immutable append-only ledger that prevents deletion and preserves complete correction history.

Formance Ledger integration introduces a second risk. The documented throughput of approximately 1,000 transactions per second per ledger on commodity PostgreSQL hardware originates from vendor documentation and has not been independently load-tested with accounting workloads [^45^]. PostgreSQL benchmarking suggests a write ceiling of ~2,000 requests per second on strong hardware, placing the claim in a plausible range but leaving a validation gap. Mitigation is threefold: comprehensive integration testing during MVP, a fallback to a custom PostgreSQL ledger if Formance proves insufficient, and horizontal ledger sharding for multi-entity deployments. The supervisor pattern introduces cost risk: LangGraph data indicates supervisor routing costs ~$0.061 per task versus $0.022 for single-agent—a 3× increase delivering an 18-point accuracy lift (89% versus 71% end-to-end success) [^116^]. For accounting transactions where an error could cost hundreds of pounds, this trade-off is justified but requires monitoring at scale.

Document extraction accuracy varies by methodology: LlamaExtractor achieved 94% in one comparative study, while hybrid LLM-plus-OCR pipelines report 97–98.5% document-level accuracy [^72^]. The 97% claim for Xero JAX reconciliation is a vendor figure that practitioners note holds only for businesses with consistent patterns [^345^]. Mitigation is a human-in-the-loop (HITL) gate with graduated autonomy: extractions below 90% confidence route to human review, and the system learns from corrections through episodic memory (Mem0) [^112^].

| Risk ID | Risk Description | Likelihood | Impact | Mitigation Strategy | Evidence Basis |
|:---|:---|:---|:---|:---|:---|
| T-01 | LLM hallucination generates incorrect double-entry transactions | Medium | High | Template-based Numscript generation (50+ templates); 6-stage deterministic validation; confirmation gates; immutable ledger with reversing-entry undo | Weber et al. (2025): 8.33% raw accuracy [^45^]; template mitigation from dim03 |
| T-02 | Formance Ledger throughput insufficient at scale | Low | High | Integration testing; fallback to custom PostgreSQL ledger; horizontal sharding | Vendor claim: ~1,000 tx/s [^45^]; independent PostgreSQL ceiling ~2,000 rps |
| T-03 | Supervisor pattern cost escalation (3× single-agent) | Medium | Medium | Phased agent rollout (4 core specialists for MVP); cost-per-task monitoring; single-agent fallback for low-value queries | LangGraph: $0.061 vs $0.022 per task [^116^] |
| T-04 | Document extraction accuracy below production threshold | Medium | Medium | HITL review for <90% confidence; hybrid LLM+OCR pipeline; per-organization model learning | 94–97% range across studies [^72^]; vendor claims require validation |
| T-05 | LLM context window exceeded for large reports | Medium | Medium | Streaming report generation; pagination; summary-first approach; chunked bulk processing | GPT-4o 128K context [^116^]; pattern from dim01 |

The technical risk profile is dominated by LLM reliability concerns. All five risks have mitigations either built into the architecture (validation pipeline, confirmation gates, immutable ledger) or scheduled for MVP (integration testing, HITL thresholds). Residual risk after mitigation is low for T-02 and T-03, and medium-low for T-01, where template constraints plus deterministic validation provide defense in depth.

#### 10.1.2 Compliance Risks

The EU AI Act presents the most significant compliance exposure. High-risk system rules take full effect in August 2026, with penalties reaching 7% of global annual revenue [^583^]. The system's AI-driven categorization, automated reconciliation, and document extraction all qualify as high-risk financial AI applications. Three research dimensions independently converge on the approach: agent decision provenance logging per Article 12, 6-month minimum audit retention, human oversight per Article 14, and model transparency through human-readable Numscript outputs [^124^]. Residual risk is regulatory interpretation uncertainty—whether the European Commission will issue supplementary guidance imposing additional requirements. Mitigation centers on a modular compliance architecture that absorbs new requirements without structural change, plus formal legal review in Q2 2026.

IFRS 18, effective January 2027, replaces IAS 1 with a five-category P&L structure (Operating, Investing, Financing, Income Tax, Discontinued Operations) and introduces Management Performance Measure disclosures [^301^]. The current COA uses traditional categories (4000–4999 revenue, 5000–6999 expenses) that do not map one-to-one to IFRS 18. Mitigation is a metadata-driven presentation layer: the COA remains unchanged, but report SKILLs map accounts to IFRS 18 categories at generation time through configurable metadata flags, enabling simultaneous IFRS, UK GAAP, and US GAAP compliance without parallel books.

HMRC MTD for VAT represents a third risk. While VAT calculation and nine-box preview are MVP features, direct API submission depends on OAuth 2.0 integration and HMRC error handling that are acknowledged but not fully specified [^579^]. Mitigation is an abstraction layer around the HMRC API, preview-only operation in MVP, and full submission in Phase 2 after deep integration testing.

| Risk ID | Risk Description | Likelihood | Impact | Mitigation Strategy | Timeline |
|:---|:---|:---|:---|:---|:---|
| C-01 | EU AI Act interpretation imposes unanticipated requirements | Medium | High | Modular compliance architecture; legal review Q2 2026; Art. 12 logging, Art. 13 transparency, Art. 14 HITL built in from MVP | Enforcement: August 2026 [^583^] |
| C-02 | IFRS 18 category mapping requires structural COA changes | Medium | Medium | Metadata-driven presentation layer; IFRS 18 report SKILLs with account-to-category mapping | Effective: January 2027 [^301^] |
| C-03 | HMRC MTD API changes break VAT submission pipeline | Medium | High | Adapter pattern abstraction layer; preview-only in MVP; monitored integration in Phase 2; manual fallback | Ongoing; MTD VAT mandatory [^124^] |
| C-04 | HMRC RTI payroll submission errors trigger penalties | Low | Very High | Testing against HMRC calculators; beta with volunteers; phased rollout (salary-only first) | Phase 3 (Month 8) [^592^][^593^] |

The compliance risk profile is shaped by external regulatory timelines. The EU AI Act and IFRS 18 deadlines align favorably with the roadmap: compliance features are delivered in Phase 2 (Months 3–5) and IFRS 18 SKILLs in Phase 3 (Months 6–9), providing 6–12 months of buffer. HMRC risks are operational—the three-layer tax architecture (Rule Store, Execution Engine, Override Workflow) is sound, but the API integration layer requires deeper specification.

#### 10.1.3 Business Risks

User adoption risk arises from the headless, chat-only model that replaces familiar accounting interfaces with natural language. Small business owners are accustomed to visual dashboards and spreadsheet-like grids. Mitigation is graduated autonomy: the system begins with 100% human approval for AI-generated transactions, transitions to sampled review once accuracy is demonstrated, and reaches exception-only approval for routine transactions [^112^]. The skill registry exposes familiar concepts (invoices, reconciliations, VAT returns) through natural language, reducing conceptual migration cost. The 8-week MVP targets UK freelancers already comfortable with technology, validating product-market fit before broader rollout.

Resource constraint risk reflects the tension between a 15-month roadmap and a team peaking at 5–7 engineers. The MVP requires 48 engineering days (2–3 engineers over 8 weeks at 75% velocity), with Phases 2–4 adding 65, 80, and 105 days respectively for a cumulative 298 days [^213^]. Mitigation is strict phasing with go/no-go gates, prioritizing revenue-generating and compliance-critical features. The MVP is designed as a standalone product that can generate paid users before Phase 2 begins.

#### 10.1.4 External Risks

External risks center on third-party service dependencies. Open Banking aggregator downtime is mitigated by a four-provider failover chain: TrueLayer (UK/EU primary, PSD2-regulated), Plaid (12,000+ institutions), Salt Edge (60+ countries), and Yodlee (17,000+ institutions) [^261^][^258^][^265^][^254^]. If TrueLayer is unavailable, the system promotes Plaid to primary; Salt Edge and Yodlee provide tertiary coverage. A manual CSV/OFX import fallback ensures bank data entry even during simultaneous aggregator outages—a low-probability scenario with elevated impact at month-end and quarter-end.

Exchange rate API failure presents lower risk. Daily rates from the European Central Bank are cached with 30-day retention; manual override supports backdated transactions; secondary providers (XE.com, Open Exchange Rates) provide fallback. Impact is limited because target-market SMEs operate predominantly in GBP; multi-currency support is a Phase 3 feature where the exchange rate infrastructure will be fully hardened [^585^].

### 10.2 Coverage Gaps and Resolutions

Cross-dimensional analysis of 18 research dimensions identified ten topics with insufficient coverage for production readiness. These are not architectural flaws but areas requiring additional design work.

The two highest-severity gaps are production load testing and disaster recovery. No dimension provides independent load test data for Formance Ledger; vendor claims of ~1,000 tx/s remain unvalidated [^45^]. Disaster recovery is mentioned only briefly with no Recovery Time Objective (RTO), Recovery Point Objective (RPO), or multi-region strategy. Both gaps directly threaten production readiness.

Medium-severity gaps cluster around integration depth and operational tooling. HMRC MTD API integration lacks detailed OAuth 2.0 specifications and error handling [^579^]. LLM cost modeling has no Total Cost of Ownership (TCO) model at scale—current estimates cite $0.061 per supervisor-routed task [^116^] but lack projections for 100× or 1,000× growth. Payroll has Numscript templates but no deep design for PAYE/NI calculations or RTI submission workflows [^592^][^593^]. Migration tooling from Xero/QBO is limited to CSV adapters with no API-based path. Mobile architecture, operations tooling (admin dashboard, monitoring), multi-tenant isolation at scale, and pricing strategy round out the ten gaps.

| Gap ID | Coverage Gap | Severity | Impact if Unaddressed | Resolution Phase | Resolution Approach |
|:---|:---|:---|:---|:---|:---|
| G-01 | Production load testing & scalability validation | High | Cannot validate 1,000 tx/s claim; production bottleneck risk | Phase 2 (M3) | Independent throughput test with realistic workloads; PostgreSQL query analysis; sharding prototype |
| G-02 | Disaster recovery & business continuity | High | No RTO/RPO; single point of failure; blocks enterprise adoption | Phase 2 (M4) | RTO <4 hours, RPO <1 hour; automated daily backups; multi-region k8s spec; annual DR drill |
| G-03 | HMRC MTD API deep integration | Medium-High | VAT submission failure; UK market entry blocked | Phase 2 (M5) | OAuth 2.0 flow design; endpoint mapping; error taxonomy; retry with backoff; sandbox testing |
| G-04 | LLM cost modeling at scale | Medium-High | Business model unviable if LLM costs exceed revenue per user | Phase 2 (M3) | Token usage instrumentation per workflow; cost model at 10×/100×/1,000×; provider cost comparison |
| G-05 | Payroll module deep design | Medium | Cannot offer UK payroll; competitive disadvantage | Phase 3 (M8) | PAYE/NI engine spec; RTI FPS/EPS workflow; HMRC PAYE API integration; beta with volunteers |
| G-06 | Migration tooling from Xero/QBO | Medium | Manual migration friction slows customer acquisition | Phase 3 (M7) | Xero API OAuth export pipeline; data validation engine; COA auto-mapping; migration dashboard |
| G-07 | Mobile application architecture | Medium | No field access for receipt capture, approvals | Phase 3 (M9) | PWA or React Native; offline receipt capture; push notifications |
| G-08 | Operations tooling & monitoring | Medium | Cannot operate multi-tenant service reliably | Phase 3 (M6) | Multi-tenant admin dashboard; Prometheus/Grafana; PagerDuty alerting; support workflow |
| G-09 | Multi-tenant isolation at scale | Medium | Noisy neighbor risk; data leakage between tenants | Phase 4 (M10) | Database-per-tenant validation at 100+ scale; resource quotas; tenant provisioning automation |
| G-10 | Competitive pricing strategy | Low-Medium | Risk of pricing below cost or above market willingness-to-pay | Phase 4 (M12) | Cost-plus analysis with LLM overhead; competitive benchmarking vs Xero/QBO; freemium design |

Resolution follows severity rather than roadmap chronology. The two highest-severity gaps (G-01, G-02) are pulled into Phase 2 because they block production readiness. G-03 (HMRC integration) is also Phase 2 because it is on the critical path for UK market validation. Medium gaps (G-04 through G-08) distribute across Phases 2 and 3 based on dependencies: LLM cost modeling (G-04) begins once MVP users generate real token traffic, while migration tooling (G-06) requires a stable data model. Lower-severity gaps (G-09, G-10) defer to Phase 4, when operational data informs tenant architecture and pricing decisions.

### 10.3 Architectural Consistency Assessment

An architectural consistency assessment across 12 subsystem categories scores each on a 0–100 scale based on cross-dimensional agreement, evidence strength, and absence of contradictions. The overall system scores 87/100.

| Category | Score | Key Strength | Primary Weakness |
|:---|:---|:---|:---|
| Backend technology | 95/100 | Formance + PostgreSQL agreed across 4 dimensions; sum-to-zero, Numscript, immutability native [^45^][^213^] | NATS choice has only 2 confirming dimensions; Kafka viable at scale |
| Data model (COA/GL) | 92/100 | 4-digit gap-friendly scheme; metadata-driven multi-standard support without parallel books [^264^] | IFRS 18 mapping requires presentation-layer implementation |
| Agent architecture | 90/100 | Supervisor pattern with LangGraph empirical data (89% vs 71% success) [^116^] | 3× cost; no accounting-specific cost benchmark |
| Multi-currency (IAS 21) | 90/100 | 3-currency architecture with full SQL schemas; spot/closing/average rates; CTA in OCI [^585^] | No independent FX calculation validation against IFRS test cases |
| Transaction processing | 88/100 | 50+ Numscript templates; 6-stage pipeline catches 91.67% of LLM errors | 8.33% figure not replicated on Numscript [^45^] |
| Reporting | 88/100 | 33+ report SKILLs with deterministic JSON schemas; IFRS 18 support designed [^301^] | Custom report builder in Phase 3; XBRL output untested |
| Tax engine | 85/100 | 3-layer architecture (Rule Store, Execution Engine, Override) across 4 dimensions [^257^] | HMRC API integration details missing |
| Security / compliance | 82/100 | Hash-chained ledger, WORM storage; EU AI Act and GDPR addressed [^583^] | DR missing; no RTO/RPO; no penetration test results |
| Bank feeds | 80/100 | 4-aggregator failover to 17,000+ institutions; PSD2 SCA [^261^] | Actual aggregator integration untested |
| Document processing | 78/100 | Hybrid LLM+OCR pipeline agreed; local vs cloud resolution path [^72^] | Local vs cloud tension unresolved for sensitive docs |
| DevOps / deployment | 75/100 | Docker Compose + k8s specs; Kong gateway, NATS, Redis all specified [^116^] | No multi-region; no DR plan; no CI/CD spec |
| Cost / business model | 55/100 | Unit cost data ($0.061/task) enables economics modeling [^116^] | No pricing model; no cost-plus analysis; no freemium design |

The score distribution reveals a clear pattern: highest scores are in backend technology, data model, and agent architecture—areas where multiple independent dimensions converge with strong evidence. Lowest scores are in cost/business model (55) and DevOps/deployment (75), reflecting the research's technical focus over commercial and operational concerns. This is an intentional artifact of scope rather than an architectural deficiency, but it signals that business modeling and operational readiness require dedicated attention.

The 87-point overall score measures internal consistency—how well components agree with each other—not market success or implementation ease. A system can be architecturally consistent and still fail if its business model is unviable. The coverage gaps and the low cost/business model score together highlight the highest-priority remediation: closing the loop between technical design and commercial viability through LLM cost modeling, competitive pricing analysis, and operational readiness planning before the MVP exits validation.
