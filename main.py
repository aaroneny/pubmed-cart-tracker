import requests
from Bio import Entrez
import datetime
from deep_translator import GoogleTranslator

# --- 1. 基础配置 ---
Entrez.email = "dlu_fangenyue@163.com"

# --- 2. 关键词策略 (保持不变) ---
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

# --- 3. 2025 最新期刊影响因子字典 (保持不变) ---
JOURNAL_IFS = {
    "Nature": "48.5", "Science": "44.7", "Cell": "42.5",
    "Nature Communications": "14.7", "Science Advances": "11.7",
    "PNAS": "9.6", "Proceedings of the National Academy of Sciences": "9.6",
    "New England Journal of Medicine": "78.5", "The Lancet": "88.5", "JAMA": "63.1", "BMJ": "93.6",
    "Nature Medicine": "58.7", "Cancer Cell": "48.8", "Lancet Oncology": "35.9",
    "Journal of Clinical Oncology": "42.1", "Annals of Oncology": "65.4",
    "World Psychiatry": "65.8", "Circulation": "35.5", "European Heart Journal": "37.6",
    "Gastroenterology": "25.7", "Gut": "23.0", "Journal of Hepatology": "26.8",
    "Nature Reviews Drug Discovery": "101.8", "Nature Reviews Microbiology": "103.3",
    "Nature Reviews Molecular Cell Biology": "90.2", "Nature Reviews Clinical Oncology": "82.2",
    "Nature Reviews Cancer": "66.8", "Nature Reviews Immunology": "60.9",
    "Nature Reviews Materials": "86.2", "Nature Reviews Disease Primers": "60.6",
    "Nature Reviews Genetics": "52.0", "Nature Biotechnology": "33.1",
    "Nature Cell Biology": "17.3", "Cell Research": "25.9", "Molecular Cancer": "29.9",
    "Signal Transduction and Targeted Therapy": "40.8", "Cell Metabolism": "27.7",
    "Cell Stem Cell": "19.8", "Immunity": "32.4", "Nature Immunology": "27.7",
    "Science Immunology": "24.8", "Nature Biomedical Engineering": "26.8",
    "Advanced Materials": "26.8", "Advanced Functional Materials": "18.5",
    "ACS Nano": "15.8", "Nano Letters": "9.6", "Biomaterials": "12.8",
    "Small": "13.0", "Bioactive Materials": "18.0", "Journal of Controlled Release": "10.5",
    "Chemical Reviews": "55.8", "Molecular Therapy": "10.1", "Nucleic Acids Research": "16.6",
    "Journal of Extracellular Vesicles": "15.5", "Molecular Therapy - Nucleic Acids": "7.0"
}

def get_impact_factor(journal_name):
    if journal_name in JOURNAL_IFS: return JOURNAL_IFS[journal_name]
    for key, value in JOURNAL_IFS.items():
        if key.lower() == journal_name.lower(): return value
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

# --- 新增函数：提取第一作者单位 ---
def extract_affiliation(article):
    try:
        # 路径: Article -> AuthorList -> Author -> AffiliationInfo -> Affiliation
        authors = article['MedlineCitation']['Article'].get('AuthorList', [])
        if not authors: return "暂无单位信息"
        
        # 获取第一作者的单位
        aff_info = authors[0].get('AffiliationInfo', [])
        if aff_info:
            full_aff = aff_info[0].get('Affiliation', '')
            # 简单清理，只保留前面部分，避免地址太长
            return full_aff.split(';')[0].split('.')[0] 
    except Exception:
        pass
    return "暂无单位信息"

# --- 新增函数：格式化发表日期 ---
def extract_date(article):
    try:
        pub_date = article['MedlineCitation']['Article']['Journal']['JournalIssue']['PubDate']
        year = pub_date.get('Year', '')
        month = pub_date.get('Month', '')
        day = pub_date.get('Day', '')
        
        # 有些只有 Year 和 Month，没有 Day
        if year:
            date_str = f"{year}"
            if month: date_str += f"-{month}"
            if day: date_str += f"-{day}"
            return date_str
        elif 'MedlineDate' in pub_date:
            return pub_date['MedlineDate'] # 处理 "2024 Jan-Feb" 这种格式
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
                    
                    # --- 提取新字段 ---
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
                        "aff": aff,           # 新增单位
                        "date": pub_date,     # 新增日期
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
        
        # --- 优化的展示格式 ---
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
