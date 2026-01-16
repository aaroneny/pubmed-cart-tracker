import json
import os
import requests
from Bio import Entrez
import datetime
from deep_translator import GoogleTranslator

# --- 1. 基础配置 ---
Entrez.email = "dlu_fangenyue@163.com"

# --- 2. 关键词策略 ---
KEYWORDS = """
(
  ("In vivo CAR-T"[Title/Abstract] OR "In situ CAR-T"[Title/Abstract])
  OR
  ("mRNA-LNP"[Title/Abstract] AND ("T cell"[Title/Abstract] OR "CAR"[Title/Abstract] OR "Immunotherapy"[Title/Abstract]))
  OR
  ("Lentiviral vector"[Title/Abstract] AND ("CAR"[Title/Abstract] OR "Gene therapy"[Title/Abstract] OR "Transduction efficiency"[Title/Abstract]))
  OR
  ("In vivo gene delivery"[Title/Abstract] AND "T cell"[Title/Abstract])
)
"""

# --- 3. 动态加载 IF 数据库 ---
def load_impact_factors():
    """从 json 文件加载 IF 数据，方便维护"""
    json_file = "impact_factors.json"
    if os.path.exists(json_file):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ 读取 IF 数据库失败: {e}")
    else:
        print("⚠️ 未找到 impact_factors.json，将不显示 IF")
    return {}

# 全局变量：加载一次即可
JOURNAL_IFS = load_impact_factors()

def get_impact_factor(journal_name):
    if not JOURNAL_IFS: return "N/A"
    
    # 1. 精确匹配
    if journal_name in JOURNAL_IFS: return JOURNAL_IFS[journal_name]
    
    # 2. 忽略大小写匹配
    for key, value in JOURNAL_IFS.items():
        if key.lower() == journal_name.lower(): return value
    
    # 3. 模糊匹配 (包含关系，取最长匹配)
    sorted_keys = sorted(JOURNAL_IFS.keys(), key=len, reverse=True)
    for key in sorted_keys:
        if key in journal_name: return JOURNAL_IFS[key]
        
    return "N/A"

def translate_to_chinese(text):
    try:
        translator = GoogleTranslator(source='auto', target='zh-CN')
        return translator.translate(text)
    except Exception:
        return text

def extract_conclusion(abstract_text):
    if not abstract_text: return "暂无摘要"
    text = abstract_text.strip()
    upper_text = text.upper()
    for keyword in ["CONCLUSION:", "CONCLUSIONS:", "DISCUSSION:"]:
        if keyword in upper_text:
            index = upper_text.rfind(keyword)
            return text[index + len(keyword):].strip()
    sentences = [s.strip() for s in text.split('. ') if s.strip()]
    if len(sentences) >= 2: return ". ".join(sentences[-2:]) + "."
    elif len(sentences) == 1: return sentences[0] + "."
    return text

def extract_affiliation(article):
    try:
        authors = article['MedlineCitation']['Article'].get('AuthorList', [])
        if not authors: return "暂无单位信息"
        aff_info = authors[0].get('AffiliationInfo', [])
        if aff_info:
            full_aff = aff_info[0].get('Affiliation', '')
            return full_aff.split(';')[0].split('.')[0] 
    except Exception:
        pass
    return "暂无单位信息"

def extract_date(article):
    try:
        pub_date = article['MedlineCitation']['Article']['Journal']['JournalIssue']['PubDate']
        year = pub_date.get('Year', '')
        month = pub_date.get('Month', '')
        day = pub_date.get('Day', '')
        if year:
            date_str = f"{year}"
            if month: date_str += f"-{month}"
            if day: date_str += f"-{day}"
            return date_str
        elif 'MedlineDate' in pub_date:
            return pub_date['MedlineDate']
    except Exception:
        pass
    return "未知日期"

def check_relevance(title, abstract):
    text = (title + " " + abstract).lower()
    must_have = [
        "car-t", "chimeric antigen", "t cell", "t-cell", "immunotherapy",
        "tumor", "cancer", "oncology", "malignan", 
        "gene edit", "crispr", "transduction", "payload"
    ]
    black_list = ["sars-cov-2", "covid-19", "coronavirus"]
    has_blacklist = any(word in text for word in black_list)
    has_cancer_context = any(w in text for w in ["cancer", "tumor", "oncology", "car"])
    
    if has_blacklist and not has_cancer_context: return False
    if any(word in text for word in must_have): return True
    return False

def fetch_papers():
    today = datetime.date.today()
    print(f"[{today}] 启动周报搜索 (过去 30 天)...")
    
    try:
        handle = Entrez.esearch(db="pubmed", term=KEYWORDS, reldate=30, datetype="pdat", retmax=30)
        record = Entrez.read(handle)
        id_list = record["IdList"]
    except Exception as e:
        print(f"搜索出错: {e}")
        return []
    
    papers = []
    if id_list:
        try:
            handle = Entrez.efetch(db="pubmed", id=id_list, retmode="xml")
            records = Entrez.read(handle)
            
            for article in records['PubmedArticle']:
                try:
                    title = article['MedlineCitation']['Article']['ArticleTitle']
                    journal = article['MedlineCitation']['Article']['Journal']['Title']
                    abstract_list = article['MedlineCitation']['Article'].get('Abstract', {}).get('AbstractText', [])
                    full_abstract = " ".join([str(x) for x in abstract_list]) if isinstance(abstract_list, list) else str(abstract_list)
                    
                    if not check_relevance(title, full_abstract): continue
                        
                    if_score = get_impact_factor(journal)
                    aff = extract_affiliation(article)
                    pub_date = extract_date(article)
                    
                    conclusion_en = extract_conclusion(full_abstract)
                    highlight_cn = translate_to_chinese(conclusion_en)
                    pmid = article['MedlineCitation']['PMID']
                    
                    print(f"✅ 处理: {title[:20]}... | IF: {if_score}")

                    papers.append({
                        "title": title,
                        "journal": journal,
                        "if": if_score,
                        "highlight": highlight_cn, 
                        "aff": aff,
                        "date": pub_date,
                        "link": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                    })
                except Exception as e:
                    continue
        except Exception:
            pass

    papers.sort(key=lambda x: float(x['if']) if x['if'] != 'N/A' else 0, reverse=True)
    return papers

def update_readme(papers):
    current_date = datetime.datetime.now().strftime('%Y-%m-%d')
    content = f"# 🧬 In vivo CAR-T 周报\n\n"
    content += f"**聚焦方向**: In vivo CAR-T | mRNA-LNP (Oncology) | Lentiviral Engineering\n\n"
    content += f"📅 **更新日期**: {current_date}\n\n"
    content += "---\n\n"
    
    if not papers:
        content += "📭 **本周未发现高相关度文献。**\n"
    
    for paper in papers:
        if_display = f"🔥 IF: **{paper['if']}**" if paper['if'] != "N/A" else "IF: -"
        
        content += f"### [{paper['title']}]({paper['link']})\n"
        content += f"- **期刊**: *{paper['journal']}* | {if_display}\n"
        content += f"- **发表日期**: {paper['date']}\n"
        content += f"- **主要单位**: {paper['aff']}\n"
        content += f"- **核心结论**: \n> {paper['highlight']}\n\n"
        content += "---\n"
        
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(content)

if __name__ == "__main__":
    papers = fetch_papers()
    update_readme(papers)
