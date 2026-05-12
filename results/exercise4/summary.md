# Exercise 4: Trace vs. Messages Narration

Per-task comparison of narratives produced from the structured trace (Exercise 2 contract) vs. the agent's raw messages list.

## Token / latency table

| # | Task | Trace events | Msgs | Trace in/out tok | Msgs in/out tok | Trace lat (s) | Msgs lat (s) |
|---|---|---|---|---|---|---|---|
| 1 | What is the renewal date for Initech? | 4 | 4 | 814/129 | 1007/132 | 2.59 | 3.14 |
| 2 | Build me an account brief on Acme Corp. | 6 | 5 | 2015/351 | 2209/323 | 2.74 | 2.89 |
| 3 | Build me an account brief on Globex. | 6 | 5 | 1841/288 | 2046/281 | 2.79 | 2.94 |
| 4 | Build me an account brief on Wayne Enterprises. | 6 | 5 | 1795/244 | 2009/231 | 2.22 | 1.92 |
| 5 | Compare Acme Corp and Globex on renewal risk. | 10 | 7 | 3219/456 | 3543/476 | 3.28 | 3.58 |

**Totals** -- trace: 9684 in / 1468 out tokens. messages: 10814 in / 1443 out tokens. Δ input: +1130 (+11.7%).

## Side-by-side narratives

### 1. What is the renewal date for Initech?

**Final answer:**

> [{'type': 'text', 'text': '{"response":"Initech’s renewal date is **December 1, 2026**.","agent_summary":"Looked up Initech in the internal CRM and retrieved the account’s renewal date from the account record."}', 'annotations': [], 'id': 'msg_0d815306c95a7781006a02837d19f081a2b3074bfcf3f2c7e1', 'phase': 'final_answer'}]

#### From trace

- **Goal:** What is the renewal date for Initech?
- **Steps taken:**
  - Looked up the Initech account in the internal CRM and retrieved its account record.
  - Found the renewal date on the account record: 2026-12-01.
- **Decisions made:**
  - The agent chose to use the account lookup tool because the question required a specific account field that would be available in the CRM.
  - After retrieving the account record, the agent stopped because the renewal date was directly available and no further lookup was needed.
- **Summary:** Initech’s renewal date is December 1, 2026.

#### From messages

- **Goal:** What is the renewal date for Initech?
- **Steps taken:**
  - Looked up the Initech account in the internal CRM using the company name.
  - Retrieved the account record, which listed the renewal date as 2026-12-01.
- **Decisions made:**
  - The agent chose to use the account lookup tool because the answer required a specific customer record rather than general knowledge.
  - After finding the renewal date in the CRM, the agent stopped without further searching because the needed information was already available.
- **Summary:** The agent said, "Initech’s renewal date is December 1, 2026."

---

### 2. Build me an account brief on Acme Corp.

**Final answer:**

> [{'id': 'rs_04488658ca050620006a028387df94819396199694daa21ade', 'summary': [], 'type': 'reasoning'}, {'type': 'text', 'text': '{"response":"## Account Brief: Acme Corp\\n\\n### Relationship status\\n- **Account owner:** Priya Shah\\n- **Tier:** Strategic\\n- **ARR:** $1.25M\\n- **Products in use:** Automation Cloud, Document Understanding\\n- **Renewal date:** September 15, 2026\\n- **Open opportunities:** 2\\n- **Last QBR:** February 10, 2026\\n- **Current relationship notes:** Acme is expanding finance automation. The CFO is the executive sponsor, which is a strong signal for continued investment. Procurement is a known bottleneck and should be managed early for any expansion or renewal motion.\\n\\n### Recent external developments\\n*Note: Public search results surfaced information for “Acme United Corporation,” which may or may not be the same entity as Acme Corp. Confirm company identity before using externally sourced talking points.*\\n\\n- Acme United reported stronger recent earnings, including a **12% increase in EPS for Q4 2025**.\\n- 2025 commentary referenced **tariff-related program delays**, with some delayed activity expected to shift into later quarters.\\n- Public materials also referenced potential **strategic acquisitions** and a **GICS reclassification** announced in late 2025.\\n\\n### Talking points / risks for Priya Shah\\n1. **Finance automation expansion:** Since Acme is already expanding finance automation and the CFO is the sponsor, align the 2 open opportunities to measurable finance outcomes: cycle-time reduction, document-processing accuracy, auditability, and cost takeout.\\n2. **Procurement risk:** Start procurement engagement well ahead of the September 2026 renewal. If expansion is targeted, build a business case early and identify legal/security/procurement blockers now.\\n3. **External cost pressure / tariffs:** If the public Acme United information applies, tariff-driven delays and cost pressure could affect budget timing. Position automation as a margin-protection lever, but validate whether these macro pressures are relevant to this account.","agent_summary":"Looked up Acme Corp in the internal CRM to retrieve owner, ARR, products, renewal timing, open opportunities, QBR history, and account notes. In parallel, searched the public web for recent company developments. The web results appeared to reference Acme United Corporation, so I included those developments with a caveat that the identity should be confirmed before using them in customer-facing outreach."}', 'annotations': [], 'id': 'msg_04488658ca050620006a02838974108193b842fafc06dd543b', 'phase': 'final_answer'}]

