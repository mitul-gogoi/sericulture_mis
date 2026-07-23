# Sericulture MIS — Business Use Cases

This document is derived directly from the current codebase (there is no external business-requirements spec in this repo) — it describes what each role can actually do today, not an aspirational design. It complements [../CLAUDE.md](../CLAUDE.md) (technical/dev orientation: stack, run instructions, sidebar structure) and [PRD.md](PRD.md) (chronological build history and backlog). If this file and the code ever disagree, trust the code and update this file.

Each use case follows the same template:

```
### UC-<id>: <Short name>
**As a** <Role>, **I can** <action>, **so that** <outcome>.

**Steps:**
1. ...

**Business rules:**
- ...
```

Steps describe the exact screen flow (sidebar item, field names, button labels) as currently coded. "Business rules" captures validations, scoping, and side effects that aren't obvious from the screen alone. Roles: **SA** = State Admin, **DA** = District Admin, **FP** = FIG President.

---

## State Admin (SA)

### UC-SA-1: Manage master data
**As a** State Admin, **I can** maintain the state's master lookup lists, **so that** downstream forms (farmer/FIG registration, etc.) have consistent, controlled options to choose from.

**Steps:**
1. Expand **Masters** in the sidebar and pick one of: Sectors, Stages, Districts, Sericulture Blocks, Caste, Religion.
2. Each of the 6 pages shares the same layout (a single reusable component): a search box, a table of existing rows with an Active/Inactive badge, and an inline "Add" panel (not a modal).
3. Fill the type-specific fields and save:
   - **Sectors**: Sector name.
   - **Stages**: Stage name, Sector (select), Yield stage type (free text, e.g. "rearing"), Output unit (free text, e.g. "kg cocoon").
   - **Districts**: District name, State name (defaults to "Assam").
   - **Sericulture Blocks**: Block name, District (select).
   - **Caste**: Caste name.
   - **Religion**: Religion name.
4. To modify an existing row, click **Edit** on its row, change fields, save.
5. To retire a row without deleting it, click **Deactivate** (or **Activate** to bring it back).

**Business rules:**
- Master pages are hard-gated to State Admin only in the UI — District Admin or FIG President visiting these URLs directly sees "Only State Admins can access master data."
- There is no hard delete anywhere in Masters — only the soft Activate/Deactivate toggle.
- Blocks are unique per district; Stages must reference a valid Sector.
- Deactivating a master row doesn't retroactively affect farmers/FIGs already using it — it only removes it from future selection lists.

### UC-SA-2: Register a farmer (state-wide)
**As a** State Admin, **I can** register a farmer in any district, **so that** the farmer enters the state's records and becomes eligible for FIG membership, land registration, and scheme benefits.

**Steps:**
1. Expand **Farmers & FIGs** → **Farmer Management**.
2. Click **Register farmer**.
3. Fill the form: First name, Last name, Gender (Male/Female/Other), Mobile, Aadhaar (optional), Farmer type (Small/Marginal/Medium/Large), **District** (select — SA only), Block (select, populated once a district is chosen), Village, Production stages (check all stages the farmer works in), Primary stage (appears once ≥1 stage is checked; auto-defaults to the first one checked), Photo (optional upload), Bank passbook (optional upload) + Account no. + IFSC.
4. Click **Save**.

**Business rules:**
- Farmer code is auto-generated as `SERI-FRM-NNNNNN` — starts at `100001`, and the sequence skips any number ending in `0`.
- Mobile number and Aadhaar (if given) must be unique across all farmers.
- The chosen Primary stage must be one of the checked Production stages.

### UC-SA-3: Edit or activate/deactivate a farmer
**As a** State Admin, **I can** correct a farmer's details or take them out of active service, **so that** records stay accurate without losing history.

**Steps:**
1. On **Farmer Management**, find the farmer's row and click **Edit** to open the same field set as registration (minus District, which can't be changed via edit) pre-filled, then **Save**.
2. Or click **Deactivate** (or **Activate**) on the row to toggle status without opening the edit form.

