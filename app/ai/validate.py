"""Never release model claims with invented or unavailable evidence identifiers."""

import re

def validate_quantities(text, ids):
    """Catch unit mistakes such as calling a GB sized download TB in grounded text."""
    from .retrieval import logs
    rows=[logs()[key] for key in ids if key in logs()]
    scales={'byte':1,'bytes':1,'kb':1000,'mb':1000**2,'gb':1000**3,'tb':1000**4,
            'kib':1024,'mib':1024**2,'gib':1024**3,'tib':1024**4}
    if 'FIL9003' in ids:
        # The recorded UTC time is 02:16; the stated normal window begins 03:00.
        lowered=text.casefold()
        wrong_window=re.search(r'\b(?:during|within|inside) (?:the |its |normal |scheduled )*backup window',lowered)
        unqualified_legitimate=re.search(r'\b(?:legitimate|expected|normal) backup (?:activity|service account|job)',lowered)
        contrast=any(word in lowered for word in ('outside','not within','not inside','not during','unexpected','abnormal','anomal','could','possible','uncertain'))
        if (wrong_window or unqualified_legitimate) and not contrast:
            raise ValueError('Backup timing claim contradicts FIL9003: 02:16 is outside 03:00 to 03:30 UTC. Preserve uncertainty without changing this fact.')
    for number,unit in re.findall(r'\b(\d+(?:\.\d+)?)\s*(bytes?|[KMGT]i?B)\b',text,re.I):
        actual=float(number)*scales[unit.casefold()]
        expected=[row['bytes'] for row in rows if row.get('bytes')]
        if not any(abs(actual-value)/value<.03 for value in expected):
            raise ValueError('Numeric size claim does not match cited bytes. Use large download instead of a size.')
    for number in re.findall(r'\b(\d[\d,]*)\s+(?:(?:sensitive|confidential)\s+)?files\b',text,re.I):
        if int(number.replace(',','')) not in [row.get('files') for row in rows]:
            raise ValueError('File count does not match cited logs')

def validate_ids(result, allowed):
    value=result.model_dump() if hasattr(result,'model_dump') else result
    def walk(node):
        if isinstance(node,dict):
            ids=node.get('log_ids',node.get('summary_log_ids',[]))
            if ids:
                for field in ('summary','explanation','uncertainty'):
                    if isinstance(node.get(field),str):validate_quantities(node[field],ids)
            for key,item in node.items():
                if key in ('log_ids','summary_log_ids'):
                    if not item or any(log_id not in allowed for log_id in item):
                        raise ValueError('Unavailable cited ID: '+','.join(str(x) for x in item if x not in allowed))
                else:
                    walk(item)
        elif isinstance(node,list):
            for item in node: walk(item)
        elif isinstance(node,str):
            for identifier in re.findall(r'\b(?:IDP|EML|EDR|FIL|NET)\d{4,}\b',node):
                if identifier not in allowed:
                    raise ValueError('Model text mentions an unavailable log ID')
    walk(value)
    for item in value.get('events',[]):
        if len(item['explanation'].split())>25:
            raise ValueError('Shorten this timeline sentence to at most 12 words: '+item['explanation'])
    if 'events' in value:
        from .retrieval import logs
        dataset=logs()
        value['events'].sort(key=lambda event:dataset[event['log_ids'][0]]['timestamp'])
    return value
