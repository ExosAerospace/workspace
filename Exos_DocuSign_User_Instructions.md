# Exos Internal DocuSign — User Instructions

**Version:** Draft 1.0 · **Date:** 2026-07-27

## What this is
Exos runs a segregated, in-house e-signature panel for sending documents for signature. It is isolated from the rest of Mission Control and reached at **/docusign**, behind its own access passcode. All executed-document emails are sent from **jquinn@exosaero.com**.

## Access
1. Go to **/docusign** on the Mission Control host.
2. Enter the DocuSign access passcode.
3. You reach the send panel — nothing else in Mission Control is exposed from this entry.

## Sending a document
1. Pick a **template** from the list (e.g., Employment Offer Letter, Mutual NDA, Consulting Agreement, Technology License, Subcontract, and the ITAR Technical Data Transfer Control Agreement).
2. Fill the placeholder fields ([EFFECTIVE DATE], [PARTY], etc.).
3. Add signer name(s) and email(s) and their role.
4. Send. When all parties sign, a fully-executed copy is emailed to the signers.

## Templates available
- **Employment Offer Letter**
- **Mutual Non-Disclosure Agreement (MNDA)**
- **Advisory Agreement**
- **Consulting Agreement**
- **Technology License**
- **Letter of Intent (LOI)**
- **Subcontract Agreement**
- **ITAR-Controlled Technical Data Transfer Control Agreement (TDTCA)** — for releasing export-controlled data to a support contractor (see use case below).

---

## USE CASE: Releasing ITAR-controlled drawings to a support contractor
Use this whenever Exos proposes to share export-controlled technical data (drawings, models, engineering data) with an outside party — for example, contracting **Blue Dwarf Space** to support **BLK3 fin Part 450 licensing**, which requires releasing fin drawings.

**Do not send the drawings first.** The TDTCA and the release process are the gate. Follow the sequence:

1. **Due Diligence + Dossier.** Before anything is sent, Exo completes export-control due diligence on the recipient and builds a dossier (entity, ownership/FOCI, principals and nationalities, denied-party screening, viability, risk verdict). A failed DD stops the transfer.

2. **Determine the authorization basis.**
   - Recipient is a **U.S. Person** → no license needed.
   - Recipient is a **Foreign Person** (e.g., Blue Dwarf is Australian) → you need a license, a Technical Assistance Agreement, a license exemption, or the **AUKUS / 22 C.F.R. 126.7** Australia/UK pathway. Confirm this before release.

3. **Prepare the TDTCA in DocuSign.** Select the *ITAR-Controlled Technical Data Transfer Control Agreement* template and complete:
   - Recipient legal name / entity type / address and the support scope.
   - Section 2: recipient U.S./Foreign-Person status and the authorization basis.
   - **Exhibit A — Drawing Manifest:** list every drawing to be released. Only listed items are authorized.
   - **Exhibit B — Due Diligence & Dossier Summary:** attach/summarize the DD result and dossier.

4. **Exo completeness review.** Exo confirms DD complete, dossier attached, authorization basis confirmed, manifest accurate, safeguarding boundary set, and all fields complete.

5. **Empowered Official signs Section 12 (the human gate).** The designated Empowered Official, **John Quinn (Cofounder & CEO)**, certifies DD is reviewed and the authorization basis is in place, and authorizes release. **This signature is the only thing that permits transfer.**

6. **Send for signature and release.** Send the TDTCA to the recipient to sign. Only after full execution and the Empowered Official authorization are the manifested drawings released, and the transfer is logged for the export record.

**Reminders**
- Nothing releases before the Empowered Official signs.
- Only Exhibit A items are authorized — anything else needs a new manifest and re-authorization.
- Internal U.S.-person exchange is not an export; foreign-person release always needs an authorization basis.
- This document is a draft for review; after Jon approves it, the TDTCA is reviewed by Exos ITAR support (Denise Shirey) before first operational use.
