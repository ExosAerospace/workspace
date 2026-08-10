# Expense Report Submission Procedure (ADM-EXP-02)

**Purpose:** how Exos employees submit, approve, and pay expense reports — entirely from Mission Control.

**Scope:** all employees submitting reimbursable business expenses (travel, materials, per diem, etc.).

## The process (all in Mission Control → 💵 Expenses)

1. **Download the template.** On the Expenses page, click **Download expense report template (.xlsx)** (also in the Process Library, Administrative area).
2. **Fill it out.** Enter each expense line: date, category, description, amount. Attach or keep receipts per Finance policy. Total the report.
3. **Upload it.** On the Expenses page, choose your completed file, enter the **total amount**, **expense period**, and a short **purpose**, then click **Submit for approval**.
4. **Manager approval (automatic).** On submit, Mission Control automatically creates an **approval task for your manager** (resolved from the BambooHR org chart) with your report attached. Your manager approves by marking that task **Done**.
5. **Finance payment (automatic).** Once your manager approves, Mission Control automatically creates **payment tasks for the Finance role holders** (CFO / Finance and BD / Accounts Payable — currently Kyle Ballard and Lizi Quinn). They process payment and mark their task Done.
6. **Paid.** When payment is complete the report shows **Paid** on your Expenses page. You can track status (Submitted → Approved → Paid) there at any time.

## Routing (role-based)

- **Approver:** your direct manager, from the live org (BambooHR). If your manager changes in Bamboo, routing follows automatically.
- **Payers:** whoever holds the CFO/Finance and AP roles, configured in `expense-roles.json`. Update that file when a role holder changes — routing is by role, not by name.

## Notes

- Everyone is notified automatically when a task is assigned to them (approval and payment).
- Keep the report and receipts business-appropriate; Finance may return an item for correction.
- Owner of this procedure: Finance (Kyle Ballard) with Exo/MC maintaining the workflow.