#### From trace

- **Goal:** Build an account brief on Acme Corp.
- **Steps taken:**
  - Looked up Acme Corp in the internal account system and retrieved its owner, tier, ARR, products, renewal date, open opportunities, last QBR date, and relationship notes.
  - Searched the web for recent 2025 news about Acme Corp and collected several public results, though the results referenced Acme United Corporation rather than clearly matching Acme Corp.
  - Compiled an account brief that combined the internal CRM details with the public news findings and added a caution that the external information may not be for the same company.
- **Decisions made:**
  - Used both the internal account lookup and a public web search because the task asked for an account brief, which typically includes both relationship data and recent company context.
  - Flagged the public news as potentially mismatched because the search results appeared to be for Acme United Corporation, so they should not be treated as confirmed facts about Acme Corp without identity verification.
  - Stopped after assembling a brief from the available data because the trace shows no additional sources were consulted.
- **Summary:** The agent produced an account brief for Acme Corp: Priya Shah is the owner, the account is Strategic with $1.25M ARR, the products in use are Automation Cloud and Document Understanding, renewal is September 15, 2026, there are 2 open opportunities, and the last QBR was February 10, 2026. It noted that Acme is expanding finance automation, with the CFO as executive sponsor and procurement as a known bottleneck. For external context, it included recent news about Acme United Corporation but warned that this may not be the same entity and should be confirmed before use.

#### From messages

- **Goal:** Build an account brief on Acme Corp.
- **Steps taken:**
  - Looked up Acme Corp in the internal account system and retrieved ownership, tier, ARR, products in use, renewal date, open opportunities, last QBR, and account notes.
  - Searched the web for recent 2025 company news related to Acme Corp.
  - Combined the internal account details and the web results into an account brief, including a note that the public results appeared to be for Acme United Corporation rather than clearly for Acme Corp.
- **Decisions made:**
  - The agent used both the account lookup and web search because the request called for an account brief, which needed both relationship data and recent external context.
  - The agent flagged the web findings cautiously because the search results seemed to reference a potentially different company name, so it did not present them as confirmed facts about Acme Corp.
  - The agent stopped after assembling a usable brief with a caveat, rather than continuing to resolve the company-identity mismatch within the available run.
- **Summary:** The agent produced an account brief for Acme Corp: account owner Priya Shah, Strategic tier, $1.25M ARR, products Automation Cloud and Document Understanding, renewal on September 15, 2026, two open opportunities, last QBR on February 10, 2026, and notes that the account is expanding finance automation with the CFO as sponsor and procurement as a bottleneck. It also included recent public news, but warned that the search results appeared to be for Acme United Corporation and should be confirmed before use.

---

### 3. Build me an account brief on Globex.

**Final answer:**

