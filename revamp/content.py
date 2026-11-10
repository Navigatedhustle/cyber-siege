"""Fictional game content. Monetary values are game values, never statistics."""
ROBOTS = {
    'SCOUT': ('The watcher', 'Spots trouble before people do.', '#40e6ed', '◎'),
    'SHERLOCK': ('The investigator', 'Explains what happened in plain English.', '#b9a0ff', '⌕'),
    'SHIELD': ('The protector', 'Locks the doors and isolates the problem.', '#67e8a5', '⬡'),
    'PATCH': ('The fixer', 'Gets the business back online.', '#ffd279', '+'),
    'SCRIBE': ('The storyteller', 'Writes the customer update and the value story.', '#ff9ece', '≡'),
}
INDUSTRIES = {
    'healthcare': ['Patient records', 'Surgery schedule', 'Pharmacy', 'Billing', 'Care team hub', 'Recovery center'],
    'manufacturing': ['Production line', 'Supplier portal', 'Design files', 'Payroll', 'Quality lab', 'Recovery center'],
    'retail': ['Online store', 'Payments', 'Warehouse', 'Loyalty data', 'Service desk', 'Recovery center'],
    'financial_services': ['Payments hub', 'Customer accounts', 'Trading desk', 'Call center', 'Risk office', 'Recovery center'],
    'public_sector': ['Resident records', '911 dispatch', 'Permits portal', 'Payroll', 'Service center', 'Recovery center'],
    'higher_education': ['Student records', 'Research lab', 'Financial aid', 'Campus email', 'Library', 'Recovery center'],
}
INDUSTRY_ICONS = {
    'healthcare': ['+', '◷', '+', '$', '♡', '✓'],
    'manufacturing': ['⚙', '⇄', '▤', '$', '◎', '✓'],
    'retail': ['▣', '$', '▦', '♡', '?', '✓'],
    'financial_services': ['⇄', '$', '↗', '☎', '◎', '✓'],
    'public_sector': ['▤', '☎', '▣', '$', '◎', '✓'],
    'higher_education': ['▤', '⚗', '$', '✉', '▥', '✓'],
}
VILLAINS = {
    'invoice': ('PHANTOM INVOICE', 'A fake urgent invoice is trying to steal a payment.', '▤'),
    'phisher': ('PHISHER', 'Fake emails are trying to steal your team’s logins.', '✉'),
    'lockjaw': ('LOCKJAW', 'Frozen systems are stopping the business.', '❄'),
    'leaky': ('LEAKY', 'A record thief is sneaking out the back door.', '▧'),
}
WAVES = {
    1: {'name': 'The payment trap', 'villain': 'invoice', 'duration': 180, 'goal': 'Check the invoice. Then call the vendor.',
        'translate': ['A rushed payment could cost Northwind $48,000 and hours of recovery. Game value.',
                      'Local AI highlighted warning signs. A human verified the payment details.',
                      '“Your team can check suspicious requests faster while keeping its analysis local.”']},
    2: {'name': 'The inbox storm', 'villain': 'phisher', 'duration': 180, 'goal': 'Send SCOUT to each building. Quarantine fake emails.',
        'translate': ['Stolen logins put customer records and business uptime at risk.',
                      'SCOUT checked 200 fictional emails and highlighted 12 fakes for the team.',
                      '“Local AI can help your people sort more evidence in less time.”']},
    3: {'name': 'Freeze protocol', 'villain': 'lockjaw', 'duration': 240, 'goal': 'Spot → explain → isolate → restore → communicate.',
        'translate': ['Frozen systems put $12,000 per minute at risk. Game value.',
                      'Five local AI roles helped the team spot, explain, isolate, restore and communicate.',
                      '“A Fury can run local AI agents that help your team respond faster.”']},
}
INVOICE = {'id': 'INV-104', 'company': 'Northwind (fictional)', 'amount_game_usd': 48000,
           'sender': 'billing@parts.example.test', 'reply_to': 'urgent@pay-change.example.test',
           'text': 'Pay within 15 minutes. Our bank details changed today. Do not call the usual contact.'}
EMAILS = [{'id': f'MAIL-{i:03}', 'building': i % 6,
           'sender': 'login@verify-now.example.test' if i < 12 else 'colleague@northwind.example.test',
           'subject': 'Urgent: enter your password to keep access' if i < 12 else 'Scheduled team update',
           'link': 'https://password-check.example.test' if i < 12 else None} for i in range(200)]
FILES = [{'id': f'FILE-{i}', 'building': i % 6, 'event': 'unexpected encryption', 'restore': 'verified offline backup'} for i in range(24)]
LOGINS = [{'id': f'LOGIN-{i}', 'event': 'unusual login after fake email', 'approved': False} for i in range(12)]
FALLBACKS = {
    'SCOUT': 'I found warning signs in the fictional evidence. Let’s check the affected buildings.',
    'SHERLOCK': 'Changed payment details. A mismatched reply address. Pressure to hurry. Verify with a trusted contact.',
    'SHIELD': 'Isolate affected systems so the problem cannot spread. Your security team makes the decision.',
    'PATCH': 'Restore from a verified backup, then check that the business can work again.',
    'SCRIBE': 'Your team contained the incident with local AI assistance. Explain what changed, what is restored and what comes next.',
}

def evidence_for(wave):
    return [INVOICE] if wave == 1 else EMAILS if wave == 2 else FILES + LOGINS
