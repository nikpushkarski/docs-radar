---
{
  "source_id": "rupa-transition-schedule",
  "source_summary_sha256": "7babb0d77b31658e80b8ba28e990103acfafd88195a4c05e102edbb8077baec7",
  "audience": "Providers",
  "passages": [
    {
      "id": "provider-ordering",
      "heading": "New lab orders",
      "valid_from": "2026-11-01",
      "valid_until": "{{fact:rupa-login-closure-date}}"
    },
    {
      "id": "recommended-transfer",
      "heading": "Recommended transfer timing",
      "valid_from": "2026-11-01",
      "valid_until": "2026-12-04"
    },
    {
      "id": "transfer-before-closure",
      "heading": "Before login closes",
      "valid_from": "2026-11-01",
      "valid_until": "{{fact:rupa-login-closure-date}}"
    },
    {
      "id": "recommendation-date-passed",
      "heading": "After the recommended transfer date",
      "valid_from": "2026-12-04",
      "valid_until": "{{fact:rupa-login-closure-date}}"
    },
    {
      "id": "closure-warning",
      "heading": "On or after the closure date",
      "valid_from": "{{fact:rupa-login-closure-date}}",
      "valid_until": null
    }
  ]
}
---
# Before Rupa login access closes
Proposed demo revision—not Fullscript-approved.

## New lab orders

Since October 30, 2026, Rupa has been view-only for providers; place new lab orders through Fullscript.

## Recommended transfer timing

Fullscript recommends transferring your Rupa data before December 4, 2026, to avoid disrupting patients with outstanding orders.

## Before login closes

Transfer your Rupa data before login access closes on {{fact:rupa-login-closure-date}}.

## After the recommended transfer date

Fullscript's recommended transfer date of December 4, 2026 has passed.
The captured schedule still gives the later login-closure date; follow the supported transfer guidance before that closure.

## On or after the closure date

The captured transition schedule lists {{fact:rupa-login-closure-date}} as the Rupa login-closure date.
On or after that date, do not assume that Rupa login remains available.
Recovery procedures are not established by the captured evidence.

## Source

[Fullscript: Rupa closes January 20, 2027—key dates and next steps](https://support.fullscript.com/articles/rupa-closes-january-20-2027-key-dates-and-next-steps)
Source captured November 1, 2026.