> [{'id': 'rs_0a484004ada5ba93006a02839a22f0819f827d964cb55a6dd8', 'summary': [], 'type': 'reasoning'}, {'type': 'text', 'text': '{"response":"## Account brief: Globex\\n\\n**Relationship status**\\n- **Owner:** Marcus Lee\\n- **Tier / ARR:** Enterprise, **$480K ARR**\\n- **Current products:** Automation Cloud\\n- **Renewal:** July 1, 2026\\n- **Engagement health:** Mixed. Last QBR was **Nov. 22, 2025**. Expansion motion stalled after a CIO change, but the team is re-engaging through the new VP of Ops.\\n- **Pipeline:** 1 open opportunity\\n\\n**Recent external developments**\\n- Public search results for “Globex” are ambiguous and surface multiple similarly named companies, including Globex Business Centres and Globex Mining Enterprises.\\n- Potentially relevant developments include business expansion activity by Globex Business Centres in Oman and exploration/permitting updates from Globex Mining. These should be validated against the exact Globex entity in CRM before use in outreach.\\n\\n**Talking points / risks for Marcus**\\n1. **Rebuild executive alignment:** The CIO transition appears to have disrupted expansion. Use the VP of Ops relationship to confirm current operational priorities and identify the new buying committee.\\n2. **Anchor on Automation Cloud value:** Before pushing expansion, quantify outcomes from the existing deployment—automation coverage, efficiency gains, cost savings, or SLA improvements.\\n3. **Data-quality risk:** External company identity is unclear from public search. Marcus should confirm the customer’s full legal name, industry, and website before referencing recent news or tailoring industry-specific messaging.","agent_summary":"Looked up Globex in the internal CRM to retrieve ARR, owner, products, renewal date, QBR timing, pipeline, and account notes. In parallel, searched the public web for recent Globex-related developments, then flagged that results appear ambiguous across multiple companies and should be validated before outreach."}', 'annotations': [], 'id': 'msg_0a484004ada5ba93006a02839ac0f8819faf8ec7218d020571', 'phase': 'final_answer'}]

#### From trace

- **Goal:** Build an account brief on Globex.
- **Steps taken:**
  - Looked up Globex in the internal account record and retrieved the owner, tier, ARR, product usage, renewal date, open opportunities, last QBR date, and account notes.
  - Searched the public web for recent news about Globex and found multiple similarly named companies, including Globex Business Centres and Globex Mining Enterprises.
  - Prepared an account brief that combined the CRM facts with the external search results and included cautions about the ambiguity of the public-company identity.
- **Decisions made:**
  - Used both the internal account lookup and a web search because the task required an account brief, which needs both CRM context and recent external developments.
  - Stopped after the first search results because they were already ambiguous and the agent chose to flag the identity risk rather than continue without validating the exact entity.
- **Summary:** The agent produced an account brief for Globex: Marcus Lee owns the account; it is an Enterprise account at $480K ARR using Automation Cloud, with renewal on July 1, 2026, one open opportunity, and a last QBR on Nov. 22, 2025. It noted that expansion stalled after a CIO change but is being re-engaged through the new VP of Ops. For external news, it reported that search results were ambiguous across multiple Globex entities and should be validated before use in outreach.

#### From messages

- **Goal:** Build an account brief on Globex.
- **Steps taken:**
  - Looked up Globex in the internal account system and retrieved owner, tier, ARR, products, renewal date, open opportunities, last QBR date, and account notes.
  - Searched the web for recent news about Globex and collected several possible matches from different companies with similar names.
  - Compiled an account brief summarizing the relationship status, recent external developments, talking points, and risks.
- **Decisions made:**
  - Used both internal account data and public web search because the task called for an account brief, which needed both relationship context and recent developments.
  - Flagged the public search results as ambiguous because the name ‘Globex’ matched multiple companies, so the agent avoided treating any one news item as definitive.
- **Summary:** The agent produced an account brief for Globex: Marcus Lee owns the account, it is Enterprise with $480K ARR, the current product is Automation Cloud, renewal is July 1, 2026, there is one open opportunity, and the last QBR was on Nov. 22, 2025. It noted that expansion stalled after a CIO change but re-engagement is happening through the new VP of Ops. It also warned that web results for ‘Globex’ are ambiguous across multiple similarly named companies, so any external news should be validated before outreach.

---

### 4. Build me an account brief on Wayne Enterprises.

**Final answer:**

