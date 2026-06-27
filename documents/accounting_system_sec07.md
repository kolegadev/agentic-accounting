## 7. Security, Compliance and Audit Trail

An AI-native accounting system operates at the intersection of two of the most stringently regulated domains: financial record-keeping, where immutable audit trails are mandated by securities and tax law, and artificial intelligence, where emergent regulations impose novel obligations for transparency, human oversight, and decision provenance. The architecture must simultaneously satisfy the EU AI Act's high-risk system requirements (enforceable August 2026) [^500^], the General Data Protection Regulation (GDPR)'s right to erasure, SOC 2 Type II assurance expectations, and jurisdiction-specific tax regimes such as HMRC's Making Tax Digital (MTD). This chapter defines the security architecture, immutable audit trail design, and regulatory compliance framework that together resolve the apparent tension between these obligations.

### 7.1 Security Architecture

The security model follows a defense-in-depth strategy with cryptographic controls at every layer: authentication, authorization, encryption in transit and at rest, and multi-tenant data isolation. Each control is designed to satisfy overlapping requirements across multiple compliance frameworks simultaneously, avoiding the proliferation of framework-specific implementations.

#### 7.1.1 Authentication: OAuth 2.0 + PKCE

The primary authentication protocol is OAuth 2.0 with Proof Key for Code Exchange (PKCE) per RFC 9700, the current security best practice for native and single-page applications [^391^]. Access tokens are JSON Web Tokens (JWT) signed with RS256 (RSA with SHA-256), carrying a 30-minute expiry to limit the window of compromise. Each token embeds claims for user identity (`sub`), tenant scope (`org`), and role assignments (`roles`), enabling both authentication and coarse-grained authorization in a single round trip. Refresh tokens rotate on every use with a 60-day maximum lifetime, rendering stolen tokens useless once invalidated. For server-to-server integrations---such as connections to banking APIs or external ERP systems---mutual TLS (mTLS) provides certificate-based authentication that is resistant to credential replay attacks. Multi-factor authentication (MFA) via Time-based One-Time Password (TOTP) or WebAuthn/FIDO2 is mandatory for the Owner and Admin roles, and recommended for Accountant roles [^514^]. Identity provider support includes Google Workspace, Microsoft Entra ID, Okta, and Auth0, with SAML 2.0 available for legacy enterprise integration [^515^].

The authentication flow follows the standard OpenID Connect (OIDC) pattern: the user authenticates at the identity provider, receives an ID token and access token, and presents the access token at the API gateway where tenant scope and RBAC claims are validated before the request reaches any service [^515^] [^521^].

#### 7.1.2 RBAC: Five Roles with Middleware-Enforced Claim Validation

Role-based access control (RBAC) implements five predefined roles aligned with standard accounting separation-of-duties practice [^514^]. All permission checks are enforced at the middleware layer---never relying on client-side validation---with claims extracted from the JWT and validated against the endpoint's required role set on every request.

| Role | Ledger Access | Contacts | Reports | Settings | COA Edit | User Mgmt |
|------|-------------|----------|---------|----------|----------|-----------|
| Owner | Full read/write | Full | Full | Full | Yes | Yes |
| Admin | Full read/write | Full | Full | Most | Yes | Yes |
| Bookkeeper | Read/write | Read/write | Read-only | None | No | No |
| Accountant | Read/write | Read-only | Full (incl. export) | None | No | No |
| Viewer | Read-only | Read-only | Read-only | None | No | No |

The five-role structure directly implements SOC 2 Common Criteria CC6.3 (role-based access control) and supports SOX Section 404's separation-of-duties mandate. Sensitive operations enforce additional dual-control requirements: journal entry creation by a Bookkeeper requires approval by an Accountant or above; period-close requires that all entries be reviewed; chart-of-accounts changes are restricted to Admin; and AI model overrides require Accountant-level authorization with the override reason captured in the immutable audit trail [^514^]. Quarterly automated access reviews identify inactive accounts (>30 days unused) and flag them for offboarding, satisfying CC6.1 and CC6.3 simultaneously.

#### 7.1.3 Data Encryption: TLS 1.3, mTLS, TDE, and AES-256-GCM

Encryption is applied at four distinct layers, each addressing a specific threat model and compliance requirement.

| Layer | Technology | Standard | Threat Addressed |
|-------|-----------|----------|-----------------|
| In transit (external) | TLS 1.3 | IETF RFC 8446 | Eavesdropping, man-in-the-middle |
| In transit (internal) | mTLS over gRPC | X.509 v3 | Service impersonation, lateral movement |
| At rest (database) | PostgreSQL TDE + LUKS | AES-256 | Physical media theft, backup compromise |
| At rest (files) | MinIO server-side encryption | AES-256-GCM | Object storage breach |
| At rest (sensitive fields) | Application-level | AES-256-GCM | Insider threat, column-level exposure |

