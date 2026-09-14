# EC Channel Memory

Per-channel durable memory for the **EC Discord server** (Exobot Control, guild `1501635980094996631`).
Each channel has its own `memory.md` so topic context persists independently of the shared
workspace `MEMORY.md`. When Exo responds in an EC channel, it should read (and update) that
channel's `memory.md` here, keyed by the channel id below.

## Rules
- Keep it lean: standing context + open threads. No large artifacts (per AGENTS.md context hygiene).
- Update the `_Last updated_` line when you touch a file.
- Backups: whole workspace is git-tracked + covered by the launchd interval backup. Point-in-time
  snapshots of this tree live in `_backups/`.

## Channel id → name map
| Channel ID | Name |
|---|---|
| 1501635980975804590 | general |
| 1501636814849577050 | exomac-system |
| 1501636728711282741 | series-a |
| 1501636614034821320 | rd-team |
| 1502869101507514418 | social-content |
| 1501636501778464939 | dubai-fraud |
| 1501636671492460554 | blk3-payload |
| 1501636766258696333 | home-automation |
| 1504983528306380860 | license |
| 1511744611343925258 | rdre |
| 1513191553462698115 | vfw-post2150 |
| 1520160892661272666 | international-trade-zone |
| 1524171611283001434 | power |
| 1529234995787599932 | lizi-channel |
| 1543193323630628914 | lizi-channel-2 |
| 1529489733078614076 | project-lazarus (voice cat) |
| 1530535449750409320 | project-lazarus |
| 1532810358153285862 | starfighters |
| 1533954015757598991 | navy |
| 1539382179120021616 | utd-exo3capstone |
