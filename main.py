import os
from Bio import Entrez
from datetime import datetime

# ================= 配置区域 =================
Entrez.email = "your.email@example.com"
SEARCH_TERM = "In vivo CAR-T"
# ✅ 改回 7 天，避免信息过载
TIME_RANGE_DAYS = 7
MAX_RESULTS = 500 

# 🌟 扩充版影响因子库 (涵盖 CAR-T 相关的 免疫/肿瘤/血液/综合 期刊)
# 数据大致基于 2023/2024 JCR，仅供参考
JOURNAL_IF_MAP = {
    # === 综合顶刊 ===
    "Nature": 64.8, "Science": 56.9, "Cell": 64.5, 
    "The New England Journal of Medicine": 96.2, "New England Journal of Medicine": 96.2,
    "The Lancet": 168.9, "JAMA": 120.7, "BMJ": 105.7,
    "Nature Communications": 16.6, "Science Advances": 13.6, 
    "Proceedings of the National Academy of Sciences": 11.1, "PNAS": 11.1,
    "Cell Reports": 8.8, "iScience": 5.8, "Heliyon": 4.0,

    # === 血液学核心 (Hematology) ===
    "Blood": 21.0, "Leukemia": 12.8, 
    "American Journal of Hematology": 12.8, "Haematologica": 10.1,
    "Blood Advances": 7.5, "British Journal of Haematology": 8.6,
    "Journal of Hematology & Oncology": 29.5, 
    "Bone Marrow Transplantation": 4.5, "Transplantation and Cellular Therapy": 5.2,
    "Stem Cell Reviews and Reports": 5.8,

    # === 肿瘤学核心 (Oncology) ===
    "Cancer Cell": 50.3, "Cancer Discovery": 29.7, 
    "Journal of Clinical Oncology": 45.3, "JAMA Oncology": 28.4,
    "The Lancet Oncology": 51.1, "Molecular Cancer": 37.3,
    "Clinical Cancer Research": 11.5, "Cancer Research": 11.2,
    "Journal for ImmunoTherapy of Cancer": 10.9, "JITC": 10.9,
    "Oncogene": 8.0, "Cancer Letters": 9.7, "Cancers": 5.2,
    "Frontiers in Oncology": 4.7, "BMC Cancer": 3.8,

    # === 免疫学与治疗 (Immunology & Therapy) ===
    "Nature Immunology": 30.5, "Immunity": 32.4, "Science Immunology": 24.8,
    "Cellular & Molecular Immunology": 24.1, "Molecular Therapy": 12.4,
    "Molecular Therapy - Oncolytics": 5.3, "Molecular Therapy - Methods & Clinical Development": 10.2,
    "Molecular Therapy - Nucleic Acids": 8.8,
    "Frontiers in Immunology": 7.3, "Journal of Immunology": 4.4,
    "Cancer Immunology Research": 10.1, "OncoImmunology": 7.2,
    "Cytotherapy": 5.4, "Human Gene Therapy": 4.2,

    # === 自然子刊 (Nature Reviews / Others) ===
    "Nature Reviews Drug Discovery": 122.7, "Nature Reviews Cancer": 78.5,
    "Nature Reviews Immunology": 100.3, "Nature Reviews Clinical Oncology": 78.8,
    "Nature Medicine": 82.9, "Nature Biotechnology": 46.9,
    "Nature Biomedical Engineering": 28.1, "Nature Cancer": 23.5,

    # === 常见的综合/OA期刊 (容易出现的地方) ===
    "Scientific Reports": 4.6, "PLoS One": 3.7, "PLOS ONE": 3.7,
    "eLife": 7.7, "Theranostics": 12.4, "Bioactive Materials": 18.9,
    "Signal Transduction and Targeted Therapy": 39.3, "STTT": 39.3,
    "International Journal of Molecular Sciences": 5.6, "IJMS": 5.6,
    "Biomaterials": 14.0, "Advanced Materials": 29.4,
    "ACS Nano": 17.1, "Nano Letters": 10.8, "Small": 13.3,
    "Cells": 6.0, "Biomedicines": 4.7
}
# ===========================================

def get_impact_factor(journal_name):
    """
    智能匹配 IF：
    1. 完全匹配
    2. 忽略大小写匹配
    3. 移除 'The ' 前缀匹配
    """
    if not journal_name: return "N/A"
    
    # 1. 直接查
    if journal_name in JOURNAL_IF_MAP:
        return JOURNAL_IF_MAP[journal_name]
    
    # 2. 清洗一下名字 (变小写, 去空格)
    clean_name = journal_name.strip().lower()
    
    # 遍历字典查找
    for k, v in JOURNAL_IF_MAP.items():
        db_clean = k.strip().lower()
        
        # 匹配逻辑：全等 或者 也是为了处理 "The Lancet" vs "Lancet"
        if clean_name == db_clean:
            return v
        if clean_name.replace("the ", "") == db_clean.replace("the ", ""):
            return v
            
    return "N/A"