> [{'id': 'rs_09f77daec9c00534006a0283aa92e8819796a85f7286a8d397', 'summary': [], 'type': 'reasoning'}, {'type': 'text', 'text': '{"response":"## Account Brief: Wayne Enterprises\\n\\n### 1) Relationship status\\n- **CRM status:** No internal account record found for “Wayne Enterprises.”\\n- **Implication:** No ARR, owner, products, renewal date, or account notes are currently available. This appears to be either a net-new/prospect account or the company may be listed under a different name in CRM.\\n\\n### 2) Recent external developments\\n- Public search results show references to **Wayne Enterprises Inc.** as a company associated with **trade uniforms, PPE, custom workwear, and embroidery services**.\\n- Recent public items indicate **GME Supply acquired Wayne Enterprises** to expand capabilities in custom workwear and uniform programs.\\n- Some search results are noisy or likely unrelated, including fictional/social references to “Wayne Enterprises,” so confirm the exact entity before outreach.\\n\\n### 3) Talking points / risks for the account owner\\n1. **Clarify entity and ownership:** Confirm whether the target is the Wayne Enterprises recently acquired by GME Supply. If so, outreach may need to go through GME Supply leadership or procurement.\\n2. **Acquisition-driven opportunity:** If the acquisition is relevant, there may be post-merger needs around systems consolidation, vendor rationalization, customer support workflows, or operational scaling.\\n3. **Data quality risk:** No CRM match means there is no known relationship history. Recommend checking for alternate names, parent company records, or duplicate accounts before creating a new opportunity.","agent_summary":"I looked up Wayne Enterprises in the internal CRM and found no matching account record. I then searched the public web for recent developments and found results suggesting a Wayne Enterprises Inc. in custom workwear/PPE was recently acquired by GME Supply, while noting some search-result noise from unrelated or fictional references. I combined those findings into a concise account brief with relationship status, external developments, and suggested talking points/risks."}', 'annotations': [], 'id': 'msg_09f77daec9c00534006a0283ac04a08197a5a223b73223b9bb', 'phase': 'final_answer'}]

#### From trace

- **Goal:** Build an account brief on Wayne Enterprises.
- **Steps taken:**
  - Checked the internal CRM for an account record for Wayne Enterprises and found none.
  - Searched the web for recent news and developments related to Wayne Enterprises.
  - Reviewed the search results, which pointed to a Wayne Enterprises Inc. in trade uniforms, PPE, custom workwear, and embroidery, including a reported acquisition by GME Supply, while also showing some unrelated or noisy references.
  - Prepared an account brief summarizing relationship status, recent external developments, and talking points/risks.
- **Decisions made:**
  - Used both internal account lookup and web search because the task required an account brief and the company did not appear to be present in internal records.
  - Stopped after the first web pass because the results were sufficient to draft the brief and no further clarification was pursued in the trace.
- **Summary:** The agent reported that no internal account record exists for Wayne Enterprises. It then summarized public findings indicating that Wayne Enterprises Inc. is associated with trade uniforms, PPE, custom workwear, and embroidery services, and that GME Supply has reportedly acquired it. The final brief also flagged search-result noise and advised confirming the exact entity before outreach.

#### From messages

- **Goal:** Build an account brief on Wayne Enterprises.
- **Steps taken:**
  - Checked the internal CRM for Wayne Enterprises and found no matching account record.
  - Searched the web for recent news and developments related to Wayne Enterprises.
  - Reviewed the search results and noted references to Wayne Enterprises Inc. being acquired by GME Supply, along with some unrelated or noisy results.
  - Compiled the findings into an account brief covering relationship status, recent external developments, and talking points/risks.
- **Decisions made:**
  - Used the internal account lookup first to see whether there was an existing CRM relationship before relying on public information.
  - Supplemented the CRM check with a web search because there was no internal record and the brief needed current external context.
  - Flagged the search results as potentially noisy because some references appeared unrelated or fictional, so the entity should be confirmed before outreach.
- **Summary:** The agent produced a brief stating that no internal CRM account was found for Wayne Enterprises, that public results suggest a Wayne Enterprises Inc. in custom workwear/PPE was acquired by GME Supply, and that the account owner should confirm the exact entity and ownership before outreach.

---

### 5. Compare Acme Corp and Globex on renewal risk.

