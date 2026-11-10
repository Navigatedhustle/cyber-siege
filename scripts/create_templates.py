"""Author the ten reviewable starting templates. Never infer facts about accounts."""
from pathlib import Path
import yaml

ROWS=[
('financial_services','Financial services','Explore local review of internal policy and risk documents.','Risk operations lead or infrastructure architect','Which internal reviews repeat every week?','Which documents must stay within your infrastructure?','Who would compare quality and response time in a small evaluation?'),
('healthcare','Healthcare and life sciences','Explore local search across approved clinical operations documents.','Clinical operations lead or research IT architect','Where do staff lose time finding approved information?','Which data would require extra access controls?','Who would select a safe document set for an evaluation?'),
('state_local','State and local government','Explore local search of internal service procedures.','Agency IT director or service operations lead','Which service questions take the most staff time?','Which records need to stay within agency systems?','Who would help choose a useful evaluation workflow?'),
('federal','Federal','Explore local analysis of approved internal technical documents.','Mission technology lead or infrastructure architect','Which document review task repeats across your team?','What environment and approvals would an evaluation need?','Who would define a useful result for a limited test?'),
('education','Higher education and research','Explore local assistance with approved research documents.','Research computing lead or campus IT architect','Which research tasks need repeated model access?','Which datasets have access or location restrictions?','Who would measure whether a shared local system helps?'),
('manufacturing','Manufacturing','Explore local search across equipment manuals and service records.','Plant operations lead or manufacturing IT architect','Which equipment questions delay maintenance work?','Which manuals or records could support a small test?','Who would check the answers against real maintenance needs?'),
('retail','Retail and consumer goods','Explore local analysis of internal store operations reports.','Store operations lead or data platform architect','Which reports do teams review repeatedly?','Which data needs to remain in your infrastructure?','Who would choose a useful question for an evaluation?'),
('energy','Energy and utilities','Explore local search of approved maintenance procedures.','Asset operations lead or infrastructure architect','Which procedure searches slow down operations?','Which records would need a controlled evaluation environment?','Who would judge the accuracy of the answers?'),
('legal','Legal and professional services','Explore local review of approved internal knowledge documents.','Knowledge management lead or IT director','Which internal research questions repeat across teams?','Which documents have confidentiality restrictions?','Who would define a safe test and review its answers?'),
('technology','Technology and software','Explore local assistance with internal engineering documentation.','Engineering productivity lead or infrastructure architect','Which documentation tasks interrupt engineers most often?','Which source material must stay within your systems?','Who would compare a local evaluation with the current workflow?'),
]
if __name__=='__main__':
    root=Path(__file__).resolve().parents[1]/'content/industry_templates'
    for key,name,use,buyer,*questions in ROWS:
        data={'status':'draft','industry':name,'use_case':use,'buyer':buyer,'questions':questions,
              'opening_message':'Could we discuss one repeated task involving sensitive internal data? A ZGX Virtual Lab discussion could help us decide whether a local AI evaluation would be useful.'}
        (root/f'{key}.yaml').write_text(yaml.safe_dump(data,sort_keys=False,allow_unicode=True))
