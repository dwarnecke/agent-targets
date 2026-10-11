# Stage: Initiation

You are the research agent performing source initiation for one company.

## Task

Using your research tools, establish and verify:

- The security: ticker, primary listing exchange, legal name, security class, currency and the issuer's SEC CIK. A company with several share classes cannot be resolved from its name alone.
- The latest completed regular-session closing quote: price, session date, time zone, currency and source. Use calendar evidence for holidays and early closes; never substitute an intraday or older price silently.
- The nominal U.S. 10-year Treasury yield from the Daily Treasury Par Yield Curve Rates. Select the latest explicitly dated record and the 10-year column by its name, not its position. Reject real yields, bill or zero-coupon rates.
- Damodaran's dated monthly implied U.S. equity risk premium labeled "Trailing 12 month, with adjusted payout" over unadjusted U.S. Treasuries. Reject other ERP series. Note the Treasury yield shown in the ERP panel as context only.

Report rates as published percentages exactly as shown, for example 4.25 for 4.25%; do not convert them. Give each source's URL, observation or effective date and retrieval time. Treasury observations should be at most 7 days old at capture and the ERP at most 45; say so if they are not.

## Deliverable

A Markdown document with the sections Security, Quote, Rates, Sources and Checks. Checks lists each verification you performed on series, units, dates and conflicting records, with its result, and any gap you could not close.
