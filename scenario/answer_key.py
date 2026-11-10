"""Only this deterministic key decides points. Models do not score teams."""
DECISIONS={'escalate':60,'investigate':25,'close':0}
KEY_IDS={'EML9001','EDR9001','EDR9002','NET9001','IDP9001','FIL9001','FIL9002','FIL9003'}
DECOY_IDS={'IDP9002','FIL9004','FIL9005','EML9002'}
EVIDENCE={
    'invoice': {'title':'Lookalike supplier and opened attachment','log_ids':['EML9001','EDR9001'],'key':True},
    'token': {'title':'Browser token access and a call to the lookalike site','log_ids':['EDR9002','NET9001'],'key':True},
    'session': {'title':'The same session signs in without a new MFA prompt','log_ids':['IDP9001','NET9001'],'key':True},
    'files': {'title':'The same session enumerates and downloads finance files','log_ids':['FIL9001','FIL9002'],'key':True},
    'twist': {'title':'Backup account uses the same external network outside its window','log_ids':['FIL9003','FIL9005'],'key':True},
    'travel': {'title':'Executive signs in abroad using a managed device and MFA','log_ids':['IDP9002'],'key':False},
    'export': {'title':'Analytics exports a large approved dataset','log_ids':['FIL9004'],'key':False},
    'normal_backup': {'title':'Backup account runs from its normal internal host at 03:10','log_ids':['FIL9005'],'key':False},
    'normal_invoice': {'title':'Another supplier invoice passes email checks','log_ids':['EML9002'],'key':False},
}