TLS 1.3 is mandatory for all external-facing connections, with TLS 1.2 permitted only as a fallback for legacy clients. The protocol's 1-RTT handshake reduces latency versus TLS 1.2's 2-RTT, while perfect forward secrecy (PFS) is enforced by default through ephemeral key exchange, ensuring that compromise of a long-term private key does not expose past session data [^546^]. Internal service-to-service communication over gRPC uses mutual TLS, where both client and server present X.509 certificates, preventing unauthorized services from interacting with the ledger or agent orchestrator even if they gain network access.

At the database layer, PostgreSQL Transparent Data Encryption (TDE) encrypts all data files, table indexes, and Write-Ahead Logs (WAL) with AES-256. The performance penalty is measured at less than 1% throughput reduction [^509^]. For deployments where TDE is unavailable, Linux Unified Key Setup (LUKS) provides full-disk encryption at the volume level. Files stored in MinIO---invoices, receipts, reports---are encrypted with AES-256-GCM, with each tenant's files isolated in a dedicated bucket. Application-level encryption protects the most sensitive fields: bank account numbers, tax identification numbers, and email addresses are encrypted with AES-256-GCM before storage, using per-tenant encryption keys managed through a Hardware Security Module (HSM) or cloud Key Management Service (KMS) at FIPS 140-2 Level 3 [^542^]. Tokenization replaces bank account numbers with reversible tokens for display purposes; only the last four digits are readable without decryption capability.

#### 7.1.4 Multi-Tenant Isolation

Multi-tenant isolation is achieved through a hybrid model that combines ledger-level, schema-level, and application-level separation. Formance's bucket mechanism maps each tenant to a distinct PostgreSQL schema, providing namespace isolation at the database level [^498^]. Within each bucket, the tenant's ledgers (general ledger, payroll, budget) are fully segregated. PostgreSQL Row-Level Security (RLS) policies enforce tenant filtering at the database query layer: every SELECT, INSERT, and UPDATE is automatically scoped to the tenant_id extracted from the JWT claim, so that even a SQL injection vulnerability cannot expose cross-tenant data [^561^].

Cache isolation uses key-prefixing: all Redis keys are prefixed with the tenant identifier (`{tenant_id}:{resource}`), preventing cache poisoning or leakage between tenants. Event streaming uses topic namespacing (`ledger.{tenant_id}.transactions.created`), ensuring that NATS consumers receive only their tenant's events. File storage uses per-tenant MinIO buckets with tenant-scoped access policies. This layered isolation---ledger, schema, RLS, cache prefix, topic namespace, and bucket separation---creates defense in depth against cross-tenant data exposure, a critical requirement for financial SaaS where a single leakage incident can destroy trust.

### 7.2 Immutable Audit Trail

The audit trail design must satisfy two fundamentally different requirements: financial ledger immutability (mandated by SOX, GAAP/IFRS, and tax law) and AI decision provenance (mandated by the EU AI Act). Rather than building separate systems, the architecture creates two linked audit streams---financial and AI---that share correlation identifiers, enabling end-to-end reconstruction from a user's natural language request through the AI's reasoning to the final ledger posting.

#### 7.2.1 Formance Hash-Chained Ledger

The financial ledger implements Formance's native hash-chained architecture, where every transaction is cryptographically linked to its predecessor [^499^]. Each posting record contains a SHA-256 hash computed over the concatenation of the transaction ID, timestamp, posting contents, and the previous transaction's hash. This Merkle-like chain creates tamper evidence: any retroactive modification of a historical transaction invalidates all subsequent hashes, detectable during routine verification-on-read operations.

Immutability is enforced at multiple levels. At the application layer, the postings table is append-only: no UPDATE or DELETE operations are permitted. Corrections---whether initiated by a human or triggered by an AI reversal workflow---are recorded as compensating entries that preserve the original transaction in the chain [^499^]. At the storage layer, Write-Once-Read-Many (WORM) format prevents edits or deletions at the filesystem level [^545^]. Idempotency keys on all posting operations ensure that duplicate submissions (from network retries or LLM re-execution) produce the same result without double-posting [^499^]. Every read operation can optionally verify the full hash chain back to the genesis transaction, providing cryptographic proof of ledger integrity for auditors.

#### 7.2.2 Conversational Audit Trail