**Final answer:**

> [{'id': 'rs_0e1fb32264bdd332006a0283ba1560819da9eb5e141b161f23', 'summary': [], 'type': 'reasoning'}, {'type': 'text', 'text': '{"response":"## Renewal risk comparison: Acme Corp vs. Globex\\n\\n| Account | Renewal | ARR | Relationship status | Renewal risk | Why |\\n|---|---:|---:|---|---|---|\\n| **Globex** | **2026-07-01** | **$480K** | Enterprise account; expansion stalled after CIO change; re-engaging via new VP of Ops; last QBR was 2025-11-22 | **High** | Renewal is ~7 weeks away, stakeholder disruption from CIO change, expansion momentum stalled, and QBR cadence appears stale. |\\n| **Acme Corp** | 2026-09-15 | $1.25M | Strategic account; expanding finance automation; CFO is exec sponsor; last QBR 2026-02-10 | **Medium** | Stronger relationship signals and expansion activity, but large ARR and known procurement bottleneck create execution risk. |\\n\\n### Recent external developments\\n- **Acme Corp:** Public search results were not clearly tied to the exact CRM account. Results referenced similarly named companies, including Acme United and Acme Electronics. One relevant directional signal from Acme United results: revenue growth with profit pressure, tariff/debt concerns, and planned automation investment. Validate company match before using externally.\\n- **Globex:** Public results appear to reference Globex Mining, which may or may not be the CRM account. If applicable, recent coverage highlights a royalty/asset portfolio strategy, strong cash/no-debt messaging, and 2026–2028 production catalysts. Validate company match before citing in customer conversation.\\n\\n## Recommendation\\n**Prioritize Globex as the higher renewal-risk account.** Marcus Lee should urgently confirm the new economic buyer / decision process, schedule an executive-level renewal checkpoint, and rebuild value alignment around the VP of Ops.\\n\\n### Talking points / risks to flag\\n**Globex — Marcus Lee**\\n1. **Stakeholder risk:** CIO change likely disrupted sponsorship; confirm who owns renewal and budget now.\\n2. **Timing risk:** July 1 renewal leaves limited runway; push for a renewal plan and mutual close date immediately.\\n3. **Value risk:** Expansion stalled, so reinforce realized value from Automation Cloud before discussing upsell.\\n\\n**Acme Corp — Priya Shah**\\n1. **Procurement risk:** Known bottleneck should be addressed early despite later September renewal.\\n2. **Expansion opportunity:** Finance automation momentum and CFO sponsorship are positive; tie renewal to broader finance outcomes.\\n3. **Commercial risk:** Because ARR is $1.25M, even a small delay or contraction has material impact; start renewal/procurement path now.","agent_summary":"Looked up CRM records for Acme Corp and Globex, including ARR, renewal dates, account owners, products, QBR timing, and notes. Ran public web searches for recent developments on both companies, but results appeared potentially ambiguous due to similarly named companies, so I treated those as directional signals requiring validation. Compared renewal timing, stakeholder stability, expansion momentum, QBR recency, procurement issues, and ARR exposure to assess relative renewal risk."}', 'annotations': [], 'id': 'msg_0e1fb32264bdd332006a0283bbc174819da7a0a1c57a431c4c', 'phase': 'final_answer'}]

#### From trace

- **Goal:** Compare Acme Corp and Globex on renewal risk.
- **Steps taken:**
  - Looked up the CRM record for Acme Corp and found it is a Strategic account with $1.25M ARR, renewal on 2026-09-15, two open opportunities, a last QBR on 2026-02-10, and notes about expanding finance automation with a procurement bottleneck.
  - Looked up the CRM record for Globex and found it is an Enterprise account with $480K ARR, renewal on 2026-07-01, one open opportunity, a last QBR on 2025-11-22, and notes about stalled expansion after a CIO change while re-engaging through a new VP of Ops.
  - Searched the web for recent 2026 news about Acme Corp and found results that appeared to refer to similarly named companies rather than the exact account, so the information was treated as only directional.
  - Searched the web for recent 2026 news about Globex and found results that appeared to refer to Globex Mining rather than the exact CRM account, so the information was treated as only directional.
  - Compared the two accounts using renewal date, stakeholder stability, expansion momentum, QBR recency, procurement risk, and ARR exposure, then chose Globex as the higher-risk renewal.