**Business rules:**
- Changing mobile/Aadhaar re-checks uniqueness against other farmers.
- A farmer's district cannot be changed through the edit form.

### UC-SA-4: Register a Farmer Interest Group (FIG)
**As a** State Admin, **I can** form a new FIG with its members and (optionally) a president in one flow, **so that** the group is immediately operational — able to log meetings and submit yield.

**Steps:**
1. Expand **Farmers & FIGs** → **FIG Management**, click **Register FIG**.
2. Fill: Name, Primary stage (select), Formation date, **District** (select — SA only), Block (select, cascades off district), Meeting venue (optional).
3. In **Add members**, check any number of farmers from the list shown — this list only contains farmers in the chosen district who aren't already in another active FIG.
4. If at least one member is checked, a **Set president (optional)** section appears: pick one of the checked members from the dropdown, then fill Login mobile (auto-filled from the farmer's own mobile, editable) and Password.
5. Click **Create**.

**Business rules:**
- FIG code is auto-generated as `SERI-FIG-NNNNN` — starts at `10001`, skipping any number ending in `0`.
- Under the hood this is 2–3 separate API calls in sequence: create the FIG, then add each checked member, then (if a president was chosen) set the president. If a later step fails, the FIG has already been created — the error toast says so explicitly and directs you to finish setup from the FIG's detail view.
- Setting a president here does double duty: it promotes that farmer to "President" within the FIG's member list **and** provisions a `FIG_PRESIDENT` login account for them (visible afterward under User Management → FIG Presidents) using the mobile/password entered.
- If the chosen mobile number already belongs to a different, non-FIG-President account, the president step fails (that mobile is taken).
- A farmer can only be an active member of one FIG at a time.

### UC-SA-5: Edit, activate/deactivate a FIG, or manage its members/president
**As a** State Admin, **I can** adjust an existing FIG's details, membership, and leadership, **so that** the group reflects real-world changes over time.

**Steps:**
1. On **FIG Management**, click a FIG's card to open its detail view.
2. Click **Edit** to change Name, Primary stage, Formation date, or Meeting venue inline, then **Save**. Click **Activate**/**Deactivate** to toggle the FIG's status.
3. Under **Add member**, pick a farmer (only unassigned farmers in this FIG's district are listed) and click **Add**.
4. Under **Set / Update President**, pick a member, fill Login mobile + Password, click **Save** — this works both to assign a first president and to replace an existing one.
5. If a president is already set, a **Reset president password** box appears — enter a new password and click **Reset** (no need to re-select the farmer or re-enter the mobile number).

**Business rules:**
- Deactivated FIGs stay visible in FIG Management (with an "Inactive" badge) rather than disappearing, so they can be reactivated later.
- Setting a new president automatically demotes the previous one to "Member."
- "Reset president password" only appears/works if the FIG currently has an active president; it changes only the password, not the assignment.

### UC-SA-6: Monitor monthly submission status (state-wide)
**As a** State Admin, **I can** see which FIGs have and haven't submitted their monthly meeting, **so that** I can follow up with districts that are falling behind.

**Steps:**
1. Expand **Meetings & Yield** → **Monthly Submission Status**.
2. Use the Month picker (defaults to the current month) to check any month.
3. Read the summary line ("N of M FIGs submitted for &lt;month&gt;") and the table below, which lists every FIG with its District, a Submitted/Pending badge, and the date it was submitted.

**Business rules:**
- This is a read-only status board — State Admin cannot edit, unlock, or submit on behalf of a FIG here.

### UC-SA-7: View yield reports
**As a** State Admin, **I can** review recorded yield data across the state, **so that** I can spot production trends without waiting for an aggregated report.

**Steps:**
1. Expand **Meetings & Yield** → **Yield Reports**.
2. Optionally filter by Month.
3. Read the table: Month, Farmer, Stage, Type (Primary/Non-primary badge), Planned, Actual, Stock, Earning, Loss reason.

**Business rules:**
- Pure read view — no create/edit UI on this page for any role.

### UC-SA-8: Verify farmer land GPS submissions
**As a** State Admin, **I can** approve or reject the GPS boundary a FIG President submits for a farmer's land, **so that** only accurate, non-overlapping parcels are recorded as verified.

**Steps:**
1. Go to **Land & GIS → GPS Verification & Reports**.
2. Rows with a "Pending" status and an available GPS submission show **Verify** and **Fail** actions.
3. Click **Fail** to reject — you'll be prompted for a reason.
4. Click **Verify** to approve. If the system flagged an overlap with another parcel, you'll get a confirmation prompt ("Overlap detected — verify anyway?") before it's allowed through.

**Business rules:**
- Overlap detection runs automatically at submission time using PostGIS spatial intersection against every other parcel that has a boundary — it is not something the verifier calculates manually.
- A flagged overlap cannot be verified without the explicit override confirmation.

### UC-SA-9: Approve or reject a district's training request
**As a** State Admin, **I can** decide whether a District Admin's proposed training goes ahead, **so that** training budget/venue commitments are centrally controlled.

**Steps:**
1. Go to **Training → Training Requests**.
2. For any row with status "Pending", use the Approve or Reject action.
3. Approving prompts for From date, To date, and Venue (three separate prompts).
4. Rejecting prompts for a rejection reason (defaults to "—" if left blank).

**Business rules:**
- Status becomes "Approved" or "Rejected". Only "Approved" trainings can later be marked complete by the requesting District Admin.
- There's no check that the request is still "Pending" before you act — a request could technically be re-approved or re-rejected.

### UC-SA-10: Manage and target schemes
**As a** State Admin, **I can** create a government scheme and define exactly who it's for, **so that** District Admins only ever see the candidates who genuinely qualify, not every farmer or FIG in their district.

**Steps:**
1. Go to **Schemes → Scheme Management**, click **New scheme**.
2. Fill: Scheme Name (required), Description, Total Budget (₹), Disbursement type (DBT / Material / Both), Support Type (Cash / Kind / Training).
3. Set **Beneficiary Kind** — Farmers or FIGs. This decides which candidate pool District Admins will see.
4. Set **Targeting Criteria**: districts (all, or a chosen subset), silk types (empty = all), and — for a Farmer-kind scheme — genders and farmer types (each empty = all). Optionally pick an **Asset Granted**, so that registering a beneficiary auto-creates the matching asset record for them (see UC-SA-16).
5. Save. **Edit** updates any field including targeting; **Deactivate** retires it; once deactivated, **Archive** hides it from the default list (toggle "Show archived" to see it again); **Publish** notifies every targeted District Admin and FIG President.

**Business rules:**
- Only State Admin can create/edit/deactivate/archive/publish schemes; District Admin sees only schemes that target their district (read-only, plus the candidate-selection flow in UC-DA-10); FIG President only receives the publish notification.
- A scheme must be deactivated before it can be archived — the same guard used elsewhere for hard-deleting master data.
- Search by scheme name is available at the top of the Scheme Management page.

### UC-SA-11: Allocate scheme budget to a district
**As a** State Admin, **I can** assign a portion of a scheme's budget to a specific district, **so that** the district can register beneficiaries against a defined ceiling.

**Steps:**
1. Go to **Schemes → Allocations**, click **New allocation**.
2. Select a Scheme (active schemes only), select a District, enter Amount (₹).
3. Save.

**Business rules:**
- Each scheme+district combination can only be allocated once — attempting a second allocation for the same pair returns a friendly conflict message.
- "Utilised" and "Remaining" on this allocation update automatically as beneficiaries are registered against it (see UC-SA-12/UC-DA-10).

### UC-SA-12: Register a scheme beneficiary directly
**As a** State Admin, **I can** register a beneficiary myself (not just via the District Admin flow), **so that** I can act on behalf of a district when needed.

**Steps:**
1. Go to **Schemes → Beneficiaries**. If the scheme is Farmer-kind, pick it and select from the candidate pool exactly as a District Admin would (UC-DA-10); the same cooldown badges and override-reason requirement apply.
2. Alternatively, `POST /schemes/beneficiaries` accepts a direct farmer_id or fig_id, benefit amount, material, and disbursement date.

**Business rules:**
- Registering a beneficiary automatically deducts the amount from the matching scheme+district allocation's "Remaining" figure (and adds to "Utilised") — blocked with a 400 if it would exceed the remaining balance.
- A beneficiary's type (farmer or FIG) must match the scheme's `beneficiary_kind` — mismatches are rejected.
- If the scheme has an **Asset Granted** set, the useful-life cooldown check runs first (see UC-SA-16); an ineligible result blocks registration unless an override reason is supplied.

### UC-SA-13: Manage user accounts
**As a** State Admin, **I can** create and administer login accounts for all three roles, **so that** the right people have the right level of access.

**Steps:**
1. Expand **User Management** → one of: State Admins, District Admins, FIG Presidents.
2. **State Admins**: click add, fill Name/Mobile/Password, save. Your own row is badged "You" and its Deactivate button is disabled.
3. **District Admins**: click add, fill Name/Mobile/Password/District, save. Edit works the same way but Password becomes optional ("leave blank to keep").
4. **FIG Presidents**: this page has **no create button** — accounts here only exist because a president was assigned via UC-SA-4/UC-SA-5. You can Edit (name/mobile/password) or Activate/Deactivate from here.
5. Use each page's Activate/Deactivate toggle to disable/re-enable any account.

**Business rules:**
- A district can have only one active District Admin at a time — creating or reactivating one while another is active for the same district is blocked.
- You cannot deactivate your own account.
- The last remaining active State Admin cannot be deactivated (the system always keeps at least one).

### UC-SA-14: Broadcast a notification
**As a** State Admin, **I can** send a notification to district admins and/or FIG presidents, **so that** important information reaches the field quickly.

**Steps:**
1. Go to **Notifications**, open the compose modal.
2. Fill Title (required), Details (required), optionally attach a file.
3. Choose Recipients: All District Admins, All FIG Presidents, All DAs + FIG Presidents, Selected District Admins, or Selected FIG Presidents.
4. If a "Selected …" option is chosen, a checkbox picker of individual users (with their district shown) appears — pick at least one.
5. Send.

**Business rules:**
- Sent notifications appear on the **Sent** tab, each with a **Retract** action (with a confirmation prompt) that removes it from every recipient's inbox.

### UC-SA-15: View dashboard & reports
**As a** State Admin, **I can** see a state-wide summary on login and drill into yield figures, **so that** I get a quick health check without navigating multiple pages.

**Steps:**
1. Land on **Dashboard** after login (or click it in the sidebar) — see [../CLAUDE.md](../CLAUDE.md) "Roles, menus, and dashboards" for the exact widget layout (stat cards, sector distribution chart, district heatmap, yield trend).
2. For a filterable breakdown, go to **Reports**, optionally set a Month, and read the stat cards, stage-wise chart, and detail table.

### UC-SA-16: Manage the asset catalogue and record/verify assets
**As a** State Admin, **I can** maintain the catalogue of trackable durable assets and record or verify holdings, **so that** scheme disbursements can be checked against a useful-life cooldown before being granted again.

**Steps:**
1. Go to **Master Data → Asset Types** to add/edit an asset type: name, category (Structure / Shared Infrastructure / Equipment), applicable silk types (leave blank for all), ownership level (Individual / FIG / Individual-or-FIG), useful life in years, and whether it's typically scheme-funded.
2. Go to **Asset Management → Assets** to record an existing asset for a farmer or FIG directly: owner type, owner, asset type, quantity, acquisition date, acquisition mode, confidence level, and an evidence photo.
3. Use **Verify** on any asset row to log a physical check (Confirmed Present / Partially Functional / Not Found) with an optional photo — this updates the asset's status and keeps an append-only log (**Log** button) of every check.

**Business rules:**
- Only State Admin and District Admin can add or verify assets (mirrors land GPS verification — District Admins are scoped to their own district's farmers/FIGs); FIG President sees a read-only view of their own FIG and its members' assets.
- An asset type's ownership level is enforced on every asset record: an Individual-only asset type cannot be assigned to a FIG, and a FIG-only asset type cannot be assigned to an individual farmer.
- Deactivating an asset type before deleting it (same guard as other master data); FK conflicts (assets already recorded against it) block the delete with a friendly message.
- An asset's useful-life cooldown is checked against **every** acquisition mode equally (self-declared, self-procured, or scheme-disbursed) — see UC-SA-12 and UC-DA-10 for where this surfaces during scheme registration.

---

## District Admin (DA)

### UC-DA-1: Register a farmer (own district)
**As a** District Admin, **I can** register a farmer within my own district, **so that** the farmer is captured in state records under my jurisdiction.

**Steps:**
1. Expand **Farmers & FIGs** → **Farmer Management**, click **Register farmer**.
2. Fill the same form as UC-SA-2 — **the District field is not shown to you**; your own district is applied automatically.
3. Save.

**Business rules:**
- Same code-numbering and uniqueness rules as UC-SA-2.
- Attempting to register (via API) a farmer outside your own district is rejected.

### UC-DA-2: Edit or activate/deactivate a farmer (own district)
**As a** District Admin, **I can** correct or retire a farmer record in my district, **so that** my district's data stays accurate.

**Steps:** Same as UC-SA-3.

**Business rules:**
- Restricted to farmers whose district matches your own; attempting to touch another district's farmer is rejected.

### UC-DA-3: Register a FIG (own district)
**As a** District Admin, **I can** form a new FIG within my district, complete with members and an optional president, **so that** field operations in my district can begin.

**Steps:** Same as UC-SA-4 — the District field is hidden and your own district is applied automatically; Block, member list, and president farmer choices are all scoped to your district.

**Business rules:** Same as UC-SA-4.

### UC-DA-4: Edit a FIG, toggle its status, or manage its president (own district)
**As a** District Admin, **I can** maintain FIGs in my district, **so that** membership and leadership stay current.

**Steps:** Same as UC-SA-5, restricted to FIGs in your own district.

**Business rules:** Same as UC-SA-5, plus a district-scope check on every mutation.

### UC-DA-5: Monitor monthly submission status (own district)
**As a** District Admin, **I can** see which of my district's FIGs have submitted this month's meeting, **so that** I can chase up the ones that haven't.

**Steps:**
1. Expand **Meetings & Yield** → **Monthly Submission Status**.
2. Same month-picker + status grid as UC-SA-6, but scoped to your district only (no District column, since it's implicitly yours).

### UC-DA-6: View yield (read-only)
**As a** District Admin, **I can** view yield entries recorded within my district, **so that** I can track production without needing to enter or edit data myself.

**Steps:** Same as UC-SA-7 — sidebar label reads "Yield View (read-only)."

### UC-DA-7: Manage farmer land and verify GPS
**As a** District Admin, **I can** register a farmer's land parcel and approve/reject its submitted GPS boundary, **so that** land records for my district are accurate and free of unresolved overlaps.

**Steps:**
1. Go to **Land → Land Management** (same page as SA's "GPS Verification & Reports", different sidebar label).
2. Click **Add land**: select Farmer, enter Dag No, Patta No, Land type (Owned/Leased/Community/Government), save.
3. Verify/Fail pending GPS submissions exactly as in UC-SA-8.

**Business rules:** Same as UC-SA-8, scoped to farmers in your district.

### UC-DA-8: Request a training
**As a** District Admin, **I can** propose a training for my district, **so that** State Admin can review and approve it.

**Steps:**
1. Go to **Training**, click **Request**.
2. Fill: Topic, Description, Proposed From date, Proposed To date, Venue, Estimated participants.
3. Submit — status starts as "Pending."

### UC-DA-9: Mark an approved training complete
**As a** District Admin, **I can** record the outcome of a training that State Admin approved, **so that** there's a closed-loop record of what actually happened.

**Steps:**
1. On **Training**, find a row with status "Approved" and click **Complete**.
2. Fill: Actual From date, Actual To date, Actual venue, Actual participants, Completion report (all required).
3. Submit — status becomes "Completed."

### UC-DA-9b: Record or verify an existing asset in my district
**As a** District Admin, **I can** add an asset a farmer or FIG already owns, or confirm one during a field visit, **so that** the state's asset records reflect reality even for assets acquired before this system existed.

**Steps:**
1. Go to **Asset Management → Assets**, click **Add Asset**.
2. Pick owner type (Farmer or FIG), then the specific owner (scoped to your district), then the asset type — only asset types compatible with that owner type are offered.
3. Fill quantity, acquisition date, acquisition mode (Legacy Self-Declared or Self-Procured), confidence level, an optional evidence photo, and remarks. Save.
4. To confirm an existing asset is still there, click **Verify** on its row, pick a result (Confirmed Present / Partially Functional / Not Found), optionally attach a photo, and submit.

**Business rules:**
- You can only add or verify assets for farmers/FIGs in your own district.
- An asset can also be self-declared by the farmer at registration time (see UC-DA-1) — this page is for adding one afterward, or for FIG-owned shared assets which farmer registration doesn't cover.
- Scheme-disbursed assets (created automatically via UC-DA-10) cannot be deleted from here — they mirror a disbursement record.

**Business rules:**
- Only trainings currently in "Approved" status can be completed; a "Rejected" training can never reach "Completed."
- The system does not currently verify that the completing District Admin is the same one who requested it, or that it's their district's training.

### UC-DA-10: Select scheme beneficiaries from the matched candidate pool
**As a** District Admin, **I can** pick who in my district actually receives a scheme from the pool of farmers or FIGs that already match its targeting criteria, **so that** I never have to manually re-check eligibility against gender, silk type, or farmer type myself.

**Steps:**
1. Go to **Schemes → Beneficiaries**, select a scheme that targets your district from the dropdown (only such schemes appear).
2. The matched candidate pool loads automatically — each row shows the farmer or FIG (matching the scheme's Beneficiary Kind), whether they're already registered, and a cooldown badge if the scheme grants an asset type (Eligible, or "Until <date>" if blocked).
3. Check the candidates you want to register, enter a Benefit Amount for each, and — only if a checked row shows a cooldown block — enter an Override Reason.
4. Click **Register selected** to submit them all in one call; a toast reports how many succeeded and how many rows failed (with reasons logged to the console).
5. Go to **Schemes → District Allocations** to view (not create) your district's allocated/utilised/remaining figures per scheme.

**Business rules:**
- The candidate pool and this whole flow only appears for schemes that target your district — schemes targeting other districts (or a subset that excludes yours) never show up in the picker.
- A candidate already registered as a beneficiary is shown but cannot be selected again.
- If the scheme grants an asset type, an ineligible cooldown blocks that row's registration unless you supply an override reason — this is logged on the beneficiary record, not silently bypassed.
- Successful registration auto-creates the granted asset (if any) for the correct owner — the farmer directly, their active FIG, or the FIG beneficiary itself, depending on the asset type's ownership level.
- District Admin cannot create allocations, only view and consume them (same as before).

### UC-DA-11: Send a district-scoped notification
**As a** District Admin, **I can** notify the FIG Presidents in my district, **so that** they get timely information relevant to their operations.

**Steps:** Same as UC-SA-14, but your Recipients options are limited to "All FIG Presidents in my district" or "Selected FIG Presidents" (both scoped to your district).

### UC-DA-12: View dashboard & reports
**As a** District Admin, **I can** see a district-scoped summary including an action queue, **so that** I know what needs my attention today.

**Steps:**
1. Land on **Dashboard** — see [../CLAUDE.md](../CLAUDE.md) for the exact widget layout (stat cards, monthly submission counter, Action queue linking to pending GPS verifications and pending training requests).
2. Go to **Reports** for a filterable yield breakdown, scoped to your district.

---

## FIG President (FP)

### UC-FP-1: Submit the monthly meeting (flagship workflow)
**As a** FIG President, **I can** log this month's meeting, attendance, and yield in one guided flow, **so that** my FIG's monthly obligation is fulfilled and the data feeds district/state reporting.

**Steps:**
1. Click **Submit this month** (persistent header button) or expand **Monthly Submission → Submit This Month**.
2. **Step 1 – Meeting**: fill Meeting title, Date, Time, Venue (pre-filled from the FIG's saved meeting venue, editable), Details, Next meeting date. Click **Next**.
3. **Step 2 – Attendance**: a table lists every FIG member with a Present checkbox, all checked by default — uncheck anyone who was absent. Click **Next**.
4. **Step 3 – Yield & stock**: a table shows only the members marked present in Step 2, with entry fields per member: Actual, Next plan, Stock, Sold qty, Sold rate, Loss reason (a hint suggests filling this in "If actual&lt;planned/2"). Click **Next**.
5. **Step 4 – Review**: read-only summary of the meeting, attendance count, and number of yield entries, plus a warning that submission is final. Click **Submit final**.
6. On success, the screen shows a locked "Submission recorded" confirmation — this month's data cannot be edited afterward through the app.

**Business rules:**
- Only one meeting can exist per FIG per calendar month — submitting again for a month already submitted is rejected.
- Only present members can have a yield entry recorded; entries typed for an absent member are ignored.
- If a member's Actual yield is less than half their Planned yield, a Loss reason is mandatory for that member, or the entire submission is rejected (nothing is partially saved).
- Once submitted, there is no edit/delete path anywhere in the app for that meeting or its yield rows — it is permanent.

### UC-FP-2: View submission history
**As a** FIG President, **I can** see a log of my FIG's past monthly submissions, **so that** I can confirm what's already been recorded.

**Steps:**
1. Expand **Monthly Submission → Submission History**.
2. Read the table: Month, Meeting title, Date, Venue — every past submission, no filter needed.

### UC-FP-3: Submit non-primary stage yield
**As a** FIG President, **I can** record yield for a member's secondary production stage(s), **so that** production outside the FIG's main stage is still captured.

**Steps:**
1. Go to **Non-Primary Yield → Non-Primary Stage Yield**.
2. Pick a Month.
3. The page auto-lists a row for every member/stage combination where the member works a stage other than the FIG's primary stage, with entry fields: Actual, Next plan, Stock, Sold qty, Sold rate.
4. Fill in at least one row (empty rows are ignored) and submit.

**Business rules:**
- If a farmer/stage/month combination already has a yield entry, submitting again for it is silently skipped (not overwritten) rather than erroring.
- If no member has a secondary stage, the page shows "No members have non-primary stages" and there's nothing to submit.

### UC-FP-4: View FIG members
**As a** FIG President, **I can** see who's currently in my FIG, **so that** I know my membership roster.

**Steps:**
1. Go to **Members → FIG Members**.
2. Read the member table (Name, Mobile, Role — President highlighted).

**Business rules:**
- FIG Presidents cannot add, remove, or edit members or the president assignment themselves — that's restricted to District/State Admin.

### UC-FP-5: Add a land parcel and submit GPS coordinates
**As a** FIG President, **I can** register a member's land and submit its boundary coordinates, **so that** the parcel can be verified and tracked for overlaps.

**Steps:**
1. Go to **Land & GPS → Land & GPS**, click **Add land**: select Farmer, Dag No, Patta No, Land type, save.
2. On a parcel not yet verified, click **GPS** to open the submission dialog.
3. Enter boundary points either by typing Latitude and Longitude into the two number fields and clicking **Add point** (repeat for each point — each addition appears in a table below with a remove option), or by clicking directly on the map (a marker/polygon preview updates as points are added).
4. Once at least 3 points are marked, click **Submit GPS**.
5. On success, a toast shows the computed area (in bigha) and whether an overlap with another parcel was detected.

**Business rules:**
- At least 3 points are required to submit.
- Area is computed server-side (shoelace formula) and converted to bigha (1 bigha = 2400 sqm) and hectare.
- Overlap detection runs automatically via a PostGIS spatial check against every other parcel with a boundary — you'll see the result in the success message, but approval/rejection is done by District/State Admin (UC-DA-7 / UC-SA-8).

### UC-FP-5b: View my FIG's assets (read-only)
**As a** FIG President, **I can** see the durable assets recorded for my FIG and its members, **so that** I have visibility without being able to alter the record.

**Steps:**
1. Go to **Asset Management → Assets (read-only)**.
2. Read the table — owner, asset type, quantity, acquisition mode, status, and verification status for my FIG itself and every active member.

**Business rules:**
- No Add/Edit/Verify/Delete actions are available — recording and verifying assets is District/State Admin only (UC-SA-16 / UC-DA-9b).

### UC-FP-6: View notifications
**As a** FIG President, **I can** read notifications sent to me by my District or State Admin, **so that** I stay informed.

**Steps:**
1. Go to **Notifications → My Notifications**.
2. Unread items are visually marked (accent border + "New" badge); click **Mark read** to clear it.

**Business rules:**
- FIG Presidents cannot send notifications or see a "Sent" tab — that's SA/DA only.
- A published scheme that targets my district also appears here as a notification (see UC-SA-10), even though FIG Presidents cannot author or view the scheme catalogue itself.

---

## Cross-cutting

### UC-XC-1: Log in
**As a** user of any role, **I can** log in with my mobile number and password, **so that** I can access the features my role permits.

**Steps:**
1. On the login screen, enter Mobile number and Password, click **Sign in**.
2. On success, land on **Dashboard**; on failure, an inline error message appears.

**Business rules:**
- After 5 consecutive failed attempts, the account is locked for 15 minutes; a successful login resets the failed-attempt counter.
- Inactive (deactivated) accounts cannot log in.
- Login is rate-limited (default 10/minute) independent of the per-account lockout.

### UC-XC-2: Stay signed in across a session (token refresh)
**As a** logged-in user, **I don't have to** re-enter my password every time my session token expires, **so that** my work isn't interrupted.

**Steps:** Fully automatic — no user action. When an API call fails due to an expired access token, the app transparently exchanges the stored refresh token for a new access+refresh pair and retries the call. If the refresh token itself is invalid/expired, the user is redirected to the login page.

**Business rules:**
- Access tokens last 60 minutes, refresh tokens 7 days (both configurable).
- There is currently no server-side revocation list — a refresh token remains usable until it naturally expires, even after logout (see PRD.md known issues).

### UC-XC-3: Manage sent notifications
**As a** State or District Admin, **I can** retract a notification I sent, **so that** I can undo a mistaken broadcast.

**Steps:**
1. On **Notifications → Sent**, find the notification and click **Retract**.
2. Confirm the prompt ("This will remove the notification from all recipients' inboxes. Continue?").

**Business rules:**
- Only the original sender, or any State Admin, can retract a notification.

---

## Not yet supported

These are acknowledged gaps, not defects — see `PRD.md`'s backlog for the full list and any code-level issues found in review:
- PDF export for any report.
- Annual report / stock-position report modules.
- Pagination or advanced filtering on list/table views (all lists currently load everything up to a fixed cap).
- Server-side refresh-token revocation (logout doesn't invalidate a refresh token early).
- Automatic farmer inactivation when they leave their last active FIG.
- Auto-aggregation snapshot tables for district/state monthly rollups (reports compute live on every request).
