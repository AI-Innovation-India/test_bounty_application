# Skill: Banking & Fintech Testing

## Domain
Online banking, payment platforms, fintech apps, wallet, lending, investment platforms

## Trigger Keywords
bank, account, balance, transfer, transaction, payment, wallet, fund, withdraw, deposit, loan, credit, debit, statement, beneficiary, upi, iban, swift, kyc, compliance

## Critical Test Areas

### Account & Balance
- Balance displays correctly (positive, zero, negative/overdraft)
- Balance updates immediately after transaction
- Multiple account types (savings, current, credit) display correctly
- Account number/IBAN masked correctly in display
- Statement download shows correct transactions

### Fund Transfers
- Internal transfer (between own accounts)
- External transfer (to saved beneficiary)
- New beneficiary transfer (with OTP/2FA confirmation)
- Transfer with insufficient funds shows correct error
- Transfer limits enforced (daily, per-transaction)
- Duplicate transfer detection (same amount+beneficiary within short window)
- Transfer scheduled for future date
- Recurring/standing order setup

### Compliance & Security (Non-Negotiable)
- All sensitive data masked by default (account numbers, card numbers)
- Session times out after inactivity (stricter than normal apps: 5-10 min)
- Re-authentication required for sensitive actions (transfers, PIN change)
- Transaction history not accessible after logout
- OTP/2FA mandatory for any money movement
- Large transfer triggers additional verification

### KYC / Identity Verification
- Document upload (ID, proof of address) works
- File type and size validation
- Pending verification state handled
- Rejection with reason and re-submission flow

### Cards
- Card details visible only after authentication
- Freeze/unfreeze card updates immediately
- Card transaction history accurate
- Spending limit set/modify

### Error Handling (Critical in Finance)
- Network timeout during transfer → transaction state clearly shown (not ambiguous)
- Duplicate transaction clearly identified and blocked
- Failed transaction → funds not deducted
- Partial failure clearly communicated

## Business Rules
- Regulatory limits vary by jurisdiction (localised limits)
- Beneficiary cooling-off period (new beneficiary may have transfer delay)
- AML flags: unusual patterns should trigger review
- Interest calculation accuracy (savings, loans)
- Currency conversion rates applied correctly

## Responsible AI Note
Never use real financial credentials in tests. Always use sandbox/test environments.
Test environments must be completely isolated from production.
