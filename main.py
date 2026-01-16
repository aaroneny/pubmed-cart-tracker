import requests
from Bio import Entrez
import datetime
from deep_translator import GoogleTranslator

# --- 1. 基础配置 ---
# 已替换为你提供的邮箱
Entrez.email = "dlu_fangenyue@163.com"

# --- 2. 关键词策略优化 (High Precision) ---
# 逻辑解释：
# Group A: 直接命中 "In vivo CAR-T" 或 "In situ CAR-T"
# Group B: "mRNA-LNP" 必须结合 "T cell" 或 "CAR" (排除新冠疫苗)
# Group C: "Lentiviral vector" 必须结合 "CAR" 或 "Engineering" (排除基础病毒学)
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

# --- 3. 内置期刊影响因子字典 ---
# 包含常见的生物医学、基因治疗、纳米材料期刊
JOURNAL_IFS = {
    "Nature": "64.8", "Science": "56.9", "Cell": "64.5",
    "Nature Medicine": "58.7", "New England Journal of Medicine": "96.2",
    "The Lancet": "98.4", "Nature Biotechnology": "46.9",
    "Nature Biomedical Engineering": "28.1", "Molecular Therapy": "12.4",
    "Blood": "20.3", "Circulation": "37.8", "Signal Transduction and Targeted Therapy": "40.8",
    "Cell Research": "44.1", "Molecular Cancer": "37.3",
    "Nature Communications": "16.6", "Science Advances": "13.6",
    "Advanced Materials": "29.4", "ACS Nano": "17.1",
    "Nano Letters": "10.8", "Biomaterials": "14.0",
    "Journal of Controlled Release": "10.8", "Small": "13.3",
    "Bioactive Materials": "18.9", "Nucleic Acids Research": "14.9",
    "Molecular Therapy - Nucleic Acids": "8.8",
    "Journal of Extracellular Vesicles": "16.0", "Gastroenterology": "29.4",
    "Gut": "24.5", "Hepatology": "13.5", "Journal of Hepatology": "25.7",
    "Cancer Discovery": "28.2", "Cancer Cell": "50.3",
    "Clinical Cancer Research": "11.5", "Journal of Clinical Oncology": "45.3",
    "Immunity": "32.4", "Science Immunology": "24.8",
    "Nature Immunology": "30.5", "Frontiers in Immunology": "7.3",
    "Journal of Virology": "5.4", "Virology": "3.5",
    "Gene Therapy": "4.5", "Human Gene Therapy": "4.2",
    "Stem Cell Reports": "5.9", "Cell Stem Cell": "23.9",
    "PNAS": "11.1", "Proceedings of the National Academy of Sciences": "11.1",
    "eLife": "7.7", "Scientific Reports": "3.8", "PLoS One": "2.9"
}

def get_impact_factor(journal_name):
    if journal_name in JOURNAL_IFS: return JOURNAL_IFS[journal_name]
    for key, value in JOURNAL_IFS.items():
        if key.lower() == journal_name.lower(): return value
    for key, value in JOURNAL_IFS.items():
        if key in journal_name and len(journal_name) < len(key) + 10: return value
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

# --- 4. Python级二次相关性检查 ---
def check_relevance(title, abstract):
    """
    检查标题和摘要是否包含核心关键词。
    """
    text = (title + " " + abstract).lower()
    
    # 白名单：必须包含至少一个
    must_have = [
        "car-t", "chimeric antigen", "t cell", "t-cell", "immunotherapy",
        "tumor", "cancer", "oncology", "malignan", 
        "gene edit", "crispr", "transduction", "payload"
    ]
    
    # 黑名单：如果是新冠文章且没提癌症，丢弃
    black_list = ["sars-cov-2", "covid-19", "coronavirus"]
    
    has_blacklist = any(word in text for word in black_list)
    has_cancer_context = any(w in text for w in ["cancer", "tumor", "oncology", "car"])
    
    if has_blacklist and not has_cancer_context:
        return False

    if any(word in text for word in must_have):
        return True
        
    return False

def fetch_papers():
    today = datetime.date.today()
    print(f"[{today}] 启动高精度搜索 (过去 30 天)...")
    
    try:
        # 扩大初筛范围到 30 篇
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
                    
                    # 二次过滤
                    if not check_relevance(title, full_abstract):
                        print(f"❌ 排除低相关文章: {title[:30]}...")
                        continue
                        
                    if_score = get_impact_factor(journal)
                    print(f"✅ 命中: {title[:20]}... | IF: {if_score}")
                    
                    conclusion_en = extract_conclusion(full_abstract)
                    highlight_cn = translate_to_chinese(conclusion_en)
                    pmid = article['MedlineCitation']['PMID']
                    
                    papers.append({
                        "title": title,
                        "journal": journal,
                        "if": if_score,
                        "highlight": highlight_cn, 
                        "link": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                    })
                except Exception as e:
                    continue
        except Exception:
            pass

    # 排序：IF 高的排前面
    papers.sort(key=lambda x: float(x['if']) if x['if'] != 'N/A' else 0, reverse=True)
    return papers

def update_readme(papers):
    current_date = datetime.datetime.now().strftime('%Y-%m-%d')
    content = f"# 🧬 In vivo CAR-T 精选追踪\n\n"
    content += f"**聚焦方向**: In vivo CAR-T | mRNA-LNP (Oncology) | Lentiviral Engineering\n\n"
    content += f"📅 **更新日期**: {current_date}\n\n"
    content += "---\n\n"
    
    if not papers:
        content += "📭 **过去 30 天未发现高相关度文献。**\n"
    
    for paper in papers:
        if_display = f"🔥 IF: **{paper['if']}**" if paper['if'] != "N/A" else "IF: -"
        content += f"### [{paper['title']}]({paper['link']})\n"
        content += f"- **期刊**: *{paper['journal']}* | {if_display}\n