- **Decisions made:**
  - The agent searched both CRM records first to ground the comparison in account-specific renewal data before using external news.
  - The agent performed web searches for both companies to look for recent developments that might change renewal risk, but it stopped short of using them as firm evidence because the search results seemed ambiguous and possibly matched different companies.
  - The agent prioritized Globex as higher risk because its renewal is sooner and its account notes show stakeholder disruption and stalled expansion, while Acme has later timing and stronger sponsorship despite procurement risk.
- **Summary:** The agent concluded that Globex is the higher renewal-risk account. It described Globex as high risk because the renewal is sooner, the CIO change disrupted the relationship, expansion is stalled, and the QBR cadence is stale. Acme Corp was rated medium risk because it has stronger sponsorship and expansion momentum, but its large ARR and procurement bottleneck still create execution risk.

#### From messages

- **Goal:** Compare Acme Corp and Globex on renewal risk.
- **Steps taken:**
  - Looked up Acme Corp in the account system and found it is a Strategic account with $1.25M ARR, renewal on 2026-09-15, two open opportunities, a last QBR on 2026-02-10, and a note about a known procurement bottleneck.
  - Looked up Globex in the account system and found it is an Enterprise account with $480K ARR, renewal on 2026-07-01, one open opportunity, a last QBR on 2025-11-22, and a note that expansion stalled after a CIO change.
  - Searched the web for recent 2026 news about Acme Corp and Globex to see whether external developments added context to renewal risk.
  - Reviewed the search results and noted they appeared to reference similarly named companies, so they were treated as directional only and not used as definitive evidence.
  - Produced a side-by-side renewal risk comparison, including renewal date, ARR, relationship status, risk level, reasons, and recommended actions.
- **Decisions made:**
  - Because the task was a renewal-risk comparison, the agent prioritized internal account data first to establish renewal timing, ARR exposure, and relationship health.
  - The agent ran web searches to look for recent developments that might affect renewal risk, but then decided not to rely heavily on them because the results were ambiguous and may not match the CRM accounts exactly.
  - The agent concluded Globex was the higher-risk account because its renewal is much sooner, the stakeholder base was disrupted by a CIO change, expansion had stalled, and the QBR cadence was older than Acme’s.
  - The agent treated Acme as medium risk rather than high risk because it had stronger sponsor support and active expansion, despite a procurement bottleneck and higher ARR exposure.
- **Summary:** The agent concluded that Globex is the higher renewal-risk account and should be prioritized. It characterized Globex as high risk due to an imminent renewal date, stakeholder disruption, stalled expansion, and stale QBR timing. Acme Corp was rated medium risk because it has a later renewal, stronger sponsorship, and active finance automation expansion, though procurement is a known bottleneck. The agent also cautioned that the public web results were ambiguous and should be validated before being cited externally.

---

## Observations

For this agent shape -- a short, linear ReAct loop on LangChain with first-class tool calls on every `AIMessage` -- the narratives produced from the structured trace and from the raw messages list are effectively indistinguishable. The middleware does not make the narrative more precise.

The interesting result is what that implies, not what it disproves:

- **The narrator is the load-bearing piece.** The value being demonstrated here is an online judge that explains agent behavior to business users who will never open a trace viewer. That value is independent of capture mechanism.
- **The capture contract still earns its keep for portability, not precision.** A normalized intermediate format is what lets the same narrator run against LangSmith traces (Exercise 6) and OTEL spans (Exercise 7) without rewriting the prompt. If the narrator were bound to LangChain's messages list, it would not generalize across frameworks.
- **Messages-mode cost scales worse than it looks here.** Input tokens were +11.7% across these 5 short runs. On longer-running agents -- larger tool payloads, more turns, retries, parallel tool calls, memory truncation -- the messages list accumulates noise (system prompts, intermediate ai content, full tool outputs) that the structured trace filters out by construction. Equivalent quality at 1.1x cost on toy tasks becomes a real gap on production-scale traces.

Net: capture for portability and cost control, not for narrative accuracy. The narrator is the product.