The conversational audit trail is a cross-dimensional architectural feature that links the WebSocket chat interface (Section 4), the Plan-and-Execute agent workflow (Section 6), and the hash-chained ledger into a single tamper-evident chain. When a user submits a natural language request---for example, "Record a £500 payment from Acme Corp"---the following chain is constructed:

1. The natural language request is captured with nanosecond-precision timestamp and session correlation ID.
2. The supervisor agent's routing decision and the specialist agent's chain-of-thought reasoning are logged as structured events.
3. The generated Numscript (the human-readable transaction DSL) is recorded, serving as both the executable instruction and the explanation of the AI's intent.
4. The deterministic validation result (balance check, COA membership, duplicate detection) is appended.
5. The human approval decision---approved, rejected, or modified---with reviewer identity and reason is captured.
6. The final ledger posting is committed to the Formance hash chain, carrying the session correlation ID in its metadata.

All six links share a common `session_id` and `trace_id`, enabling auditors to reconstruct the complete causal chain from utterance to ledger entry. This exceeds traditional accounting audit trails, which record *what* happened but not *why* it happened in human-understandable form. The Numscript itself serves as a human-readable explanation of the AI's decision, satisfying EU AI Act Article 13 (transparency) without additional infrastructure.

#### 7.2.3 Agent Decision Provenance

Every AI agent decision that affects financial records produces a structured provenance record capturing the complete decision context. The provenance schema is designed to exceed EU AI Act Article 12 requirements while supporting post-market monitoring, incident investigation, and third-party conformity assessment [^504^] [^540^].

| Provenance Field | Content | Compliance Purpose |
|-----------------|---------|-------------------|
| `provenance_id` + timestamp | Unique identifier, ISO-8601 nanoseconds | Uniqueness, temporal ordering |
| Correlation IDs | session_id, trace_id, tenant_id, user_id | End-to-end traceability |
| Agent identity | Agent name, version, model provider, model version, owner | Accountability, model card linkage |
| Input | Transaction data, retrieved context, prompt hash | Reproducibility, input validation |
| Reasoning | Chain-of-thought, confidence score, uncertainty quantification (entropy, top-2 margin, OOD flag) | Explainability, accuracy assessment |
| Alternative options | Rejected categories with confidence scores | Transparency, override justification |
| Tool calls | Tool name, input, output, duration, success/failure | Action trace, performance monitoring |
| Output | Decision, category, tax treatment, general ledger entry | Financial impact documentation |
| Validation | Automated checks (balance, duplicate, COA), guardrail results | Quality assurance, accuracy per Art. 15 |
| Oversight | Review type (auto/human), reviewer_id, decision, override reason | Human oversight per Art. 14 |
| Policy events | Classification, risk level, GDPR lawful basis, retention tag | Governance, legal basis, lifecycle |

The provenance record is cryptographically signed with HMAC-SHA256 using a dedicated audit key, producing tamper evidence equivalent to the financial ledger's hash chain. Full prompts (which may contain sensitive personal data) are stored in encrypted cold storage; only the SHA-256 hash and a retrieval key appear in operational logs, enabling GDPR erasure through key destruction without modifying the audit trail [^503^]. Financial decision logs---categorization, reconciliation, journal entry creation---are retained for 7 years to satisfy SOX and IRS requirements. Operational model-invocation logs are retained for a minimum of 6 months per EU AI Act Article 12 [^541^] [^543^].

### 7.3 Regulatory Compliance

The compliance framework is organized around four regulatory regimes, with each control designed to satisfy multiple regimes where overlap exists. The cross-cutting compliance matrix in Table 12 of the design specification maps each architectural control to its supporting regulations [^499^] [^500^] [^505^] [^508^].

#### 7.3.1 EU AI Act: High-Risk System Classification

The system is classified as a high-risk AI system under Annex III, Section 5(b) of the EU AI Act, covering "AI systems intended to be used to evaluate the creditworthiness of natural persons or establish their credit score." This classification extends to systems that assess financial health and make automated decisions affecting access to financial resources, including transaction categorization, anomaly detection, and automated reconciliation [^471^] [^475^]. The full set of high-risk obligations becomes enforceable on August 2, 2026 [^500^] [^468^]. Non-compliance carries penalties of up to EUR 30 million or 6% of global annual turnover for Tier 2 violations [^500^]---for a provider with EUR 100 million revenue, this represents a EUR 6 million exposure.

