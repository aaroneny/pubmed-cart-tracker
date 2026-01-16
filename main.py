import requests
from Bio import Entrez
import datetime
from deep_translator import GoogleTranslator

# --- 1. 基础配置 ---
# 请替换为你自己的邮箱
Entrez.email = "dlu_fangenyue@163.com"

# --- 2. 关键词升级 (涵盖 In vivo CAR-T, mRNA-LNP, 慢病毒) ---
# 使用 OR 逻辑连接不同领域，确保全面覆盖
KEYWORDS = """
("In vivo CAR-T"[Title/Abstract] OR "In situ CAR-T"[Title/Abstract] 
OR "mRNA-LNP"[Title/Abstract] OR "Lipid nanoparticle"[Title/Abstract]
OR "Lentiviral vector"[Title/Abstract] OR "Lentivirus packaging"[Title/Abstract] 
OR "Gene delivery"[Title/Abstract])
"""

# --- 3. 内置期刊影响因子字典 (针对生物/医学领域) ---
# 注意：这是手动维护的列表，无法覆盖所有冷门期刊
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
    """
    尝试从字典中匹配 IF
    """
    # 1. 精确匹配
    if journal_name in JOURNAL_IFS:
        return JOURNAL_IFS[journal_name]
    
    # 2. 忽略大小写匹配
    for key, value in JOURNAL_IFS.items():
        if key.lower() == journal_name.lower():
            return value
            
    # 3. 模糊匹配 (比如包含关系)
    # 风险：可能匹配错，比如 "Nature" 匹配到 "Nature Reports"
    # 这里保守一点，只处理完全包含且长度接近的情况
    for key, value in JOURNAL_IFS.items():
        if key in journal_name and len(journal_name) < len(key) + 10:
             return value
             
    return "N/A" # 未找到

def translate_to_chinese(text):
    """使用 Google Translate 免费接口"""
    try:
        translator = GoogleTranslator(source='auto', target='zh-CN')
        return translator.translate(text)
    except Exception:
        return text

def extract_conclusion(abstract_text):
    """提取摘要结论部分"""
    if not abstract_text: return "暂无摘要"
    text = abstract_text.strip()
    upper_text = text.upper()
    
    # 策略A：找标签
    for keyword in ["CONCLUSION:", "CONCLUSIONS:", "DISCUSSION:"]:
        if keyword in upper_text:
            index = upper_text.rfind(keyword)
            return text[index + len(keyword):].strip()

    # 策略B：取最后两句
    sentences = [s.strip() for s in text.split('. ') if s.strip()]
    if len(sentences) >= 2:
        return ". ".join(sentences[-2:]) + "."
    elif len(sentences) == 1:
        return sentences[0] + "."
    return text

def fetch_papers():
    today = datetime.date.today()
    print(f"[{today}] 开始搜索过去 30 天关于 In vivo CAR-T/mRNA-LNP/Lentivirus 的文献...")
    
    try:
        # 修改点：reldate=30 (过去30天)
        handle = Entrez.esearch(db="pubmed", term=KEYWORDS, reldate=30, datetype="pdat", retmax=20)
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
                    
                    # 获取并计算 IF
                    if_score = get_impact_factor(journal)
                    
                    # 摘要处理
                    abstract_list = article['MedlineCitation']['Article'].get('Abstract', {}).get('AbstractText', [])
                    full_abstract = " ".join([str(x) for x in abstract_list]) if isinstance(abstract_list, list) else str(abstract_list)

                    print(f"处理: {title[:20]}... | IF: {if_score}")
                    
                    # 提取与翻译
                    conclusion_en = extract_conclusion(full_abstract)
                    highlight_cn = translate_to_chinese(conclusion_en)

                    pmid = article['MedlineCitation']['PMID']
                    
                    papers.append({
                        "title": title,
                        "journal": journal,
                        "if": if_score, # 新增 IF 字段
                        "highlight": highlight_cn, 
                        "link": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                        "date": article['MedlineCitation']['Article']['Journal']['JournalIssue']['PubDate'].get('Year', '202X')
                    })
                except Exception as e:
                    continue
        except Exception:
            pass

    # 按 IF 从高到低排序 (把重磅文章放前面)
    # 将 'N/A' 视为 0 进行排序
    papers.sort(key=lambda x: float(x['if']) if x['if'] != 'N/A' else 0, reverse=True)
    
    return papers

def update_readme(papers):
    current_date = datetime.datetime.now().strftime('%Y-%m-%d')
    
    content = f"# 🧬 Bio-Research Monthly Tracker\n\n"
    content += f"**关注领域**: In vivo CAR-T | mRNA-LNP | Lentiviral Vectors\n\n"
    content += f"📅 **更新日期**: {current_date} (过去 30 天文献，按 IF 排序)\n\n"
    content += "---\n\n"
    
    if not papers:
        content += "📭 **过去 30 天未发现相关新文献。**\n"
    
    for paper in papers:
        # 只有当 IF 不是 N/A 时才显示火的图标
        if_display = f"🔥 IF: **{paper['if']}**" if paper['if'] != "N/A" else "IF: -"
        
        content += f"### [{paper['title']}]({paper['link']})\n"
        content += f"- **期刊**: *{paper['journal']}* | {if_display}\n"
        content += f"- **核心结论**: \n> {paper['highlight']}\n\n"
        content += "---\n"
        
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(content)

if __name__ == "__main__":
    papers = fetch_papers()
    update_readme(papers)