def search_pubmed(base_term, is_review=False):
    """搜索过去 TIME_RANGE_DAYS 天的文章"""
    if is_review:
        term = f"({base_term}) AND Review[Publication Type]"
    else:
        term = f"({base_term}) AND Journal Article[Publication Type] NOT Review[Publication Type]"

    try:
        # 使用配置好的 TIME_RANGE_DAYS
        handle = Entrez.esearch(db="pubmed", term=term, retmax=MAX_RESULTS, 
                                reldate=TIME_RANGE_DAYS, datetype="edat", sort="date")
        record = Entrez.read(handle)
        handle.close()
        return record["IdList"]
    except Exception as e:
        print(f"搜索出错: {e}")
        return []

def fetch_details(id_list):
    """批量获取详情"""
    if not id_list:
        return []
    all_records = []
    batch_size = 200
    print(f"正在获取 {len(id_list)} 篇文章详情...")
    for i in range(0, len(id_list), batch_size):
        batch_ids = id_list[i:i+batch_size]
        ids = ",".join(batch_ids)
        try:
            handle = Entrez.efetch(db="pubmed", id=ids, retmode="xml")
            records = Entrez.read(handle)
            handle.close()
            if 'PubmedArticle' in records:
                all_records.extend(records["PubmedArticle"])
        except Exception as e:
            print(f"分批获取详情失败: {e}")
    return all_records

def format_article_list(articles):
    if not articles:
        return "*(本周暂无该类目新增文献)*\n\n"
    
    text = ""
    # 按影响因子排序 (可选: 想看高分的排前面就取消注释下一行)
    # articles.sort(key=lambda x: get_impact_factor(x['MedlineCitation']['Article']['Journal'].get('Title', '')) if isinstance(get_impact_factor(x['MedlineCitation']['Article']['Journal'].get('Title', '')), (int, float)) else -1, reverse=True)

    for article in articles:
        try:
            title = article['MedlineCitation']['Article']['ArticleTitle']
        except:
            title = "无标题"
        
        pmid = article['MedlineCitation']['PMID']
        url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
        
        try:
            journal = article['MedlineCitation']['Article']['Journal']['Title']
        except:
            journal = "未知期刊"

        # 获取 IF
        if_val = get_impact_factor(journal)
        
        # 徽章显示逻辑
        if isinstance(if_val, (int, float)):
            if if_val > 20:
                if_display = f"🔥 **IF: {if_val}**" # 高分加火
            elif if_val > 10:
                if_display = f"🌟 **IF: {if_val}**" # 10分以上加星
            else:
                if_display = f"IF: {if_val}"
        else:
            if_display = "IF: N/A"

        try:
            abstract_list = article['MedlineCitation']['Article']['Abstract']['AbstractText']
            abstract = " ".join([str(x) for x in abstract_list])
            abstract_preview = abstract[:200] + "..." 
        except:
            abstract_preview = "暂无摘要预览"

        text += f"### [{title}]({url})\n"
        text += f"- 📚 **{journal}** | {if_display}\n" 
        text += f"- **摘要**: {abstract_preview}\n\n"
    return text

def update_readme(reviews, articles):
    date_str = datetime.now().strftime("%Y-%m-%d")
    
    content = f"# 🧬 In vivo CAR-T 文献周报\n\n"
    content += f"> 📅 更新日期: {date_str} | ⏱️ 统计范围: 过去 {TIME_RANGE_DAYS} 天 | 🔍 关键词: {SEARCH_TERM}\n\n"
    
    content += f"## 📘 最新综述 (Reviews) - {len(reviews)} 篇\n"
    content += "---\n"
    content += format_article_list(reviews)
    
    content += f"## 🔬 最新研究论文 (Articles) - {len(articles)} 篇\n"
    content += "---\n"
    content += format_article_list(articles)
    
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(content)

if __name__ == "__main__":
    print(f"🔍 开始检索过去 {TIME_RANGE_DAYS} 天 '{SEARCH_TERM}' 相关文献...")
    
    review_ids = search_pubmed(SEARCH_TERM, is_review=True)
    review_details = fetch_details(review_ids)
    
    article_ids = search_pubmed(SEARCH_TERM, is_review=False)
    article_details = fetch_details(article_ids)
    
    print(f"✅ 处理完成: 综述 {len(review_details)} 篇，论文 {len(article_details)} 篇。")
    update_readme(review_details, article_details)