| Article | Requirement | Implementation |
|---------|-------------|---------------|
| Art. 9 -- Risk management | Continuous risk assessment lifecycle | Documented risk register with annual review; risk metrics dashboard |
| Art. 10 -- Data governance | High-quality, unbiased training data | Data quality management system; bias testing on categorization models; demographic parity checks |
| Art. 11 -- Technical documentation | Complete system documentation for conformity assessment | Architecture docs, model cards, training methodology, API specifications |
| Art. 12 -- Record-keeping | Automatic logging of all AI events; tamper-evidence; 6-month minimum retention | Structured JSON provenance logs; HMAC-SHA256 signing; 6-month operational / 7-year financial retention [^538^] [^541^] |
| Art. 13 -- Transparency | Users informed of AI use; capability and limitation disclosure | Disclosure banner on AI features; model capability documentation; known limitations published; training data date range displayed [^525^] |
| Art. 14 -- Human oversight | Meaningful human review with ability to intervene, override, and stop | Graduated autonomy (100% → sampled → exception-only); 6 approval gates; confidence-based routing at 0.85 threshold; "pause AI" emergency stop; override with reason capture [^548^] [^551^] [^564^] [^565^] |
| Art. 15 -- Accuracy | Sufficient accuracy for intended purpose; regular assessment | Deterministic validation catches 91.67% of LLM errors; accuracy metrics published; continuous monitoring via LangSmith |

The Article 14 human-oversight implementation addresses each sub-requirement of paragraph 4 explicitly: reviewers see model cards displaying capacities and limitations (14(4)(a)); confidence scores and override statistics are always visible to combat automation bias (14(4)(b)); feature importance and similar historical cases support correct interpretation (14(4)(c)); one-click override with reason capture enables reversal of any AI decision (14(4)(d)); and a "pause AI" button provides immediate intervention capability (14(4)(e)) [^565^].

#### 7.3.2 GDPR: Pseudonymization with Managed Keys

The central tension between GDPR and financial accounting is Article 17's "right to erasure" versus the immutable ledger requirement. Direct deletion of ledger entries is architecturally impossible (the hash chain would break) and legally impermissible (SOX Section 802 makes destruction of financial records a federal offense). The resolution is a pseudonymization layer with managed encryption keys [^563^].

| Data Subject Right | Technical Implementation | SLA |
|--------------------|-------------------------|-----|
| Access (Art. 15) | Export all data linked to subject; structured JSON + human-readable PDF | 30 days |
| Rectification (Art. 16) | New corrected entry added; old entry cryptographically flagged as superseded; both retained for audit | 30 days |
| Erasure (Art. 17) | PII encryption keys destroyed; pseudonymous financial records preserved; transaction integrity maintained | 30 days |
| Portability (Art. 20) | Machine-readable export (JSON, CSV) of all subject data | 30 days |
| Restriction (Art. 18) | Processing flag set; data excluded from AI training; access restricted | Immediate |
| Objection (Art. 21) | Processing stopped for specified purposes; override logged | Immediate |

Under the pseudonymization model, personally identifiable information (PII)---names, email addresses, bank account numbers, tax IDs---is encrypted with tenant-specific keys at the point of ingestion. The encrypted values replace raw PII in all operational tables and logs. Financial transaction data (amounts, dates, account codes) remains in plaintext to preserve ledger integrity and auditability. When a verified erasure request is received, the tenant-specific encryption keys for that individual's PII are securely destroyed per NIST SP 800-88 (cryptographic erasure) [^563^]. The pseudonymous identifiers remain, ensuring that the hash chain and double-entry bookkeeping are never compromised, but the PII is irretrievable. This approach has been endorsed by the European Data Protection Board in guidance on blockchain and GDPR compliance [^563^].

Lawful basis for processing is established separately for each purpose: core accounting/bookkeeping relies on contract (Art. 6(1)(b)); AI-assisted categorization on legitimate interest with a documented balancing test and opt-out availability (Art. 6(1)(f)); fraud detection on legal obligation (Art. 6(1)(c)); marketing on granular, separately withdrawable consent (Art. 6(1)(a)); and model improvement on legitimate interest with anonymization where possible [^563^].

#### 7.3.3 SOC 2 Alignment: All Five Trust Services Criteria

SOC 2 Type II assurance covers five Trust Services Criteria (TSC), each mapped to specific architectural controls [^505^] [^508^].

| TSC | Description | Key Controls | Evidence Collected |
|-----|-------------|--------------|-------------------|
| Security (CC6) | Protection against unauthorized access | RBAC with MFA, TLS 1.3, WAF, API gateway, intrusion detection, penetration testing | Quarterly access reviews, MFA enrollment reports, pen-test results, vulnerability scan reports |
| Availability (A1) | Systems available for operation | 99.9% SLA, multi-region DR, auto-scaling, health monitoring | Uptime reports, DR drill records, incident response logs |
| Processing Integrity (PI1) | Complete, valid, accurate, timely processing | Hash-chained ledger, double-entry enforcement, idempotency, deterministic validation, reconciliation | Reconciliation reports, transaction integrity checks, change tickets |
| Confidentiality (C1) | Confidential information protected | AES-256 encryption, DLP scanning, access controls, key management with HSM | Encryption configurations, DLP rules, quarterly access reviews, key rotation logs |
| Privacy (P1) | Personal information handled per commitments | GDPR compliance, pseudonymization, consent management, DSAR workflow, 30-day SLA | Privacy policy, DSAR handling records, retention schedules, anonymization job logs |

The SOC 2 Type II audit process requires a minimum 3-month observation period during which controls operate continuously while evidence is collected. Following the observation period, a CPA firm examines the evidence and tests control effectiveness over 4-6 weeks before issuing the report [^506^]. Continuous monitoring automates much of this evidence collection: certificate expiry monitoring triggers alerts 30 days before expiration; vulnerability management scans run weekly with critical CVEs flagged within 24 hours; SIEM correlation raises alerts when unauthorized access attempts exceed 5 in 10 minutes; and all changes are ticketed with peer review required, with emergency changes (>2 per month) flagged for management review [^514^] [^528^].

#### 7.3.4 HMRC MTD Compliance Roadmap

HMRC's Making Tax Digital (MTD) for VAT requires that businesses keep digital records and submit VAT returns through compatible software using API-based submission. The compliance roadmap is staged across four phases.

Phase 1 (MVP) establishes the foundational digital record-keeping infrastructure: all transactions are recorded digitally with no manual re-keying between systems, and the VAT return is computed and previewed as a 9-box summary (Boxes 1-9) before any submission. This satisfies MTD's "digital records" requirement because the system captures transactions at source---via bank feed import, document extraction, or conversational entry---and maintains the full audit trail linking each return line item to its underlying transactions.

Phase 2 adds HMRC API submission: the computed 9-box return is submitted directly to HMRC's VAT API using OAuth 2.0 authentication, eliminating manual filing. Error handling covers HMRC API failures (rate limiting, validation errors, authentication expiry) with automatic retry and human escalation for unresolvable errors. The digital link requirement---MTD's prohibition on manual copy-paste between systems---is satisfied intrinsically because the document extraction pipeline, Numscript generation, ledger posting, and tax computation form one continuous pipeline with automatic linking at each stage.

Phase 3 extends to multi-scheme support: the tax engine's three-layer architecture (Rule Store, Execution Engine, Override Workflow) is parameterized for different VAT schemes including Standard VAT, Flat Rate Scheme, and Cash Accounting. Each scheme's rules are stored as configuration, not code, enabling scheme switches without deployment.

Phase 4 addresses group VAT (consolidated returns for corporate groups) and partial exemption (for businesses with mixed taxable and exempt supplies). These require allocation methodology support and apportionment calculations that build on the multi-entity architecture defined in Section 3. The bi-temporal posting model (transaction date and VAT point date stored separately) handles the cash accounting scheme's tax-point timing correctly.

The estimated annual compliance program cost---spanning SOC 2 Type II, penetration testing, encryption infrastructure, audit logging, EU AI Act compliance, and GDPR legal review---ranges from $155,000 to $330,000 [^511^]. This is substantially lower than the exposure from non-compliance: up to 6-7% of global annual turnover under the EU AI Act alone, plus comparable penalties under GDPR. For a provider with EUR 100 million revenue, the compliance investment represents approximately 0.15-0.33% of revenue versus a 6% non-compliance exposure---a risk-adjusted return that justifies the investment as a cost of market access rather than a discretionary expenditure.

A critical architectural principle underlying all four compliance domains is that compliance is a byproduct of normal operation, not an add-on layer. The hash-chained ledger that ensures financial integrity simultaneously produces the tamper-evident audit trail required by SOX and the EU AI Act. The pseudonymization layer that resolves the GDPR erasure conflict simultaneously enables multi-tenant isolation. The deterministic validation that catches LLM errors before posting simultaneously satisfies SOC 2 Processing Integrity and EU AI Act Article 15 accuracy requirements. The Numscript output format that makes AI decisions auditable simultaneously provides the transparency required by EU AI Act Article 13. This convergence reduces the marginal cost of each additional compliance certification and creates a defensible regulatory moat: competitors retrofitting compliance onto legacy architectures must build separate systems for each regime, while this architecture achieves multi-regime compliance through shared primitives.
